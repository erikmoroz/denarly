# Code Review Fixes — Email Infrastructure (Round 5)

## Overview

Fix two issues found during code review of the email infrastructure feature branch (round 5):

1. **No rate limiting on `/reset-password` endpoint** (Medium) — Only `/forgot-password` is rate-limited (3/hour). An attacker who obtains a valid reset token could brute-force it. While `default_token_generator` tokens are one-time-use and invalidated on password change, adding rate limiting is a defense-in-depth measure consistent with other auth endpoints.
2. **`VerifyEmailPage` doesn't refresh auth context after verification** (Low) — On successful verification, the page doesn't call `updateUser()` to refresh `email_verified` in the auth context. Users who verify while logged in will see stale "Not verified" status until they refresh or re-authenticate. `ConfirmEmailChangePage` already handles this correctly.

---

## Progress Tracker

- [x] Task 1: Backend — Add rate limiting to `/reset-password` endpoint
- [x] Task 2: Frontend — Refresh auth context after email verification in `VerifyEmailPage`

---

## Task 1: Backend — Add rate limiting to `/reset-password` endpoint

**Context budget: ~1k tokens**

### Goal

Add IP-based rate limiting to the `POST /api/auth/reset-password` endpoint to prevent brute-force attacks on password reset tokens.

### Background

The `/forgot-password` endpoint is rate-limited at 3 requests/hour, but the actual `/reset-password` endpoint (which consumes the token and sets a new password) has no rate limiting. An attacker who intercepts a reset token (e.g., via email access) could attempt to brute-force it. While `default_token_generator` tokens are one-time-use and invalidated on password change, rate limiting adds defense-in-depth.

The project uses a custom `@rate_limit` decorator (in `common/throttle.py`) based on Django's cache framework and client IP. All other auth endpoints already use it.

### Files to modify

- `backend/core/api.py`

### Implementation details

#### `core/api.py` — `reset_password` endpoint (lines 134-149)

Add the `@rate_limit` decorator. Use a limit of 5 requests per 60 seconds — tighter than general endpoints but allowing for legitimate retries (e.g., expired token → request new one → try again):

```python
@router.post('/reset-password', response={200: MessageOut, 400: DetailOut, 429: DetailOut})
@rate_limit('reset_password', limit=5, period=60)
def reset_password(request, data: ResetPasswordIn):
    ...
```

Add `429: DetailOut` to the response types so the rate limiter's `HttpError(429)` is documented in the OpenAPI schema.

### Done criteria

- [ ] `@rate_limit` decorator added to `reset_password`
- [ ] `429: DetailOut` added to response types
- [ ] Other rate-limited endpoints in the file use the same pattern (verify consistency)
- [ ] Linting passes
- [ ] Password reset tests pass

### Verification commands

```bash
cd backend
uv run ruff check --fix . && uv run ruff format .
pytest core/tests/test_password_reset.py -v
```

---

## Task 2: Frontend — Refresh auth context after email verification in `VerifyEmailPage`

**Context budget: ~1.5k tokens**

### Goal

Update `VerifyEmailPage` to fetch the current user and update the auth context after successful email verification, so `email_verified` is immediately fresh in the UI.

### Background

`ConfirmEmailChangePage` already does this correctly (lines 22-24):

```typescript
await authApi.confirmEmailChange(token)
const updatedUser = await authApi.getCurrentUser()
updateUser(updatedUser)
```

`VerifyEmailPage` only calls `authApi.verifyEmail(token)` and sets state to `'success'` without updating the auth context. If a user is logged in (e.g., in another tab or same session) and verifies their email, navigating back to the app will still show `email_verified: false` in the auth context until they refresh or re-authenticate.

The `useAuth` hook's `updateUser` accepts `Partial<User>` and merges it into the existing user state. However, per AGENTS.md, fetching the full user object from the server is preferred over partial patches to ensure full sync.

### Files to modify

- `frontend/src/pages/VerifyEmailPage.tsx`

### Implementation details

#### `VerifyEmailPage.tsx`

1. Import `useAuth` from `../contexts/AuthContext`.

2. Add `const { updateUser } = useAuth()` inside the component.

3. In the `verify` function inside `useEffect`, after `await authApi.verifyEmail(token)` succeeds, fetch the updated user and call `updateUser`:

```typescript
try {
  await authApi.verifyEmail(token)
  try {
    const updatedUser = await authApi.getCurrentUser()
    updateUser(updatedUser)
  } catch {
    // Non-critical: verification succeeded, but context refresh failed.
    // The user will see correct status on next page load or re-auth.
  }
  setState('success')
} catch {
  setState('error')
}
```

4. Add `updateUser` to the `useEffect` dependency array.

**Why the inner try/catch?** The user fetch is non-critical — the verification itself succeeded. If the user isn't logged in (no token in localStorage), `getCurrentUser` will 401 and the interceptor will redirect to login. We don't want that redirect to prevent the success state from showing. The inner catch swallows the fetch failure silently, which is acceptable since verification itself worked.

### Done criteria

- [ ] `useAuth` imported and `updateUser` destructured
- [ ] After successful verification, `authApi.getCurrentUser()` + `updateUser()` called
- [ ] Inner try/catch wraps the user fetch (non-critical failure)
- [ ] `updateUser` in `useEffect` dependency array
- [ ] Frontend lint passes

### Verification commands

```bash
cd frontend
npm run lint
```

---

## Agent Prompt Template

```
## Task Assignment

**TASK_NUMBER = [x]**

You are implementing a task from the code review fix plan (round 5).

## Your Task

1. Read the implementation plan at `.ipm/IMPLEMENTATION_PLAN.md`
2. Find Task {TASK_NUMBER} and understand what needs to be done
3. Read all files mentioned in the task's "Files to modify" / "Files to create" sections
4. Read AGENTS.md for coding conventions
5. Read `.ipm/CODING_SUMMARIES.md` for established patterns and style decisions from previous tasks — follow those conventions
6. Implement the changes as specified
7. Run the verification commands listed in the task
8. Ensure all "Done criteria" are satisfied

## Important Rules

- Follow the AGENTS.md coding guidelines
- Backend: run `uv run ruff check --fix .` and `uv run ruff format .` after changes
- Backend: run relevant tests after changes
- Frontend: run `npm run lint` after changes
- Do NOT commit changes unless explicitly asked
- When the user asks to commit changes:
  1. Update the Progress Tracker in `.ipm/IMPLEMENTATION_PLAN.md` (check the box for the completed task)
  2. Update `.ipm/CODING_SUMMARIES.md` — add a new section summarizing the patterns, decisions, and conventions established or reinforced by this task. Include files changed, the pattern name, and a brief description so future tasks can reference it.

## Context

This is part of fixing code review issues found in the email infrastructure feature (round 5). The issues are:

1. **Backend (Security)**: No rate limiting on `/reset-password` endpoint — add `@rate_limit` decorator consistent with other auth endpoints
2. **Frontend (Bug)**: `VerifyEmailPage` doesn't refresh auth context after verification — `email_verified` stays stale until next re-auth

Work on ONLY Task [x]. Do not modify files outside the task's scope.
```
