# Amount Totals Summary — PR Review Remediation Round 5

## Overview
Code quality improvements from PR #47 review (fifth cycle). Addresses inconsistency in service return types, builtin shadowing, magic strings, test gaps, precision handling, unnecessary re-renders, redundant network requests, and delayed data fetching.

## PR Review Trigger
PR #47 (fifth review cycle) — reviewer identified 11 issues; user confirmed 8 for action.

## Task Breakdown

---

### Task R9: Backend — CurrencyExchanges `totals()` return dicts + move import
**Severity:** MEDIUM
**PR Comment:** "currency_exchanges/services.py:99-117 — totals() returns CurrencyExchangeTotalsItem Pydantic instances, but the other two services return plain dicts."

**Files to modify:**
1. `backend/currency_exchanges/services.py`

**Implementation:**

1. Move the inline import `from currency_exchanges.schemas import CurrencyExchangeTotalsItem` (line 94) to the top-level imports (after line 15). No circular dependency — `schemas.py` doesn't import from `services.py`.

2. Change `totals()` (lines 102-110) to return plain dicts instead of Pydantic instances:

```python
# Before:
return [
    CurrencyExchangeTotalsItem(
        from_currency=row['from_currency__symbol'],
        to_currency=row['to_currency__symbol'],
        from_total=row['from_total'],
        to_total=row['to_total'],
    )
    for row in rows
]

# After:
return [
    {
        'from_currency': row['from_currency__symbol'],
        'to_currency': row['to_currency__symbol'],
        'from_total': row['from_total'],
        'to_total': row['to_total'],
    }
    for row in rows
]
```

3. After the change, `CurrencyExchangeTotalsItem` is no longer used in `services.py`. Remove the import entirely (it was only used for constructing instances, not for typing).

**Done criteria:**
- [ ] `CurrencyExchangeService.totals()` returns `list[dict]`, consistent with `TransactionService.totals()` and `PlannedTransactionService.totals()`
- [ ] Inline import removed from `totals()` method
- [ ] Unused `CurrencyExchangeTotalsItem` import removed from top-level imports
- [ ] Tests pass: `cd backend && backend/.venv/bin/python -m pytest currency_exchanges/tests/test_totals.py -v`

**Context estimate:** ~8k tokens
**Verification:**
```bash
cd backend && backend/.venv/bin/python -m pytest currency_exchanges/tests/ -v
```

---

### Task R10: Backend — Rename `type` → `transaction_type` in transactions API
**Severity:** MEDIUM
**PR Comment:** "transactions/api.py — type: list[str] | None = Query(None) shadows Python's type builtin."

**Files to modify:**
1. `backend/transactions/api.py` — rename the `type` Query param to `transaction_type` in all three endpoints: `list_transactions` (line 27), `get_transaction_totals` (line 64), `export_transactions` (line 97). Update the `type=` kwarg in service calls accordingly.
2. `backend/transactions/services.py` — rename `type` parameter to `transaction_type` in `_build_filtered_queryset` (line 94), `list` (line 149), and `totals` (line 198). Update the `if type:` check at line 125 to `if transaction_type:` and the filter `.filter(type__in=type)` to `.filter(type__in=transaction_type)`. Note: the Django model field is still `type` — only the Python variable names change.
3. `backend/transactions/tests.py` — update all URL query strings from `&type=expense` / `&type=income` to `&transaction_type=expense` / `&transaction_type=income`.

**Implementation details:**

In `api.py`, the three endpoints change from:
```python
type: list[str] | None = Query(None),
```
to:
```python
transaction_type: list[str] | None = Query(None),
```

And the service calls change from `type=type` to `transaction_type=transaction_type`.

The `export_transactions` endpoint uses a single string (not a list):
```python
transaction_type: str | None = Query(None, pattern=r'^(expense|income)$'),
```
And calls `TransactionService.export(workspace_id, budget_period_id, transaction_type)`.

In `services.py`, the `export` method already uses `trans_type` as the param name (line 320), so it doesn't need renaming. Only `_build_filtered_queryset`, `list`, and `totals` need the rename.

In `tests.py`, the affected URL patterns are:
- `&type=expense` → `&transaction_type=expense` (line 166, 957, 612)
- All other `type=` in tests are model field values (e.g., `type='expense'`), not URL params — those stay unchanged.

**Done criteria:**
- [ ] No `type` query parameter names in `transactions/api.py` (all renamed to `transaction_type`)
- [ ] No `type` parameter names in `transactions/services.py` methods (all renamed to `transaction_type`)
- [ ] Django `type` field lookups (`filter(type__in=...)`) still use `type` — only variable names change
- [ ] All test URLs updated to use `transaction_type=`
- [ ] Tests pass: `cd backend && backend/.venv/bin/python -m pytest transactions/tests.py -v`

**Context estimate:** ~20k tokens
**Verification:**
```bash
cd backend && backend/.venv/bin/python -m pytest transactions/tests.py -v
```

---

### Task R11: Backend — Add `TotalsLabel` enum for "Uncategorized"
**Severity:** LOW
**PR Comment:** '"Uncategorized" magic string — if a real user-created category is named "Uncategorized", it will silently merge with truly null categories.'

**Files to modify:**
1. `backend/common/enums.py` — new file with `TotalsLabel` StrEnum
2. `backend/transactions/services.py` — use `TotalsLabel.UNCATEGORIZED` instead of `'Uncategorized'`
3. `backend/planned_transactions/services.py` — use `TotalsLabel.UNCATEGORIZED` instead of `'Uncategorized'`
4. `backend/transactions/tests.py` — import and use `TotalsLabel.UNCATEGORIZED` in test assertions
5. `backend/planned_transactions/tests/test_planned_transactions.py` — import and use `TotalsLabel.UNCATEGORIZED` in test assertions

**Implementation:**

Create `backend/common/enums.py`:
```python
from enum import StrEnum


class TotalsLabel(StrEnum):
    """Labels used in totals aggregation responses.

    NOTE: The current "Uncategorized" label could collide with a user-created
    category of the same name. A future improvement should use a sentinel value
    (e.g. __uncategorized__) here and handle i18n/display on the frontend.
    """

    UNCATEGORIZED = 'Uncategorized'
```

In `transactions/services.py` (line 230), change:
```python
category_name=Coalesce('category__name', Value('Uncategorized')),
```
to:
```python
from common.enums import TotalsLabel
...
category_name=Coalesce('category__name', Value(TotalsLabel.UNCATEGORIZED)),
```

Same pattern in `planned_transactions/services.py` (line 125).

In test files, update assertions from `'Uncategorized'` to `TotalsLabel.UNCATEGORIZED`:
- `transactions/tests.py` lines 1217 (`totals_map[('Uncategorized', 'PLN')]`)
- `planned_transactions/tests/test_planned_transactions.py` lines 1186-1187

**Done criteria:**
- [ ] `common/enums.py` created with `TotalsLabel` StrEnum
- [ ] Both services import and use `TotalsLabel.UNCATEGORIZED`
- [ ] Both test files import and use `TotalsLabel.UNCATEGORIZED`
- [ ] No bare `'Uncategorized'` string literals remain in services or tests
- [ ] Tests pass for both apps

**Context estimate:** ~15k tokens
**Verification:**
```bash
cd backend && backend/.venv/bin/python -m pytest transactions/tests.py planned_transactions/tests/ -v
```

---

### Task R12: Backend — Transaction totals `group_by=type,category` support
**Severity:** MEDIUM
**PR Comment:** "Two parallel totals queries on Transactions — would halve requests with a single endpoint."

**Files to modify:**
1. `backend/transactions/schemas.py` — add optional `by_type` and `by_category` fields to `TransactionTotalsResponse`
2. `backend/transactions/api.py` — update `group_by` regex, handle `type,category` case in endpoint
3. `backend/transactions/tests.py` — add test for `group_by=type,category`

**Implementation:**

#### Schema change (`transactions/schemas.py`)

Update `TransactionTotalsResponse`:
```python
class TransactionTotalsResponse(BaseModel):
    """Schema for transaction totals response."""

    totals: list[TransactionTotalsItem] | None = None
    by_type: list[TransactionTotalsItem] | None = None
    by_category: list[TransactionTotalsItem] | None = None
```

#### API change (`transactions/api.py`)

Update the `group_by` pattern to accept `type,category`:
```python
group_by: str = Query('type', pattern=r'^(type|category|type,category)$'),
```

Update the endpoint logic (after `transaction_type` rename from R10):
```python
@router.get('/totals', response=TransactionTotalsResponse, auth=WorkspaceJWTAuth())
def get_transaction_totals(
    request: HttpRequest,
    budget_period_id: int | None = Query(None),
    current_date: date | None = Query(None),
    transaction_type: list[str] | None = Query(None),
    category_id: list[int] | None = Query(None),
    currency: list[str] | None = Query(None),
    search: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    amount_gte: Decimal | None = Query(None),
    amount_lte: Decimal | None = Query(None),
    group_by: str = Query('type', pattern=r'^(type|category|type,category)$'),
):
    """Get aggregated transaction totals grouped by type or category."""
    workspace_id = request.auth.current_workspace_id
    common_kwargs = dict(
        workspace_id=workspace_id,
        budget_period_id=budget_period_id,
        current_date=current_date,
        transaction_type=transaction_type,
        category_id=category_id,
        currency=currency,
        search=search,
        start_date=start_date,
        end_date=end_date,
        amount_gte=amount_gte,
        amount_lte=amount_lte,
    )
    if group_by == 'type,category':
        # NOTE: This issues two separate DB queries. A future optimization could
        # compute both groupings in a single query using conditional aggregation.
        by_type = TransactionService.totals(**common_kwargs, group_by='type')
        by_category = TransactionService.totals(**common_kwargs, group_by='category')
        return {'by_type': by_type, 'by_category': by_category}
    totals = TransactionService.totals(**common_kwargs, group_by=group_by)
    return {'totals': totals}
```

#### Test (`transactions/tests.py`)

Add a test in `TestTransactionTotals`:
```python
def test_totals_group_by_both(self):
    """Test totals with group_by=type,category returns both groupings."""
    Transaction.objects.create(
        budget_period=self.period,
        date=date(2025, 1, 15),
        description='Salary',
        amount=Decimal('5000.00'),
        currency=self.pln_currency,
        type='income',
        created_by=self.user,
        workspace=self.workspace,
    )
    Transaction.objects.create(
        budget_period=self.period,
        date=date(2025, 1, 16),
        description='Groceries',
        amount=Decimal('250.00'),
        currency=self.pln_currency,
        type='expense',
        created_by=self.user,
        workspace=self.workspace,
    )

    data = self.get(
        f'/api/transactions/totals?budget_period_id={self.period.id}&group_by=type,category',
        **self.auth_headers(),
    )
    self.assertStatus(200)
    # Should have by_type and by_category, no totals
    self.assertNotIn('totals', data)
    self.assertEqual(len(data['by_type']), 2)
    self.assertEqual(len(data['by_category']), 1)  # Both uncategorized
    by_type_map = {(t['group'], t['currency']): t['total'] for t in data['by_type']}
    self.assertEqual(by_type_map[('income', 'PLN')], '5000.00')
    self.assertEqual(by_type_map[('expense', 'PLN')], '250.00')
```

Also verify that existing `group_by=type` and `group_by=category` tests still return `totals` (not `by_type`/`by_category`).

**Done criteria:**
- [ ] `TransactionTotalsResponse` has optional `totals`, `by_type`, `by_category` fields
- [ ] `group_by` accepts `type`, `category`, and `type,category`
- [ ] `group_by=type` and `group_by=category` still return `{"totals": [...]}`
- [ ] `group_by=type,category` returns `{"by_type": [...], "by_category": [...]}`
- [ ] Comment about future optimization is present
- [ ] New test passes; existing tests unchanged
- [ ] All tests pass: `cd backend && backend/.venv/bin/python -m pytest transactions/tests.py -v`

**Context estimate:** ~20k tokens
**Verification:**
```bash
cd backend && backend/.venv/bin/python -m pytest transactions/tests.py -v
```

---

### Task R13: Backend — Add `amount_gte` / `amount_lte` test to TestTransactionTotals
**Severity:** LOW
**PR Comment:** "Test gap: TestTransactionTotals doesn't cover amount_gte / amount_lte filters."

**Files to modify:**
1. `backend/transactions/tests.py`

**Implementation:**

Add a test in `TestTransactionTotals` (after `test_totals_search_filter`):

```python
def test_totals_amount_filters(self):
    """Test totals filtered by amount range."""
    Transaction.objects.create(
        budget_period=self.period,
        date=date(2025, 1, 15),
        description='Small expense',
        amount=Decimal('50.00'),
        currency=self.pln_currency,
        type='expense',
        created_by=self.user,
        workspace=self.workspace,
    )
    Transaction.objects.create(
        budget_period=self.period,
        date=date(2025, 1, 16),
        description='Large expense',
        amount=Decimal('500.00'),
        currency=self.pln_currency,
        type='expense',
        created_by=self.user,
        workspace=self.workspace,
    )

    data = self.get(
        f'/api/transactions/totals?budget_period_id={self.period.id}&amount_gte=100',
        **self.auth_headers(),
    )
    self.assertStatus(200)
    totals = data['totals']
    self.assertEqual(len(totals), 1)
    self.assertEqual(totals[0]['total'], '500.00')
```

**Done criteria:**
- [ ] New `test_totals_amount_filters` test in `TestTransactionTotals`
- [ ] Test passes: `cd backend && backend/.venv/bin/python -m pytest transactions/tests.py::TestTransactionTotals::test_totals_amount_filters -v`

**Context estimate:** ~10k tokens
**Verification:**
```bash
cd backend && backend/.venv/bin/python -m pytest transactions/tests.py::TestTransactionTotals -v
```

---

### Task R14: Frontend — Fix parseFloat precision + add TotalsLabel enum + trailing newline
**Severity:** LOW
**PR Comments:**
- "parseFloat loses precision for large or high-precision values"
- "types/index.ts:1894 — file missing trailing newline"
- User requested: "I want proper enum classes" for Uncategorized label

**Files to modify:**
1. `frontend/src/components/common/TotalsSummary.tsx` — replace `parseFloat` with string-based formatting
2. `frontend/src/types/index.ts` — add `TotalsLabel` enum, add trailing newline
3. `frontend/src/types/constants.ts` (new file, OR add to `types/index.ts`) — `TotalsLabel` enum

**Implementation:**

#### parseFloat fix (`TotalsSummary.tsx`)

Replace the `formatAmount` function (line 26-29):
```typescript
// Before:
function formatAmount(total: string): string {
  const num = parseFloat(total)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// After:
function formatAmount(total: string): string {
  // String-based formatting to preserve full Decimal precision from backend.
  // Avoids parseFloat which loses precision for large values (e.g. "123456789012345.67").
  const isNegative = total.startsWith('-')
  const abs = isNegative ? total.slice(1) : total
  const [intPart, decPart = '00'] = abs.split('.')
  const paddedDec = decPart.length < 2 ? decPart.padEnd(2, '0') : decPart.slice(0, 2)
  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const sign = isNegative ? '-' : ''
  return `${sign}${formattedInt}.${paddedDec}`
}
```

#### TotalsLabel enum (`types/index.ts`)

Add at the end of `types/index.ts`, before the final newline:
```typescript
// ============= Enums =============

export enum TotalsLabel {
  /** Display label for records without a category. Synced with backend common.enums.TotalsLabel. */
  UNCATEGORIZED = 'Uncategorized',
}
```

#### Trailing newline (`types/index.ts`)

Ensure `types/index.ts` ends with a newline character after the closing `}` of `TotalsLabel` (or the last interface if adding enum before it).

**Done criteria:**
- [ ] `formatAmount` uses string manipulation (no `parseFloat` or `Number()`)
- [ ] Handles negative values, missing decimal part, and more than 2 decimal places
- [ ] `TotalsLabel` enum added to `types/index.ts`
- [ ] `types/index.ts` ends with a trailing newline
- [ ] Lint passes: `cd frontend && npm run lint`

**Context estimate:** ~10k tokens
**Verification:**
```bash
cd frontend && npm run lint
```

---

### Task R15: Frontend — Rename `type` → `transaction_type` in API + pages
**Severity:** MEDIUM
**Depends on:** Task R10
**PR Comment:** "type shadows Python's type builtin."

**Files to modify:**
1. `frontend/src/api/client.ts` — rename `type` to `transaction_type` in `transactionsApi.getAll`, `transactionsApi.getTotals`, and `transactionsApi.export` params
2. `frontend/src/pages/Transactions.tsx` — rename `type:` to `transaction_type:` in all API call params (lines 197, 228, 249, 301)

**Implementation:**

In `client.ts`:
```typescript
// getAll params: type → transaction_type
getAll: (params?: { budget_period_id?: number; ...; transaction_type?: string[]; ... }) => ...

// getTotals params: type → transaction_type
getTotals: (params?: { ...; transaction_type?: string[]; ... }) => ...

// export params: type → transaction_type
export: (params: { budget_period_id: number; transaction_type?: string }) => ...
```

In `Transactions.tsx`, change all `type: appliedTypes...` to `transaction_type: appliedTypes...`:
- Line 197: `type: appliedTypes.length > 0 ? appliedTypes : undefined` → `transaction_type: ...`
- Line 228: same change
- Line 249: same change
- Line 300-301: `params.type = appliedTypes[0]` → `params.transaction_type = appliedTypes[0]`

Note: The `type` field in `create` and `update` request bodies (e.g., `type: 'expense' | 'income'`) is the model field, not a query parameter — it stays as `type`.

**Done criteria:**
- [ ] `transactionsApi.getAll` params use `transaction_type` instead of `type`
- [ ] `transactionsApi.getTotals` params use `transaction_type` instead of `type`
- [ ] `transactionsApi.export` params use `transaction_type` instead of `type`
- [ ] `Transactions.tsx` passes `transaction_type` in all API calls
- [ ] Request body `type` fields in `create`/`update` are unchanged (model field)
- [ ] Lint passes: `cd frontend && npm run lint`

**Context estimate:** ~12k tokens
**Verification:**
```bash
cd frontend && npm run lint
```

---

### Task R16: Frontend — Single totals query + useMemo + remove `totalItems > 0` gate
**Severity:** MEDIUM
**Depends on:** Task R12
**PR Comments:**
- "Two parallel totals queries → single endpoint would halve requests"
- "totalsFilterKey rebuilt on every render — wrap in useMemo"
- "enabled: !!selectedPeriodId && totalItems > 0 causes delayed totals"

**Files to modify:**
1. `frontend/src/types/index.ts` — update `TransactionTotalsResponse` type
2. `frontend/src/api/client.ts` — update `getTotals` params and return type
3. `frontend/src/pages/Transactions.tsx` — merge two queries into one, add useMemo, remove gate

**Implementation:**

#### Type change (`types/index.ts`)

Update `TransactionTotalsResponse`:
```typescript
export interface TransactionTotalsResponse {
  totals?: TransactionTotalItem[];
  by_type?: TransactionTotalItem[];
  by_category?: TransactionTotalItem[];
}
```

#### API client change (`client.ts`)

Update `getTotals` params to accept `group_by` value `'type,category'`:
```typescript
getTotals: (params?: { ...; group_by?: 'type' | 'category' | 'type,category' }): Promise<TransactionTotalsResponse> =>
  api.get<TransactionTotalsResponse>('/transactions/totals', { params }).then(res => res.data),
```

#### Transactions page (`Transactions.tsx`)

1. **Wrap `totalsFilterKey` in useMemo** (currently line 217):
```typescript
const totalsFilterKey = useMemo(
  () => [selectedPeriodId, searchQuery, appliedStartDate, appliedEndDate, appliedTypes, appliedCategories, appliedCurrencies, appliedAmountMin, appliedAmountMax],
  [selectedPeriodId, searchQuery, appliedStartDate, appliedEndDate, appliedTypes, appliedCategories, appliedCurrencies, appliedAmountMin, appliedAmountMax],
)
```

2. **Merge two `useQuery` calls into one** (currently lines 218-257):
```typescript
const { data: combinedTotalsData } = useQuery({
  queryKey: ['transactions-totals', ...totalsFilterKey],
  queryFn: async () => {
    if (!selectedPeriodId) return null
    return transactionsApi.getTotals({
      group_by: 'type,category',
      budget_period_id: selectedPeriodId,
      search: searchQuery || undefined,
      start_date: appliedStartDate || undefined,
      end_date: appliedEndDate || undefined,
      transaction_type: appliedTypes.length > 0 ? appliedTypes : undefined,
      category_id: appliedCategories.length > 0 ? appliedCategories : undefined,
      currency: appliedCurrencies.length > 0 ? appliedCurrencies : undefined,
      amount_gte: appliedAmountMin ? parseFloat(appliedAmountMin) : undefined,
      amount_lte: appliedAmountMax ? parseFloat(appliedAmountMax) : undefined,
    })
  },
  enabled: !!selectedPeriodId,
})
```

3. **Update derived data** — replace `typeTotalsData` and `categoryTotalsData`:
```typescript
const typeTotalsData = combinedTotalsData?.by_type || []
const categoryTotalsData = combinedTotalsData?.by_category
```

4. **Update TotalsSummary props** — the component already accepts `typeTotals` and `categoryTotals`, so just wire the new derived data:
```typescript
<TotalsSummary
  mode="transactions"
  typeTotals={typeTotalsData}
  categoryTotals={categoryTotalsData}
/>
```

5. **Update query key invalidation** — in mutations (delete, import) and modals, replace the two separate invalidation keys:
```typescript
// Before:
queryClient.invalidateQueries({ queryKey: ['transactions-totals-type'] })
queryClient.invalidateQueries({ queryKey: ['transactions-totals-category'] })

// After:
queryClient.invalidateQueries({ queryKey: ['transactions-totals'] })
```

This applies to:
- `Transactions.tsx` delete mutation (lines 263-264)
- `Transactions.tsx` import mutation (if applicable)
- `TransactionFormModal.tsx` createMutation.onSuccess (lines added in R8)
- `PlannedTransactionFormModal.tsx` mutation.onSuccess (lines added in R8)
- `ExecutePlannedModal.tsx` executeMutation.onSuccess (lines added in R8)

6. **Add `useMemo` import** — if not already imported from React.

**Done criteria:**
- [ ] `TransactionTotalsResponse` type has optional `by_type` and `by_category`
- [ ] `getTotals` accepts `group_by: 'type,category'`
- [ ] Single `useQuery` call replaces two parallel queries
- [ ] `totalsFilterKey` wrapped in `useMemo`
- [ ] `totalItems > 0` gate removed from `enabled` — totals fetch in parallel with list
- [ ] All mutation `invalidateQueries` calls use single `['transactions-totals']` key
- [ ] `TotalsSummary` props unchanged (still receives `typeTotals` and `categoryTotals`)
- [ ] Lint passes: `cd frontend && npm run lint`

**Context estimate:** ~25k tokens
**Verification:**
```bash
cd frontend && npm run lint
```

---

## Progress Tracker
- [x] Task R9: Backend — CurrencyExchanges totals() return dicts + move import
- [x] Task R10: Backend — Rename `type` → `transaction_type` in transactions API
- [x] Task R11: Backend — Add TotalsLabel enum for "Uncategorized"
- [x] Task R12: Backend — Transaction totals `group_by=type,category` support
- [x] Task R13: Backend — Add amount_gte/amount_lte test to TestTransactionTotals
- [x] Task R14: Frontend — Fix parseFloat + add TotalsLabel enum + trailing newline
- [x] Task R15: Frontend — Rename `type` → `transaction_type` in API + pages
- [x] Task R16: Frontend — Single totals query + useMemo + remove totalItems gate

## Dependency Graph
```
R9  (CE dicts)           — standalone
R10 (type rename BE)     ──── R15 (type rename FE)
R11 (Uncategorized enum) — standalone
R12 (group_by BE)        ──── R16 (single query FE)
R13 (test gap)           — standalone
R14 (parseFloat + enum)  — standalone

Parallel groups:
  Group A (backend, no deps):  R9, R10, R11, R12, R13
  Group B (frontend, no deps): R14
  Group C (depends on R10):    R15
  Group D (depends on R12):    R16
```

## Agent Prompt Template
```
## Your Task

1. Read the implementation plan at `.ipm/IMPLEMENTATION_PLAN.md`
2. Find the assigned task and understand what needs to be done
3. Read all files mentioned in the task's "Files to modify" sections
4. Read `.ipm/CODING_SUMMARIES.md` for established patterns and style decisions from previous tasks — follow those conventions
5. Implement the changes as specified
6. Run the verification commands listed in the task
7. Ensure all "Done criteria" are satisfied

## Context
These are PR review fixes for the Amount Totals Summary feature (PR #47, fifth review cycle). The reviewer identified code quality issues: inconsistent service return types, Python builtin shadowing, magic strings, test gaps, precision loss, unnecessary re-renders, redundant network requests, and delayed data fetching.

## Important Rules

- Follow the AGENTS.md coding guidelines
- Backend: run `pytest` and `ruff check` / `ruff format` after changes
- Frontend: run `npm run lint` after changes
- Do NOT commit changes unless explicitly asked
- When the user asks to commit changes:
  1. Update the Progress Tracker in `.ipm/IMPLEMENTATION_PLAN.md` (check the box for the completed task)
  2. Update `.ipm/CODING_SUMMARIES.md` — add a new section summarizing the patterns, decisions, and conventions established or reinforced by this task
```

<!--
## Round 4 Remediation Plan (preserved for reference)

### Progress Tracker (Round 4)
- [x] Task R8: Frontend — Add totals query invalidation to all form modals

### Dependency Graph (Round 4)
Task R8 (totals invalidation in modals) — standalone, no dependencies

## Round 3 Remediation Plan (preserved for reference)

### Progress Tracker (Round 3)
- [x] Task R7: Frontend — Extract TotalsSummary from records table on CurrencyExchangesPage

### Dependency Graph (Round 3)
Task R7 (CurrencyExchangesPage layout) — standalone, no dependencies

## Round 2 Remediation Plan (preserved for reference)

### Progress Tracker (Round 2)
- [x] Task R6: Frontend — Constrain TotalsSummary width and add row hover highlighting

### Dependency Graph (Round 2)
Task R6 (TotalsSummary styling) — standalone, no dependencies

## Round 1 Remediation Plan (preserved for reference)

### Progress Tracker (Round 1)
- [x] Task R1: Backend — Add `group_by` param to transactions `/totals`
- [x] Task R2: Backend — Add `group_by` param to planned transactions `/totals`
- [x] Task R3: Frontend — Update types, API params, and redesign TotalsSummary component
- [x] Task R4: Frontend — Update Transactions page for two-query totals
- [x] Task R5: Frontend — Update Planned + Currency exchanges pages

### Dependency Graph (Round 1)
Task R1 (transactions backend)     ──────┐
Task R2 (planned backend)          ──────┤
Task R3 (frontend types + component) ────┤
                                        ├── Task R4 (transactions frontend) [depends on R3]
                                        └── Task R5 (planned + exchanges frontend) [depends on R3]

Tasks R1, R2, R3 can run in parallel (no code dependencies).
Tasks R4 and R5 can run in parallel (both depend only on R3).

### Original Plan (preserved for reference)

### Progress Tracker (original)
- [x] Task 1: Backend — Transaction totals endpoint + tests
- [x] Task 2: Backend — Planned transactions totals endpoint + tests
- [x] Task 3: Backend — Currency exchanges totals endpoint + tests
- [x] Task 4: Frontend — Types, API client methods, and shared TotalsSummary component
- [x] Task 5: Frontend — Transactions page totals summary integration
- [x] Task 6: Frontend — Planned + Currency exchanges page totals summary integration

### Dependency Graph (original)
Task 1 (transactions backend)  ─────────────────┐
Task 2 (planned backend)       ─────────────────┤
Task 3 (exchanges backend)     ─────────────────┤
                                                  │
Task 4 (frontend types + API + component) ───────┤
                                                  ├── Task 5 (transactions frontend) [depends on 4]
                                                  └── Task 6 (planned + exchanges frontend) [depends on 4]

Tasks 1, 2, 3, 4 can run in parallel (no code dependencies).
Tasks 5 and 6 can run in parallel (both depend only on Task 4).
-->
