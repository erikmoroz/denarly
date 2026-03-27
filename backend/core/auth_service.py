import datetime

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

from core.schemas import UserOut

User = get_user_model()


class AuthService:
    @staticmethod
    def create_access_token(user: User) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        exp = now + datetime.timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'current_workspace_id': str(user.current_workspace_id) if user.current_workspace_id else None,
            'iat': now.timestamp(),
            'exp': exp.timestamp(),
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> dict | None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def create_temp_token(user: User) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            'user_id': str(user.id),
            'type': '2fa_pending',
            'iat': now.timestamp(),
            'exp': (now + datetime.timedelta(minutes=5)).timestamp(),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_temp_token(token: str) -> dict | None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get('type') != '2fa_pending':
                return None
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def user_to_schema(user: User) -> UserOut:
        return UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            current_workspace_id=user.current_workspace_id if user.current_workspace_id else None,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )
