# Coding Summaries

Patterns, decisions, and conventions established during implementation.

## Totals Endpoints Pattern (Tasks 1-3)

### `_build_filtered_queryset()` Extraction Pattern
All three services (TransactionService, PlannedTransactionService, CurrencyExchangeService) follow the same pattern:
1. Extract filter-building logic from `list()` into a `@staticmethod _build_filtered_queryset(workspace_id, **filters)` placed before `list()` (private-methods-first convention)
2. `list()` delegates to `_build_filtered_queryset()` then adds `select_related()` and ordering
3. `totals()` delegates to `_build_filtered_queryset()` then applies aggregation

### Django `values()` + FK Field Name Conflict
When using `values()` with `F()` to alias FK fields (e.g., `currency=F('currency__symbol')`), Django raises `ValueError: The annotation 'currency' conflicts with a field on the model` because `currency` is a FK field. 

**Workaround:** Use `annotate(currency_symbol=F('currency__symbol')).values('type', 'currency_symbol')` and map result dict keys in Python:
```python
rows = queryset.annotate(currency_symbol=F('currency__symbol')).values('type', 'currency_symbol').annotate(total=Sum('amount')).order_by('type', 'currency_symbol')
return [{'type': r['type'], 'currency': r['currency_symbol'], 'total': r['total']} for r in rows]
```

Alternatively, use double-underscore lookups in `values()` directly (e.g., `values('currency__symbol')`) and remap keys.

### Totals Endpoint Placement
`GET /totals` endpoints are placed **before** `/{resource_id}` in the API router to avoid Django Ninja matching `/totals` as an `transaction_id` parameter.

### Totals Schemas
Each totals endpoint uses a `{Resource}TotalsItem` + `{Resource}TotalsResponse` pair of Pydantic schemas. The response wraps items in a `totals` list field.

## Frontend Totals Types + Component (Task 4)

### API Client `getTotals()` Methods
Each API client object (`transactionsApi`, `plannedTransactionsApi`, `currencyExchangesApi`) has a `getTotals()` method that omits `page`, `page_size`, and `ordering` params from the list endpoint params.

### `TotalsSummary` Component
Uses discriminated union props with `mode: 'transactions' | 'planned' | 'exchanges'`. Returns `null` for empty totals. Uses design system tokens (`bg-surface`, `border-border`, `text-positive`, `text-negative`, `font-mono`, `rounded-sm`). `ArrowRight` icon from `lucide-react` for exchange pairs.

### TotalsSummary Table Layout (Task R6)
- **Width constraint:** Outer container divs use `w-fit` so tables shrink to content width instead of stretching full-width. This prevents large empty gaps between columns on wide screens.
- **Row hover:** All `<tbody>` data rows use `hover:bg-surface-hover transition-colors` for visual traceability. `<thead>` rows have no hover. Existing text color classes (`text-positive`, `text-negative`, `text-text`) are preserved alongside hover — the subtle `bg-surface-hover` background doesn't conflict.

### TotalsSummary Placement Pattern (Task R7)
- **Separate card placement:** On all three pages (Transactions, Planned, Currency Exchanges), `TotalsSummary` is rendered as a sibling **after** the main table container `<div>`, NOT inside it. This makes it a separate card below the records table.
- **Inside vs outside:** The table container (`bg-surface border border-border rounded-sm overflow-hidden`) wraps only: desktop table, mobile cards, empty state, and pagination. `TotalsSummary` renders outside this container using its own card styling.
- **Consistency:** All three pages follow the same pattern — `TotalsSummary` is placed after the closing `</div>` of the records table container but before any modal components.

### Totals Query Invalidation in Form Modals (Task R8)
- **Mutation categories:** Page-level mutations (delete, import) already invalidate totals query keys. Form modal mutations (create/update via `TransactionFormModal`, `PlannedTransactionFormModal`, `CurrencyExchangeFormModal`) and execute mutations (`ExecutePlannedModal`) were missing these calls.
- **Pattern:** Add `queryClient.invalidateQueries({ queryKey: ['{resource}-totals-{group}'] })` calls in each modal's `onSuccess` callback, right after the existing resource-level invalidation.
- **Cross-resource invalidation:** `PlannedTransactionFormModal` and `ExecutePlannedModal` also invalidate transaction totals (`transactions-totals-type`, `transactions-totals-category`) because creating/executing a planned transaction affects the Transactions page data.
- **Existing calls preserved:** All pre-existing `invalidateQueries` and `refetchQueries` calls are kept in place — only new calls are added.

## Round 5 Remediation (Tasks R9-R16)

### Service Totals Return Consistency (Task R9)
- **Pattern:** All three totals services (`TransactionService`, `PlannedTransactionService`, `CurrencyExchangeService`) now return plain `list[dict]` from their `totals()` methods. No Pydantic instances in service returns — serialization happens at the API layer.
- **Import hygiene:** Inline imports inside methods are a code smell. If an import is needed, move it to the top level. If removing usage makes the import unused, remove it entirely.

### Query Parameter Naming: Avoid Builtin Shadowing (Task R10, R15)
- **Convention:** Never use Python builtins (`type`, `id`, `input`, `list`, etc.) as parameter/variable names in API endpoints or service methods. Use descriptive names like `transaction_type`, `resource_id`, etc.
- **Backend+frontend alignment:** When renaming a query parameter in the backend API, the frontend must be updated in lockstep — both the API client params AND the page components that construct the params.

### TotalsLabel Enum for Magic Strings (Task R11, R14)
- **Backend:** `common/enums.py` contains `TotalsLabel` StrEnum with `UNCATEGORIZED = 'Uncategorized'`. Used in `Value()` calls in services and in test assertions.
- **Frontend:** `types/index.ts` contains matching `TotalsLabel` enum with `UNCATEGORIZED = 'Uncategorized'`. Synced with backend enum.
- **Collision note:** The current approach could collide with a user-created category named "Uncategorized". A future improvement should use a sentinel value and handle display on the frontend.

### Combined group_by for Totals Endpoint (Task R12, R16)
- **Backend pattern:** `TransactionTotalsResponse` uses optional fields (`totals`, `by_type`, `by_category`) to support both single-group and combined-group responses from the same endpoint.
- **API design:** `group_by=type` or `group_by=category` returns `{"totals": [...]}`. `group_by=type,category` returns `{"by_type": [...], "by_category": [...]}`. This avoids a breaking change while adding combined support.
- **Frontend optimization:** Single `useQuery` call with `group_by: 'type,category'` replaces two parallel queries, halving network requests. `useMemo` prevents unnecessary query key recalculations.
- **Query invalidation key:** Single `['transactions-totals']` key replaces two separate `['transactions-totals-type']` and `['transactions-totals-category']` keys.

### String-Based Amount Formatting (Task R14)
- **Pattern:** `formatAmount()` in `TotalsSummary.tsx` uses string manipulation instead of `parseFloat()` to preserve full Decimal precision from the backend. Handles negatives, missing decimals, and >2 decimal places.
- **Never use parseFloat for financial data:** It loses precision for large values (e.g., `"123456789012345.67"`).

### Early Data Fetching (Task R16)
- **Convention:** Totals queries should use `enabled: !!selectedPeriodId` without gating on `totalItems > 0`. Fetching totals in parallel with the list query avoids delayed display when the list loads first.


