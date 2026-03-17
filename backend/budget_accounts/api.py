"""Django-Ninja API endpoints for budget_accounts app."""

from django.http import HttpRequest
from ninja import Query, Router
from ninja.errors import HttpError

from budget_accounts.exceptions import (
    BudgetAccountCurrencyNotFoundError,
    BudgetAccountDuplicateNameError,
    BudgetAccountNotFoundError,
)
from budget_accounts.schemas import BudgetAccountCreate, BudgetAccountOut, BudgetAccountUpdate
from budget_accounts.services import BudgetAccountService
from common.auth import WorkspaceJWTAuth
from common.permissions import require_role
from workspaces.models import ADMIN_ROLES

router = Router(tags=['Budget Accounts'])


def _handle_service_exception(exc) -> None:
    """Convert service exceptions to HTTP errors."""
    if isinstance(exc, BudgetAccountNotFoundError):
        raise HttpError(404, exc.message)
    if isinstance(exc, BudgetAccountDuplicateNameError):
        raise HttpError(400, exc.message)
    if isinstance(exc, BudgetAccountCurrencyNotFoundError):
        raise HttpError(400, exc.message)


@router.get('', response=list[BudgetAccountOut], auth=WorkspaceJWTAuth())
def list_budget_accounts(
    request: HttpRequest,
    include_inactive: bool = Query(False),
):
    """List all budget accounts in current workspace."""
    workspace_id = request.auth.current_workspace_id
    return BudgetAccountService.list(workspace_id, include_inactive)


@router.get('/{account_id}', response=BudgetAccountOut, auth=WorkspaceJWTAuth())
def get_budget_account(request: HttpRequest, account_id: int):
    """Get a specific budget account."""
    workspace_id = request.auth.current_workspace_id
    try:
        return BudgetAccountService.get(account_id, workspace_id)
    except BudgetAccountNotFoundError as e:
        _handle_service_exception(e)


@router.post('', response={201: BudgetAccountOut}, auth=WorkspaceJWTAuth())
def create_budget_account(request: HttpRequest, data: BudgetAccountCreate):
    """Create a new budget account (requires owner or admin role)."""
    user = request.auth
    workspace = user.current_workspace
    require_role(user, workspace.id, ADMIN_ROLES)
    try:
        account = BudgetAccountService.create(user, workspace, data)
        return 201, account
    except (BudgetAccountDuplicateNameError, BudgetAccountCurrencyNotFoundError) as e:
        _handle_service_exception(e)


@router.put('/{account_id}', response=BudgetAccountOut, auth=WorkspaceJWTAuth())
def update_budget_account(request: HttpRequest, account_id: int, data: BudgetAccountUpdate):
    """Update a budget account (requires owner or admin role)."""
    user = request.auth
    workspace = user.current_workspace
    require_role(user, workspace.id, ADMIN_ROLES)
    try:
        return BudgetAccountService.update(user, workspace, account_id, data)
    except (BudgetAccountNotFoundError, BudgetAccountDuplicateNameError, BudgetAccountCurrencyNotFoundError) as e:
        _handle_service_exception(e)


@router.delete('/{account_id}', response={204: None}, auth=WorkspaceJWTAuth())
def delete_budget_account(request: HttpRequest, account_id: int):
    """Delete a budget account (requires owner or admin role)."""
    workspace_id = request.auth.current_workspace_id
    require_role(request.auth, workspace_id, ADMIN_ROLES)
    try:
        BudgetAccountService.delete(workspace_id, account_id)
        return 204, None
    except BudgetAccountNotFoundError as e:
        _handle_service_exception(e)


@router.patch('/{account_id}/archive', response=BudgetAccountOut, auth=WorkspaceJWTAuth())
def toggle_archive_budget_account(request: HttpRequest, account_id: int):
    """Archive/unarchive a budget account (toggle is_active)."""
    user = request.auth
    workspace_id = request.auth.current_workspace_id
    require_role(user, workspace_id, ADMIN_ROLES)
    try:
        return BudgetAccountService.toggle_archive(user, workspace_id, account_id)
    except BudgetAccountNotFoundError as e:
        _handle_service_exception(e)
