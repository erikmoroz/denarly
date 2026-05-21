# Coding Summaries

Patterns, decisions, and conventions established or reinforced during implementation.

---

## Task 1: Create Celery task and refactor service

### Celery Task Pattern (first background task in the codebase)
- **File:** `planned_transactions/tasks.py`
- Use `@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)` for Celery tasks
- Heavy model imports go inside function body to avoid Django app-loading issues in Celery workers
- **Double idempotency guard:** check `transaction_id` outside the lock (fast path for retries), then again inside `select_for_update()` (prevents race conditions)
- **`select_for_update()` + `select_related()` caveat:** cannot combine on nullable FKs — PostgreSQL raises "FOR UPDATE cannot be applied to the nullable side of an outer join". Remove `select_related` from locked queries with nullable FKs.
- **Retry vs silent return:** Raise domain exceptions for transient failures (missing period — may be created later). Return silently for permanent failures (missing record, missing `payment_date`) — no point retrying.
- **`get()` with `select_for_update()`** is acceptable per AGENTS.md exception to the `filter().first()` convention.

### Service Dispatch Pattern
- **`_dispatch_execution_task`** static method on the service class calls `task.delay()` — private-methods-first ordering (before public methods)
- **Pattern B from AGENTS.md:** `with db_transaction.atomic():` block + dispatch after block for `status='done'` transitions
- **`refresh_from_db()` after dispatch:** Required in EAGER mode (tests) because the task runs synchronously and updates `transaction_id` in the DB. Without it, the returned object has `transaction_id=None`.
- **Period validation in `execute()`:** The `execute()` method must validate that a period covers the `payment_date` before saving `status='done'`. This maintains the same API error behavior (400 for no period) that tests expect.
- Removed `@db_transaction.atomic` decorators from `create`, `update`, `execute` — each now uses inline `with db_transaction.atomic():` only where needed (saving `status='done'`).

### Import Cleanup
- Removed `Transaction` and `get_or_create_period_balance` from `services.py` — the Celery task now owns these concerns.

---

## Task 2: Update tests for Celery-based execution

### Testing Celery Tasks
- **Test class:** `TestExecutePlannedTransactionTask` extends the same `PlannedTransactionTestCase` base class used by all other planned transaction test classes
- **Direct task invocation:** Call `execute_planned_transaction(planned_id)` directly (not via `.delay()`) — in test settings `CELERY_TASK_ALWAYS_EAGER = True` makes `.delay()` synchronous anyway, but calling directly gives more control and clearer error messages
- **Test setup pattern:** Each test sets `status='done'` and `payment_date` on the planned transaction before calling the task directly — this mirrors what the service does synchronously before dispatching
- **Idempotency test:** Call the task twice, assert no duplicate Transactions and no double-counted PeriodBalance
- **Graceful handling test:** Non-existent planned ID returns silently (no raise) — prevents infinite retries
- **Error propagation test:** Missing budget period raises `PlannedTransactionNoActivePeriodError` — this is what triggers Celery's `autoretry_for`

---

## PR Review Fix: Task 1 — Extract `recalculate_closing_balance()` to PeriodBalance model

### Closing Balance Formula Deduplication
- **Method:** `PeriodBalance.recalculate_closing_balance()` — computes `opening_balance + total_income - total_expenses + exchanges_in - exchanges_out`
- **Canonical formula location:** The model method is the single source of truth. All 5 previous inline locations now delegate to this method.
- **Files updated:** `transactions/services.py`, `currency_exchanges/services.py`, `period_balances/services.py` (2 locations), `planned_transactions/tasks.py`
- **Mathematical equivalence:** Some locations had different operand order (e.g., `+ income + exchanges_in - expenses - exchanges_out` vs `+ income - expenses + exchanges_in - exchanges_out`). All are mathematically identical and now use the canonical order.

---

## PR Review Fix: Task 2 — Move imports to module level in `tasks.py`

### Celery Task Import Pattern (revised)
- **Previous pattern (from original Task 1):** Heavy model imports inside function body to avoid Django app-loading issues in Celery workers
- **Revised pattern:** Module-level imports are fine because `config/celery.py` calls `autodiscover_tasks()` after Django is fully set up. The existing `common/tasks.py` email task already uses module-level imports successfully.
- **Import order:** stdlib (`logging`) → third-party (`celery`, `django`) → local apps (alphabetically)

---

## PR Review Fix: Task 3 — Inline `_dispatch_execution_task`, use `objects.create()` consistently

### Dispatch Pattern Simplification
- **Removed:** `_dispatch_execution_task` wrapper method — added indirection for a single `.delay()` call
- **Pattern:** Call `execute_planned_transaction.delay(planned.id)` directly at call sites
- **Import:** `from planned_transactions.tasks import execute_planned_transaction` at module level in `services.py`

### Consistent Object Creation
- **Pattern:** Use `PlannedTransaction.objects.create()` instead of `PlannedTransaction(...) + save()` in all service `create()` paths
- **Exception:** `bulk_create()` in import still uses `PlannedTransaction(...)` — correct for bulk operations

---

## PR Review Fix: Task 4 — Use `TransactionService.update_period_balance()` in Celery task

### Balance Update Delegation
- **Previous:** Celery task called `get_or_create_period_balance()` directly and mutated fields inline
- **Now:** Delegates to `TransactionService.update_period_balance(period.id, planned.currency, 'expense', planned.amount, 'add')` — single source of truth for balance updates
- **Removed import:** `get_or_create_period_balance` no longer needed in `tasks.py`
