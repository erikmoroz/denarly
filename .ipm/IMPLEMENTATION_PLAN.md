# PR Review Fixes: Celery Task Code Quality Improvements

## Overview
Address PR review feedback on `feat/celery-planned-transaction`. Five changes: move imports to module level, inline the dispatch wrapper, use `objects.create()` consistently, use `TransactionService.update_period_balance()` in the task, and extract `recalculate_closing_balance()` to the `PeriodBalance` model to eliminate duplicated closing balance formula across 5 locations.

## Context
These are PR review fixes on the Celery planned transaction implementation. The original plan is preserved as a comment block at the end of this file.

## Task Breakdown

### Task 1: Extract `recalculate_closing_balance()` to `PeriodBalance` model
**Severity:** HIGH
**Problem:** The closing balance formula `opening + income - expenses + exchanges_in - exchanges_out` is duplicated in 5 locations across 4 apps. Any future change to the formula must be applied everywhere, and inconsistencies are easy to introduce.
**PR comments:** tasks.py:85 — "Create a service method to get the closing balance instead of duplication"
**Files to read (context):**
- `backend/period_balances/models.py` (~48 lines) — PeriodBalance model to add method to
- `backend/transactions/services.py` (~521 lines) — `update_period_balance()` has inline formula (line 53)
- `backend/currency_exchanges/services.py` (~298 lines) — `_update_balance()` has inline formula (line 40)
- `backend/period_balances/services.py` (~156 lines) — `recalculate()` (line 123) and `update_opening_balance()` (line 144) have inline formula
- `backend/planned_transactions/tasks.py` (~101 lines) — inline formula (line 85)
**Files to modify:**
- `backend/period_balances/models.py` — add `recalculate_closing_balance()` method
- `backend/transactions/services.py` — replace inline formula with method call
- `backend/currency_exchanges/services.py` — replace inline formula with method call
- `backend/period_balances/services.py` — replace inline formula with method call (2 locations)
- `backend/planned_transactions/tasks.py` — replace inline formula with method call
**Implementation:**

#### Step 1: Add `recalculate_closing_balance()` to `PeriodBalance` model

Add to `backend/period_balances/models.py` after the `Meta` class and before `__str__`:

```python
    def recalculate_closing_balance(self) -> None:
        """Recalculate closing_balance from component fields."""
        self.closing_balance = (
            self.opening_balance
            + self.total_income
            - self.total_expenses
            + self.exchanges_in
            - self.exchanges_out
        )
```

#### Step 2: Update `backend/transactions/services.py`

In `update_period_balance()` (around line 43), replace lines 53-59:

```python
# BEFORE:
        balance.closing_balance = (
            balance.opening_balance
            + balance.total_income
            - balance.total_expenses
            + balance.exchanges_in
            - balance.exchanges_out
        )

# AFTER:
        balance.recalculate_closing_balance()
```

#### Step 3: Update `backend/currency_exchanges/services.py`

In `_update_balance()` (around line 38), replace lines 40-46:

```python
# BEFORE:
        balance.closing_balance = (
            balance.opening_balance
            + balance.total_income
            - balance.total_expenses
            + balance.exchanges_in
            - balance.exchanges_out
        )

# AFTER:
        balance.recalculate_closing_balance()
```

#### Step 4: Update `backend/period_balances/services.py`

**4a.** In `recalculate()` (around line 67), replace line 123:

```python
# BEFORE:
        balance.closing_balance = balance.opening_balance + income - expenses + exchanges_in - exchanges_out

# AFTER:
        balance.recalculate_closing_balance()
```

**4b.** In `update_opening_balance()` (around line 138), replace lines 144-150:

```python
# BEFORE:
            balance.closing_balance = (
                balance.opening_balance
                + balance.total_income
                + balance.exchanges_in
                - balance.total_expenses
                - balance.exchanges_out
            )

# AFTER:
            balance.recalculate_closing_balance()
```

**Important:** Note that the original formula in `update_opening_balance()` has a different operand order (`+ income + exchanges_in - expenses - exchanges_out` vs `+ income - expenses + exchanges_in - exchanges_out`). Mathematically identical. The `recalculate_closing_balance()` method uses the canonical order.

#### Step 5: Update `backend/planned_transactions/tasks.py`

Replace lines 85-91:

```python
# BEFORE:
        balance.closing_balance = (
            balance.opening_balance
            + balance.total_income
            - balance.total_expenses
            + balance.exchanges_in
            - balance.exchanges_out
        )

# AFTER:
        balance.recalculate_closing_balance()
```

**Done criteria:**
- [ ] `PeriodBalance.recalculate_closing_balance()` method exists and computes the formula
- [ ] All 5 inline formula locations replaced with `balance.recalculate_closing_balance()`
- [ ] No inline closing balance formula remains outside `period_balances/models.py`
- [ ] All tests pass: `cd backend && .venv/bin/python -m pytest transactions/ currency_exchanges/ period_balances/ planned_transactions/ -v`
- [ ] Lint passes: `cd backend && uv run ruff check . && uv run ruff format --check .`

**Context estimate:** ~55k tokens (5 files to read ~1124 lines, 5 files to modify)
**Verification:**
```bash
cd backend && .venv/bin/python -m pytest transactions/ currency_exchanges/ period_balances/ planned_transactions/ -v
cd backend && uv run ruff check . && uv run ruff format --check .
```

---

### Task 2: Move imports to module level in `tasks.py`
**Severity:** MEDIUM
**Problem:** Function-level imports in the Celery task were added to avoid "Django app-loading issues with Celery workers", but this is overly cautious — `config/celery.py` calls `autodiscover_tasks()` after Django is fully set up, and the existing `common/tasks.py` email task already uses module-level imports successfully.
**PR comments:** tasks.py:19 — "why did you put import inside function instead file level?", tasks.py:55 — "why import is here?"
**Files to read (context):**
- `backend/planned_transactions/tasks.py` (~101 lines) — current state with function-level imports
- `backend/common/tasks.py` (~24 lines) — existing Celery task with module-level imports (pattern to follow)
**Files to modify:**
- `backend/planned_transactions/tasks.py` — move imports to module level
**Implementation:**

#### Step 1: Move imports to module level

Replace the current file top (lines 1-8 + function-body imports at lines 19-22 and 55):

```python
# BEFORE (lines 1-8):
"""Celery tasks for the planned_transactions app."""

import logging

from celery import shared_task
from django.db import transaction as db_transaction

logger = logging.getLogger(__name__)

# ... plus function-body imports at lines 19-22:
    from common.services.base import get_or_create_period_balance
    from planned_transactions.exceptions import PlannedTransactionNoActivePeriodError
    from planned_transactions.models import PlannedTransaction
    from transactions.models import Transaction

# ... plus function-body import at line 55:
        from budget_periods.models import BudgetPeriod

# AFTER:
"""Celery tasks for the planned_transactions app."""

import logging

from budget_periods.models import BudgetPeriod
from celery import shared_task
from common.services.base import get_or_create_period_balance
from django.db import transaction as db_transaction
from planned_transactions.exceptions import PlannedTransactionNoActivePeriodError
from planned_transactions.models import PlannedTransaction
from transactions.models import Transaction

logger = logging.getLogger(__name__)
```

Then remove the 5 `from ... import ...` lines inside the function body (lines 19-22 and 55).

**Import order:** stdlib (`logging`) → third-party (`celery`, `django`) → local apps, alphabetically — following AGENTS.md import conventions.

**Note:** This task should be done AFTER Task 1, since Task 1 modifies the same `tasks.py` file (replacing the inline closing balance formula). If done first, the line numbers for import locations will shift.

**Done criteria:**
- [ ] All imports are at module level in `tasks.py`
- [ ] No function-body imports remain
- [ ] Import order follows AGENTS.md: stdlib → third-party → local
- [ ] Task still works: `cd backend && .venv/bin/python -c "from planned_transactions.tasks import execute_planned_transaction; print('OK')"`
- [ ] Tests pass: `cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v`
- [ ] Lint passes: `cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/`

**Context estimate:** ~20k tokens (2 files to read ~125 lines, 1 file to modify)
**Verification:**
```bash
cd backend && .venv/bin/python -c "from planned_transactions.tasks import execute_planned_transaction; print('OK')"
cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v
cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/
```

---

### Task 3: Inline `_dispatch_execution_task` and use `objects.create()` consistently
**Severity:** MEDIUM
**Problem:** The `_dispatch_execution_task` wrapper adds indirection for a single line. Callers already know about Celery (they call `refresh_from_db()` after). Also, `services.py` `create()` uses `PlannedTransaction(...) + save()` inconsistently with `PlannedTransaction.objects.create()` on the next code path.
**PR comments:** services.py:96 — "Why do we need a wrapper around execute_planned_transaction.delay(planned_id)?", services.py:174 — "Use service class instead of directly call Model class"
**Files to read (context):**
- `backend/planned_transactions/services.py` (~347 lines) — current state
- `backend/planned_transactions/tasks.py` — to import the task function
**Files to modify:**
- `backend/planned_transactions/services.py` — remove `_dispatch_execution_task`, inline `.delay()` calls, use `objects.create()` consistently
**Implementation:**

#### Step 1: Remove `_dispatch_execution_task` method

Delete lines 95-100 (the `_dispatch_execution_task` static method).

#### Step 2: Add import for the Celery task

Add near the other planned_transactions imports:

```python
from planned_transactions.tasks import execute_planned_transaction
```

#### Step 3: Replace all `_dispatch_execution_task` calls with inline `.delay()`

In `create()` — replace:
```python
# BEFORE:
            PlannedTransactionService._dispatch_execution_task(planned.id)
# AFTER:
            execute_planned_transaction.delay(planned.id)
```

In `update()` — replace:
```python
# BEFORE:
            PlannedTransactionService._dispatch_execution_task(planned.id)
# AFTER:
            execute_planned_transaction.delay(planned.id)
```

In `execute()` — replace:
```python
# BEFORE:
        PlannedTransactionService._dispatch_execution_task(planned.id)
# AFTER:
        execute_planned_transaction.delay(planned.id)
```

#### Step 4: Use `objects.create()` consistently in `create()` method

Replace the `status='done'` branch (lines 173-191) to use `PlannedTransaction.objects.create()` inside the `with` block:

```python
        if data.status == 'done':
            with db_transaction.atomic():
                planned = PlannedTransaction.objects.create(
                    workspace_id=workspace_id,
                    budget_period_id=period_id,
                    name=data.name,
                    amount=data.amount,
                    currency=currency,
                    category_id=data.category_id,
                    planned_date=data.planned_date,
                    status='done',
                    payment_date=data.planned_date,
                    created_by=user,
                    updated_by=user,
                )
            execute_planned_transaction.delay(planned.id)
            planned.refresh_from_db()
            return planned
```

Do the same in `update()` — wrap the `status='done'` transition in `with db_transaction.atomic():` and use `.save()` (already correct — update mutates an existing instance).

Do the same in `execute()` — wrap the save in `with db_transaction.atomic():` (already correct).

**Done criteria:**
- [ ] `_dispatch_execution_task` method is completely removed
- [ ] `execute_planned_transaction` is imported at module level in `services.py`
- [ ] All 3 callers use `execute_planned_transaction.delay(planned.id)` directly
- [ ] `create()` uses `PlannedTransaction.objects.create()` for the `status='done'` branch
- [ ] `create()` uses `PlannedTransaction.objects.create()` for the non-done branch (unchanged)
- [ ] Tests pass: `cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v`
- [ ] Lint passes: `cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/`

**Context estimate:** ~25k tokens (2 files to read ~448 lines, 1 file to modify)
**Verification:**
```bash
cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v
cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/
```

---

### Task 4: Use `TransactionService.update_period_balance()` in the Celery task
**Severity:** MEDIUM
**Problem:** The Celery task duplicates balance update logic that already exists in `TransactionService.update_period_balance()`. The task should use the service method instead.
**PR comments:** tasks.py:70 — "Use service class to create Transaction"
**Files to read (context):**
- `backend/planned_transactions/tasks.py` — current task implementation
- `backend/transactions/services.py` — `update_period_balance()` method (line 43)
**Files to modify:**
- `backend/planned_transactions/tasks.py` — replace inline balance update with `TransactionService.update_period_balance()` call
**Implementation:**

#### Step 1: Add import for TransactionService

Add at module level (after the imports from Task 2):

```python
from transactions.services import TransactionService
```

#### Step 2: Replace inline balance update with service call

Replace lines 83-92 (the `get_or_create_period_balance` + inline formula + `save`):

```python
# BEFORE:
        balance = get_or_create_period_balance(period.id, planned.currency)
        balance.total_expenses += planned.amount
        balance.closing_balance = (
            balance.opening_balance
            + balance.total_income
            - balance.total_expenses
            + balance.exchanges_in
            - balance.exchanges_out
        )
        balance.save(update_fields=['total_expenses', 'closing_balance'])

# AFTER:
        TransactionService.update_period_balance(period.id, planned.currency, 'expense', planned.amount, 'add')
```

#### Step 3: Remove now-unused import

Remove `get_or_create_period_balance` from the module-level imports (no longer used in this file after Task 1 extracted the formula and this task uses the service instead).

**Important:** `TransactionService.update_period_balance()` calls `get_or_create_period_balance()` internally, then updates the income/expenses field and calls `balance.save()` (without `update_fields`). This is functionally equivalent to the inline code. The only difference is that `update_period_balance()` calls `balance.save()` without `update_fields`, which saves all fields. This is slightly less targeted but is the standard pattern used everywhere else in the codebase.

**Done criteria:**
- [ ] `TransactionService` is imported in `tasks.py`
- [ ] Inline balance update replaced with `TransactionService.update_period_balance()` call
- [ ] `get_or_create_period_balance` import removed from `tasks.py`
- [ ] Tests pass: `cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v`
- [ ] Lint passes: `cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/`

**Context estimate:** ~25k tokens (2 files to read ~622 lines, 1 file to modify)
**Verification:**
```bash
cd backend && .venv/bin/python -m pytest planned_transactions/tests/ -v
cd backend && uv run ruff check planned_transactions/ && uv run ruff format --check planned_transactions/
```

---

## Progress Tracker
- [x] Task 1: Extract `recalculate_closing_balance()` to PeriodBalance model
- [x] Task 2: Move imports to module level in `tasks.py`
- [x] Task 3: Inline `_dispatch_execution_task` and use `objects.create()` consistently
- [x] Task 4: Use `TransactionService.update_period_balance()` in the Celery task

## Dependency Graph
```
Task 1 (recalculate_closing_balance extraction — touches tasks.py)
  └── Task 2 (move imports — touches tasks.py, must be after Task 1)
  └── Task 4 (use TransactionService — touches tasks.py, must be after Task 1)
Task 3 (inline dispatch + objects.create — touches services.py, independent)
```

Tasks 2 and 4 both modify `tasks.py` and should be done sequentially (2 then 4, or together). Task 3 is independent.

## Agent Prompt Template
```
## Your Task

1. Read the implementation plan at `.ipm/IMPLEMENTATION_PLAN.md`
2. Find Task {TASK_NUMBER} and understand what needs to be done
3. Read all files mentioned in the task's "Files to modify" / "Files to create" sections
4. Read `.ipm/CODING_SUMMARIES.md` for established patterns and style decisions from previous tasks — follow those conventions
5. Implement the changes as specified
6. Run the verification commands listed in the task
7. Ensure all "Done criteria" are satisfied

## Important Rules

- Follow the AGENTS.md coding guidelines
- Backend: run `uv run ruff check --fix .` and `uv run ruff format .` after changes
- Backend: run relevant tests after changes
- Frontend: run `npm run lint` after changes
- Do NOT commit changes unless explicitly asked
- When the user asks to commit changes:
  1. Update the Progress Tracker in `.ipm/IMPLEMENTATION_PLAN.md` (check the box for the completed task)
  2. Update `.ipm/CODING_SUMMARIES.md` — add a new section summarizing the patterns, decisions, and conventions established or reinforced by this task

## Context

These are PR review fixes on the `feat/celery-planned-transaction` branch. The original implementation plan is preserved below as a reference. The PR is at https://github.com/erikmoroz/denarly/pull/60
```

---

<!-- ORIGINAL PLAN (preserved for reference)
# Move Planned Transaction Execution to Celery Background Task

## Overview
Move the Transaction creation + PeriodBalance update from the synchronous `_execute_side_effects()` method in `PlannedTransactionService` to a background Celery task...

## Progress Tracker
- [x] Task 1: Create Celery task and refactor service to dispatch it
- [x] Task 2: Update tests for Celery-based execution
-->
