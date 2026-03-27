"""Django-Ninja API endpoints for authentication (register, login)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from ninja import Router

from common.auth import create_access_token
from common.throttle import rate_limit
from common.utils import get_client_ip
from core.schemas import (
    DetailOut,
    ErrorOut,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResendVerificationIn,
    Token,
    VerifyEmailIn,
)
from workspaces.services import WorkspaceService

router = Router(tags=['Auth'])
User = get_user_model()


@router.post('/register', response={201: Token, 400: ErrorOut, 403: DetailOut, 429: DetailOut})
@rate_limit('register', limit=5, period=60)
def register(request, data: RegisterIn):
    """
    Register a new user with workspace and default data.

    Creates:
    - User account
    - Workspace with user as owner
    - Workspace membership
    - Default budget account
    - Demo data for the previous month

    Returns JWT token for automatic login.
    """
    if settings.DEMO_MODE:
        return 403, {'detail': 'Registration is disabled in demo mode'}

    if User.objects.filter(email=data.email).exists():
        return 400, {'error': 'User with this email already exists'}

    with transaction.atomic():
        user = User.objects.create_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        WorkspaceService.create_workspace(user=user, name=data.workspace_name, create_demo=True)

        from users.models import ConsentType
        from users.services import UserService

        ip = get_client_ip(request)
        UserService.record_consent(user, ConsentType.TERMS_OF_SERVICE, data.accepted_terms_version, ip)
        UserService.record_consent(user, ConsentType.PRIVACY_POLICY, data.accepted_privacy_version, ip)

        transaction.on_commit(lambda: UserService.send_registration_emails(user))

    access_token = create_access_token(user)

    return 201, {
        'access_token': access_token,
        'token_type': 'bearer',
    }


@router.post('/login', response={200: Token, 401: DetailOut, 429: DetailOut})
@rate_limit('login', limit=10, period=60)
def login(request, data: LoginIn):
    """
    Login user and return JWT token.

    The token includes:
    - user_id
    - email
    - current_workspace_id
    """
    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        return 401, {'detail': 'Invalid email or password'}

    if not user.check_password(data.password):
        return 401, {'detail': 'Invalid email or password'}

    if not user.is_active:
        return 401, {'detail': 'User account is disabled'}

    access_token = create_access_token(user)

    return 200, {
        'access_token': access_token,
        'token_type': 'bearer',
    }


@router.post('/verify-email', response={200: MessageOut, 400: DetailOut})
def verify_email(request, data: VerifyEmailIn):
    from users.services import UserService

    UserService.verify_email(data.token)
    return 200, {'message': 'Email verified successfully'}


@router.post('/resend-verification', response={200: MessageOut, 429: DetailOut})
@rate_limit('resend_verification', limit=3, period=3600)
def resend_verification(request, data: ResendVerificationIn):
    from users.services import UserService

    return 200, {'message': UserService.resend_verification(data.email)}
