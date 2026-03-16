"""Django-Ninja API endpoints for budgets app."""

from ninja import Query, Router

from budgets.schemas import BudgetCreate, BudgetOut, BudgetUpdate
from budgets.services import BudgetService
from common.auth import WorkspaceJWTAuth

router = Router(tags=['Budgets'])


# =============================================================================
# Budget Endpoints
# =============================================================================


@router.get('', response=list[BudgetOut], auth=WorkspaceJWTAuth())
def list_budgets(
    request,
    budget_period_id: int | None = Query(None),
):
    """List budgets for the current workspace, optionally filtered by period."""
    workspace_id = request.auth.current_workspace_id

    from budgets.models import Budget

    queryset = Budget.objects.select_related('category').for_workspace(workspace_id)

    if budget_period_id:
        queryset = queryset.filter(budget_period_id=budget_period_id)

    return queryset


@router.post('', response={201: BudgetOut, 400: dict}, auth=WorkspaceJWTAuth())
def create_budget(request, data: BudgetCreate):
    """Create a new budget entry."""
    user = request.auth
    workspace = user.current_workspace

    budget = BudgetService.create(user, workspace, data)
    return 201, budget


@router.put('/{budget_id}', response=BudgetOut, auth=WorkspaceJWTAuth())
def update_budget(request, budget_id: int, data: BudgetUpdate):
    """Update a budget entry."""
    user = request.auth
    workspace = user.current_workspace

    budget = BudgetService.update(user, workspace, budget_id, data)
    return budget


@router.delete('/{budget_id}', response={204: None}, auth=WorkspaceJWTAuth())
def delete_budget(request, budget_id: int):
    """Delete a budget entry."""
    user = request.auth
    workspace = user.current_workspace

    BudgetService.delete(user, workspace, budget_id)
    return 204, None
