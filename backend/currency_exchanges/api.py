"""Django-Ninja API endpoints for currency_exchanges app."""

import json

from django.http import HttpRequest, HttpResponse
from ninja import File, Form, Query, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from common.auth import WorkspaceJWTAuth
from common.throttle import validate_file_size
from currency_exchanges.schemas import (
    CurrencyExchangeCreate,
    CurrencyExchangeOut,
    CurrencyExchangeUpdate,
)
from currency_exchanges.services import CurrencyExchangeService

router = Router(tags=['Currency Exchanges'])


# =============================================================================
# Currency Exchange Endpoints
# =============================================================================


@router.get('', response=list[CurrencyExchangeOut], auth=WorkspaceJWTAuth())
def list_exchanges(
    request: HttpRequest,
    budget_period_id: int | None = Query(None),
):
    """List currency exchanges for the current workspace."""
    workspace_id = request.auth.current_workspace_id

    from currency_exchanges.models import CurrencyExchange

    queryset = CurrencyExchange.objects.select_related('budget_period').for_workspace(workspace_id)

    if budget_period_id:
        queryset = queryset.filter(budget_period_id=budget_period_id)

    return list(queryset.order_by('-date'))


@router.post('', response={201: CurrencyExchangeOut, 400: dict}, auth=WorkspaceJWTAuth())
def create_exchange(request: HttpRequest, data: CurrencyExchangeCreate):
    """Create a new currency exchange (requires write access)."""
    user = request.auth
    workspace = user.current_workspace

    exchange = CurrencyExchangeService.create(user, workspace, data)
    return 201, exchange


# Specific routes must come before parameterized routes
@router.get('/export/', auth=WorkspaceJWTAuth())
def export_exchanges(
    request: HttpRequest,
    budget_period_id: int = Query(...),
):
    """Export currency exchanges from a budget period to a JSON file."""
    workspace = request.auth.current_workspace

    export_data = CurrencyExchangeService.export(workspace, budget_period_id)
    response = HttpResponse(
        json.dumps(export_data, indent=2),
        content_type='application/json',
    )
    response['Content-Disposition'] = f'attachment; filename=currency_exchanges_export_{budget_period_id}.json'
    return response


@router.post('/import', response={201: dict, 400: dict}, auth=WorkspaceJWTAuth())
def import_exchanges(
    request: HttpRequest,
    budget_period_id: int = Form(...),
    file: UploadedFile = File(...),
):
    """Import currency exchanges from a JSON file into a budget period (requires write access)."""
    user = request.auth
    workspace = user.current_workspace

    validate_file_size(file, max_size_mb=5)

    try:
        data = json.loads(file.read())
    except json.JSONDecodeError:
        return 400, {'error': 'Invalid JSON file.'}
    except Exception as e:
        return 400, {'error': f'Invalid data format: {e}'}

    count = CurrencyExchangeService.import_data(user, workspace, budget_period_id, data)
    if count == 0:
        return 201, {'message': 'No new currency exchanges to import.'}
    return 201, {'message': f'Successfully imported {count} new currency exchanges.'}


# Parameterized routes must come after specific routes
@router.get('/{exchange_id}', response=CurrencyExchangeOut, auth=WorkspaceJWTAuth())
def get_exchange(request: HttpRequest, exchange_id: int):
    """Get a specific currency exchange."""
    workspace_id = request.auth.current_workspace_id

    exchange = CurrencyExchangeService.get_exchange(exchange_id, workspace_id)
    if not exchange:
        raise HttpError(404, 'Exchange not found')

    return exchange


@router.put('/{exchange_id}', response=CurrencyExchangeOut, auth=WorkspaceJWTAuth())
def update_exchange(request: HttpRequest, exchange_id: int, data: CurrencyExchangeUpdate):
    """Update a currency exchange (requires write access)."""
    user = request.auth
    workspace = user.current_workspace

    exchange = CurrencyExchangeService.update(user, workspace, exchange_id, data)
    return exchange


@router.delete('/{exchange_id}', response={204: None}, auth=WorkspaceJWTAuth())
def delete_exchange(request: HttpRequest, exchange_id: int):
    """Delete a currency exchange (requires write access)."""
    user = request.auth
    workspace = user.current_workspace

    CurrencyExchangeService.delete(user, workspace, exchange_id)
    return 204, None
