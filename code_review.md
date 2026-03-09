# Code Review — PR #22 GDPR Compliance

> Source: review of `feature/gdpr-compliance` → `main`
> Reviewer notes converted to actionable tasks for developers + AI agents.

---

## 🔴 Critical (must fix before merge)

### 1. Consent records deleted on CASCADE — contradicts stated GDPR retention policy

- [x] **Fix**

**Problem:**
`UserConsent.user` is a `CASCADE` FK (`backend/users/models.py:92`). When `delete_account()`
deletes the user, all their consent records are deleted too. But
`docs/gdpr/data-processing-records.md` (Processing Activity 3) explicitly states:
> Retention Period: Retained for legal compliance purposes even after account deletion

This is an internal contradiction and a potential compliance issue — regulators may ask for
proof that a user consented to terms at a specific time and IP, even after they left.

**Acceptance criteria:**
- After `DELETE /api/users/me`, `UserConsent` rows for that user still exist in DB with
  `user_id = NULL`.
- All existing deletion tests still pass.
- New test `test_consent_records_survive_account_deletion` added and green.
- `UserConsent.__str__` and admin panel handle `user=None` gracefully.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Step 1 — Change the FK on `UserConsent` model**
File: `backend/users/models.py`

Line 92 — change:
```python
user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consents')
```
to:
```python
user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consents')
```

Line 105–107 — fix `__str__` to handle `user=None`:
```python
def __str__(self):
    status = 'withdrawn' if self.withdrawn_at else 'active'
    email = self.user.email if self.user else '[deleted]'
    return f'{email} - {self.consent_type} v{self.version} ({status})'
```

**Step 2 — Generate migration**
```bash
cd backend
python manage.py makemigrations users --name userconsent_user_nullable
```
This creates `backend/users/migrations/0005_userconsent_user_nullable.py`.
Verify the generated migration alters the `user` field to nullable with `SET_NULL`.

**Step 3 — Update admin panel for null user**
File: `backend/users/admin.py`

Line 46 — `search_fields = ('user__email',)` will still work with nullable FK.
Line 44 — `list_display` includes `'user'` which Django renders as `None` for null FKs.
No changes needed unless you want a nicer display; optionally add:
```python
@admin.display(description='User')
def user_display(self, obj):
    return obj.user.email if obj.user else '[deleted]'
```
and replace `'user'` with `user_display` in `list_display`.

**Step 4 — Update `delete_account()` docstring**
File: `backend/users/services.py`

Line 187 — change the docstring step 5 from:
```
5. Delete user record (CASCADE: preferences, consents, memberships; SET_NULL: audit refs)
```
to:
```
5. Delete user record (CASCADE: preferences; SET_NULL: consents, audit refs)
```

Line 244 — change the comment:
```python
# Delete user — CASCADE: UserPreferences, UserConsent
```
to:
```python
# Delete user — CASCADE: UserPreferences
# SET_NULL: UserConsent (retained for GDPR audit), created_by/updated_by on financial models
```

**Step 5 — Add test for consent record retention**
File: `backend/users/tests/test_account_deletion.py`

Add after the last test (after line 113):
```python
def test_consent_records_survive_account_deletion(self):
    """Consent records should be retained (with user=NULL) after account deletion."""
    from users.models import UserConsent

    UserConsent.objects.create(user=self.user, consent_type='terms_of_service', version='1.0')
    UserConsent.objects.create(user=self.user, consent_type='privacy_policy', version='1.0')
    consent_ids = list(UserConsent.objects.filter(user=self.user).values_list('id', flat=True))

    self.client.delete(
        '/api/users/me',
        {'password': self.user_password},
        content_type='application/json',
        **self.auth_headers(),
    )

    # User is gone, but consent records survive with user=NULL
    self.assertFalse(User.objects.filter(id=self.user.id).exists())
    surviving = UserConsent.objects.filter(id__in=consent_ids)
    self.assertEqual(surviving.count(), 2)
    for consent in surviving:
        self.assertIsNone(consent.user)
```

**Step 6 — Run & verify**
```bash
cd backend
python manage.py migrate
pytest users/tests/test_account_deletion.py -v
pytest -v  # full suite
```

**Step 7 — Documentation check**
Review and update if needed:
- [x] `docs/gdpr/data-processing-records.md` — confirm the retention statement for
  Processing Activity 3 is now accurate (it already says "retained"; no change needed).
- [x] `docs/gdpr/README.md` — cascade behaviour section; update if it mentions
  `UserConsent` being deleted on account deletion.
- [x] `CLAUDE.md` — GDPR section mentions `delete_account`; verify wording is still correct.
- [x] `AGENTS.md` — same check.
- [x] `backend/README.md` — no change expected.

</details>

---

### 2. Move legal templates to Django app + use Django template loader (fixes `lru_cache` + `override_settings` flakiness)

- [x] **Fix**

**Problem (original):**
`get_terms()` and `get_privacy()` in `backend/core/legal.py` use `@lru_cache(maxsize=None)`.
The cache stores the **fully rendered** content (template variables already substituted).
Tests in `backend/core/tests/test_legal.py` use `override_settings(...)` expecting fresh
rendering, but the cache returns stale results.

**Problem (structural):**
Legal templates live in `docs/legal/` — a general knowledge folder. They're runtime assets
served via API, not developer documentation. `core/legal.py` uses `Path(__file__).resolve()
.parent.parent.parent` to escape the backend boundary to reach them.

**Solution:**
Move templates into `backend/core/templates/legal/` and use Django's built-in template
loader (`render_to_string`). Since `APP_DIRS: True` is set in `config/settings.py:81` and
`core` is in `INSTALLED_APPS`, Django auto-discovers templates in `core/templates/`.

This solves both problems at once:
- **No `lru_cache` needed** — Django caches the compiled template, not the rendered output.
  Every `render_to_string()` call renders fresh with current settings.
- **`override_settings` works** — each render reads live `settings.*` values.
- **No `Path` hacking** — standard Django template resolution.

**Acceptance criteria:**
- Legal templates live at `backend/core/templates/legal/{privacy-policy,terms-of-service}.md`.
- `core/legal.py` uses `render_to_string` — no `Path`, no `lru_cache`.
- Running `pytest backend/core/tests/test_legal.py` in any order produces the same result.
- Running the full test suite passes.
- `docs/legal/` no longer exists (or only contains non-template files).

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Step 1 — Move the template files**
```bash
mkdir -p backend/core/templates/legal
mv docs/legal/privacy-policy.md backend/core/templates/legal/privacy-policy.md
mv docs/legal/terms-of-service.md backend/core/templates/legal/terms-of-service.md
```

If `docs/legal/` is now empty, remove it:
```bash
rmdir docs/legal/
```

**Step 2 — Rewrite `backend/core/legal.py`**

Replace the entire file with:
```python
"""Reads and renders legal documents (Privacy Policy, Terms of Service)."""

from django.conf import settings
from django.template.loader import render_to_string


def _get_legal_context() -> dict:
    """Build template context from Django settings."""
    return {
        'operator_name': settings.LEGAL_OPERATOR_NAME,
        'operator_type': settings.LEGAL_OPERATOR_TYPE,
        'contact_email': settings.LEGAL_CONTACT_EMAIL,
        'contact_address': settings.LEGAL_CONTACT_ADDRESS,
        'jurisdiction': settings.LEGAL_JURISDICTION,
        'is_individual': settings.LEGAL_OPERATOR_TYPE == 'individual',
        'is_company': settings.LEGAL_OPERATOR_TYPE == 'company',
    }


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from content. Returns (meta_dict, content_str)."""
    if not text.startswith('---\n'):
        return {}, text

    try:
        end = text.index('\n---\n', 4)
    except ValueError:
        return {}, text

    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            meta[key.strip()] = value.strip().strip('"\'')

    return meta, text[end + 5:].strip()


def _render(template_name: str) -> dict:
    """Render a legal document template and extract frontmatter metadata."""
    rendered = render_to_string(template_name, _get_legal_context())
    meta, content = _parse_frontmatter(rendered)
    return {
        'version': meta.get('version', '1.0'),
        'effective_date': meta.get('effective_date', ''),
        'content': content,
    }


def get_terms() -> dict:
    """Return rendered Terms of Service with version and effective date."""
    return _render('legal/terms-of-service.md')


def get_privacy() -> dict:
    """Return rendered Privacy Policy with version and effective date."""
    return _render('legal/privacy-policy.md')
```

Key changes vs. the old version:
- No `from functools import lru_cache` — removed entirely.
- No `from pathlib import Path` — removed entirely.
- No `LEGAL_DIR` constant — removed entirely.
- No `@lru_cache` decorators — Django handles template caching.
- `render_to_string('legal/...', context)` replaces manual `Path.read_text()` +
  `Template(text).render(Context(ctx))`.
- `_parse_frontmatter` extracts metadata from the rendered output (frontmatter YAML has
  no template variables, so rendering it is harmless).

**Step 3 — Update `backend/core/tests/test_legal.py`**

Remove the `_read_raw` import (no longer exists). Update imports:
```python
from core.legal import _get_legal_context, get_privacy, get_terms
```

Remove any `cache_clear()` calls in `setUp`/`tearDown` — no longer needed since there's
no `lru_cache`.

The `override_settings` tests will now work correctly without any cache management because
`render_to_string` reads `settings.*` on every call via `_get_legal_context()`.

No test logic changes needed — only import cleanup.

**Step 4 — Verify**
```bash
cd backend
pytest core/tests/test_legal.py -v
pytest -v  # full suite
```

**Step 5 — Documentation check**
Review and update references to the old path `docs/legal/`:
- [x] `CLAUDE.md` — update `docs/legal/privacy-policy.md` and `docs/legal/terms-of-service.md`
  references to `backend/core/templates/legal/privacy-policy.md` and
  `backend/core/templates/legal/terms-of-service.md`.
- [x] `AGENTS.md` — same path references.
- [x] `docs/gdpr/README.md` — mentions "served from `docs/legal/privacy-policy.md`"; update
  paths and note that they now live in `backend/core/templates/legal/`.
- [x] `README.md` — if it references `docs/legal/`, update.
- [x] `backend/README.md` — if it mentions editing legal docs, update the path.

</details>

---

## 🟡 Medium (fix soon — functional bugs or significant code quality issues)

### 3. Race condition in `AuthContext.tsx` post-login navigation

- [x] **Fix**

**Problem:**
After `login()` calls `checkConsentStatus()`, the code reads the `needsReconsent` state
variable to decide whether to navigate to `/`:

```typescript
// frontend/src/contexts/AuthContext.tsx  line 74–75
await checkConsentStatus();        // internally calls setNeedsReconsent(true/false)
if (!needsReconsent) navigate('/'); // reads STALE state — always false at this point!
```

React state updates via `setNeedsReconsent` are asynchronous. The `needsReconsent` variable
captured by the closure is always the **previous** render's value (`false`), so
`navigate('/')` always fires, racing with the `navigate('/reconsent')` inside
`checkConsentStatus`.

**Acceptance criteria:**
- After login, if `GET /api/users/me/consent-status` returns `needs_reconsent: true`,
  the user lands on `/reconsent`, not on `/`.
- After login with current consents, the user lands on `/`.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Single file change:** `frontend/src/contexts/AuthContext.tsx`

**Step 1 — Make `checkConsentStatus` return a boolean**

Line 27–37 — change:
```typescript
const checkConsentStatus = async () => {
    try {
      const status = await authApi.getConsentStatus();
      setNeedsReconsent(status.needs_reconsent);
      if (status.needs_reconsent) {
        navigate('/reconsent');
      }
    } catch {
      // Non-critical — do not block the user if the check fails
    }
  };
```
to:
```typescript
const checkConsentStatus = async (): Promise<boolean> => {
    try {
      const status = await authApi.getConsentStatus();
      setNeedsReconsent(status.needs_reconsent);
      if (status.needs_reconsent) {
        navigate('/reconsent');
      }
      return status.needs_reconsent;
    } catch {
      // Non-critical — do not block the user if the check fails
      return false;
    }
  };
```

**Step 2 — Use the return value in `login()`**

Line 73–75 — change:
```typescript
      toast.success('Logged in successfully');
      await checkConsentStatus();
      if (!needsReconsent) navigate('/');
```
to:
```typescript
      toast.success('Logged in successfully');
      const reconsent = await checkConsentStatus();
      if (!reconsent) navigate('/');
```

No changes needed in the `loadUser` `useEffect` (line 51) — there the
`checkConsentStatus()` return value is not used for navigation, and the redirect
inside the function handles it.

**Step 3 — Verify manually**
1. Create a user, grant consent for v1.0.
2. Bump the legal document version to 2.0 in `terms-of-service.md` frontmatter.
3. Log in → should land on `/reconsent`.
4. Accept → should land on `/`.
5. Log out and back in → should go straight to `/`.

**Step 4 — Documentation check**
- [ ] No documentation references this internal React implementation — no doc updates needed.

</details>

---

### 4. `get_consent_status` — wrong version selected when user has multiple active consents of the same type

- [x] **Fix**

**Problem:**
```python
# backend/users/services.py  line 123
active = {c.consent_type: c.version for c in
          UserConsent.objects.filter(user=user, withdrawn_at__isnull=True)}
```
If a user has two active (non-withdrawn) consent rows for the same `consent_type` (e.g.,
granted v1.0 then v2.0 without withdrawing v1.0 first), the dict comprehension uses
whichever row comes last in **undefined** queryset iteration order. The "current" version
check may pick an older version, incorrectly triggering re-consent.

**Acceptance criteria:**
- `get_consent_status` always uses the **most recently granted** active consent per type.
- New test confirms correct behaviour when duplicate active consents exist.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Step 1 — Fix the queryset in `get_consent_status`**

File: `backend/users/services.py`

Line 123 — change:
```python
active = {c.consent_type: c.version for c in UserConsent.objects.filter(user=user, withdrawn_at__isnull=True)}
```
to:
```python
active = {}
for c in UserConsent.objects.filter(user=user, withdrawn_at__isnull=True).order_by('consent_type', '-granted_at'):
    active.setdefault(c.consent_type, c.version)
```

`setdefault` keeps the first value per key. Because the queryset is ordered by
`-granted_at`, the first row per `consent_type` is the most recent.

**Step 2 — Add test**

File: `backend/users/tests/test_consent.py`

Add after `test_grant_consent_records_ip_address` (after line 131):
```python
def test_consent_status_uses_latest_version_when_duplicates_exist(self):
    """When multiple active consents exist for the same type, use the latest."""
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    # Older consent — v0.9
    UserConsent.objects.create(
        user=self.user,
        consent_type='terms_of_service',
        version='0.9',
    )
    # Newer consent — v1.0 (the current version)
    newer = UserConsent.objects.create(
        user=self.user,
        consent_type='terms_of_service',
        version='1.0',
    )
    # Manually set granted_at so newer is definitely later
    UserConsent.objects.filter(id=newer.id).update(granted_at=now + timedelta(seconds=1))

    UserConsent.objects.create(user=self.user, consent_type='privacy_policy', version='1.0')

    response = self.client.get('/api/users/me/consent-status', **self.auth_headers())
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertTrue(data['terms_current'])  # should pick v1.0, not v0.9
    self.assertFalse(data['needs_reconsent'])
```

**Step 3 — Verify**
```bash
cd backend
pytest users/tests/test_consent.py -v
```

**Step 4 — Documentation check**
- [ ] No documentation describes the internal consent-status query logic — no doc updates
  needed.

</details>

---

### 5. IP address extraction duplicated in multiple places

- [x] **Refactor**

**Problem:**
The same IP-extraction pattern is copy-pasted in three places:
1. `backend/core/api.py:68` (registration)
2. `backend/users/api.py:74` (grant consent endpoint)
3. `backend/common/throttle.py:29–32` (rate limiter)

Any future fix (e.g., handling IPv6, multiple proxies) must be applied in all three.

**Acceptance criteria:**
- Single `get_client_ip(request)` utility function exists in `backend/common/utils.py`.
- All three call sites use the utility.
- A unit test for `get_client_ip` covers X-Forwarded-For and REMOTE_ADDR.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Step 1 — Create utility function**

Create new file: `backend/common/utils.py`
```python
"""Shared utility functions."""


def get_client_ip(request) -> str | None:
    """Return the client IP, preferring X-Forwarded-For (first hop) over REMOTE_ADDR."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
```

**Step 2 — Update `backend/core/api.py`**

Add import at the top of the file:
```python
from common.utils import get_client_ip
```

Line 68 — change:
```python
ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
```
to:
```python
ip = get_client_ip(request)
```

**Step 3 — Update `backend/users/api.py`**

Add import at the top of the file:
```python
from common.utils import get_client_ip
```

Line 74 — change:
```python
ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
```
to:
```python
ip = get_client_ip(request)
```

**Step 4 — Update `backend/common/throttle.py`**

Add import at the top of the file:
```python
from common.utils import get_client_ip
```

Lines 29–32 — change:
```python
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
```
to:
```python
            ip = get_client_ip(request) or 'unknown'
```

**Step 5 — Add unit tests**

Create file: `backend/common/tests/test_utils.py`
```python
"""Tests for common utility functions."""

from django.test import RequestFactory, SimpleTestCase

from common.utils import get_client_ip


class GetClientIPTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_remote_addr(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '192.168.1.1')

    def test_prefers_x_forwarded_for(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.50, 70.41.3.18'
        self.assertEqual(get_client_ip(request), '203.0.113.50')

    def test_single_x_forwarded_for(self):
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1'
        self.assertEqual(get_client_ip(request), '10.0.0.1')

    def test_no_headers_returns_none(self):
        request = self.factory.get('/')
        request.META.pop('REMOTE_ADDR', None)
        self.assertIsNone(get_client_ip(request))
```

**Step 6 — Verify**
```bash
cd backend
pytest common/tests/test_utils.py -v
pytest -v  # full suite
```

**Step 7 — Documentation check**
- [ ] No documentation references IP extraction internals — no doc updates needed.

</details>

---

## 🟢 Minor / Polish (low priority, improve when time allows)

### 6. `withdraw_consent` endpoint accepts any string consent_type — invalid types return 404 instead of 422

- [x] **Improve**

**Problem:**
`DELETE /api/users/me/consents/{consent_type}` (`backend/users/api.py:90–94`) accepts any
string path parameter. An invalid type like `"foobar"` returns 404 (no active consent
found) which is misleading — the correct status for an invalid enum value is 422.

**Acceptance criteria:**
- `DELETE /api/users/me/consents/foobar` returns 422 (not 404).
- Existing valid consent types (`terms_of_service`, `privacy_policy`) still work.
- Updated/new test covers the 422 case.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Step 1 — Use `Literal` type for path parameter**

File: `backend/users/api.py`

Line 90–94 — change:
```python
@router.delete('/me/consents/{consent_type}', auth=JWTAuth(), response={200: ConsentOut, 404: DetailOut})
def withdraw_consent(request, consent_type: str):
    """Withdraw consent of a specific type."""
    consent = services.UserService.withdraw_consent(request.auth, consent_type)
    return 200, consent
```
to:
```python
from typing import Literal

ConsentTypeLiteral = Literal['terms_of_service', 'privacy_policy']

@router.delete('/me/consents/{consent_type}', auth=JWTAuth(), response={200: ConsentOut, 404: DetailOut})
def withdraw_consent(request, consent_type: ConsentTypeLiteral):
    """Withdraw consent of a specific type."""
    consent = services.UserService.withdraw_consent(request.auth, consent_type)
    return 200, consent
```

Django Ninja will return 422 automatically for values not in the Literal.

**Note:** If Django Ninja does not natively support `Literal` on path parameters (check
the version), fall back to an explicit guard at the top of the view:
```python
from users.models import ConsentType

if consent_type not in ConsentType.values:
    return 422, {'detail': f'Invalid consent type. Must be one of: {", ".join(ConsentType.values)}'}
```

**Step 2 — Update test**

File: `backend/users/tests/test_consent.py`

Add a new test:
```python
def test_withdraw_invalid_consent_type_returns_422(self):
    """Withdrawing an invalid consent type should return 422."""
    response = self.client.delete('/api/users/me/consents/invalid_type', **self.auth_headers())
    self.assertEqual(response.status_code, 422)
```

**Step 3 — Verify**
```bash
cd backend
pytest users/tests/test_consent.py -v
```

**Step 4 — Documentation check**
- [ ] `backend/README.md` — if the API endpoint table lists `DELETE /api/users/me/consents/{consent_type}`,
  no change needed (the path shape is the same, only the validation changes).
- [ ] `docs/gdpr/README.md` — same; path is unchanged.

</details>

---

### 7. `blocking_workspaces` field uses untyped `list[dict]`

- [x] **Improve**

**Problem:**
```python
# backend/core/schemas/gdpr.py:16
blocking_workspaces: list[dict] | None = None  # [{'id': 1, 'name': 'X', 'member_count': 3}]
```
`list[dict]` is not validated or typed. Clients get no schema documentation for the shape.

**Acceptance criteria:**
- `blocking_workspaces` uses a typed Pydantic model.
- OpenAPI docs at `/api/docs` show the full shape.
- Existing deletion-check tests pass unchanged.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Single file change:** `backend/core/schemas/gdpr.py`

Replace:
```python
"""GDPR-related schemas for account deletion and data portability."""

from pydantic import BaseModel


class AccountDeleteIn(BaseModel):
    """Input for account deletion — requires password confirmation."""

    password: str


class AccountDeleteCheckOut(BaseModel):
    """Pre-deletion check showing what will be affected."""

    can_delete: bool
    blocking_workspaces: list[dict] | None = None  # [{'id': 1, 'name': 'X', 'member_count': 3}]
    solo_workspaces: list[str]  # workspace names that will be deleted
    shared_workspace_memberships: int  # count of non-owned workspace memberships
    total_transactions: int  # count of transactions created by user
    total_planned_transactions: int
    total_currency_exchanges: int


class AccountDeleteOut(BaseModel):
    """Output confirming account deletion."""

    message: str
    deleted_workspaces: list[str]
```

with:
```python
"""GDPR-related schemas for account deletion and data portability."""

from pydantic import BaseModel


class AccountDeleteIn(BaseModel):
    """Input for account deletion — requires password confirmation."""

    password: str


class BlockingWorkspace(BaseModel):
    """A workspace that blocks account deletion (user owns it + other members exist)."""

    id: int
    name: str
    member_count: int


class AccountDeleteCheckOut(BaseModel):
    """Pre-deletion check showing what will be affected."""

    can_delete: bool
    blocking_workspaces: list[BlockingWorkspace] | None = None
    solo_workspaces: list[str]
    shared_workspace_memberships: int
    total_transactions: int
    total_planned_transactions: int
    total_currency_exchanges: int


class AccountDeleteOut(BaseModel):
    """Output confirming account deletion."""

    message: str
    deleted_workspaces: list[str]
```

Also update `backend/core/schemas/__init__.py` — add `BlockingWorkspace` to the imports
and `__all__` list (only if other schemas are individually re-exported; otherwise the
import via `AccountDeleteCheckOut` auto-resolves the nested model).

**Verify:**
```bash
cd backend
pytest users/tests/test_account_deletion.py -v
```

**Documentation check:**
- [ ] No docs reference the internal schema shape — no doc updates needed.

</details>

---

### 8. `Register.tsx` uses a single checkbox for both Terms and Privacy acceptance

- [x] **Improve**

**Problem:**
One `acceptedTerms` boolean tracks acceptance of both documents. The variable name is
misleading (it covers privacy too), and GDPR best practice is to allow users to consent
to each purpose separately.

**Acceptance criteria:**
- Two separate checkboxes on the registration form.
- Both must be checked before the form can be submitted.
- Each links to the respective legal page.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Single file change:** `frontend/src/pages/Register.tsx`

**Step 1 — Split state**

Line 15 — change:
```typescript
const [acceptedTerms, setAcceptedTerms] = useState(false);
```
to:
```typescript
const [acceptedTerms, setAcceptedTerms] = useState(false);
const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
```

**Step 2 — Replace checkbox block**

Lines 161–177 — replace the single checkbox `<div>` with two:
```tsx
<div className="space-y-2">
  <div className="flex items-start gap-2">
    <input
      id="accept-terms"
      type="checkbox"
      required
      checked={acceptedTerms}
      onChange={(e) => setAcceptedTerms(e.target.checked)}
      className="mt-1"
    />
    <label htmlFor="accept-terms" className="text-sm text-gray-600">
      I accept the{' '}
      <Link to="/terms" className="text-blue-600 hover:underline">Terms of Service</Link>
      {' '}*
    </label>
  </div>
  <div className="flex items-start gap-2">
    <input
      id="accept-privacy"
      type="checkbox"
      required
      checked={acceptedPrivacy}
      onChange={(e) => setAcceptedPrivacy(e.target.checked)}
      className="mt-1"
    />
    <label htmlFor="accept-privacy" className="text-sm text-gray-600">
      I accept the{' '}
      <Link to="/privacy" className="text-blue-600 hover:underline">Privacy Policy</Link>
      {' '}*
    </label>
  </div>
</div>
```

**Step 3 — Update submit button disabled condition**

Line 182 — change:
```typescript
disabled={isSubmitting || !acceptedTerms || !termsVersion}
```
to:
```typescript
disabled={isSubmitting || !acceptedTerms || !acceptedPrivacy || !termsVersion}
```

**Step 4 — Verify manually**
- Both checkboxes must be checked to enable the submit button.
- Each links to the correct legal page.
- Registration still works end-to-end.

**Step 5 — Documentation check**
- [ ] No docs describe the registration form UI — no doc updates needed.

</details>

---

### 9. `export_all_data` has N+1 query pattern (acceptable now, worth a note)

- [x] **Document / Optimize when needed**

**Problem:**
`UserService.export_all_data()` (`backend/users/services.py:272–415`) fires 6 queries per
budget period (categories, budgets, transactions, planned_transactions, currency_exchanges,
period_balances). For a user with many workspaces x accounts x periods, this produces
hundreds of queries.

Currently acceptable because the endpoint is rate-limited to 3/hour, but worth documenting.

**Acceptance criteria:**
- Inline comment added to the method noting the N+1 pattern and its mitigation.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Single file change:** `backend/users/services.py`

Add a comment inside `export_all_data()` after line 330 (before the workspace loop):
```python
        # NOTE: This uses nested loops (workspaces -> accounts -> periods -> 6 queries per
        # period), resulting in O(W * A * P) queries. This is acceptable for now because
        # the endpoint is rate-limited to 3 requests/hour. If performance becomes an issue
        # for power users with years of data, refactor to batch-query each model type and
        # assemble the nested structure in Python.
```

**Verify:**
```bash
cd backend
pytest users/tests/test_data_export.py -v
```

**Documentation check:**
- [ ] No docs describe the export internals — no doc updates needed.

</details>

---

### 10. `PrivacyPolicyPage` and `TermsPage` — "Back to login" link is always shown

- [x] **Improve (UX)**

**Problem:**
Both `PrivacyPolicyPage.tsx` and `TermsPage.tsx` always show a "Back to login" link. If an
authenticated user opens these pages (e.g., from the re-consent flow), this is confusing.

**Acceptance criteria:**
- Authenticated users see "Back" linking to `/`.
- Unauthenticated users see "Back to login" linking to `/login`.

<details>
<summary><strong>Implementation plan (click to expand)</strong></summary>

**Two files to change — identical pattern in both.**

**File 1:** `frontend/src/pages/PrivacyPolicyPage.tsx`

Add import at line 2:
```typescript
import { useAuth } from '../contexts/AuthContext';
```

Inside the component (after `const [error, setError] = ...`), add:
```typescript
const { isAuthenticated } = useAuth();
```

Lines 19–21 — change:
```tsx
<Link to="/login" className="text-sm text-blue-600 hover:text-blue-500">
  &larr; Back to login
</Link>
```
to:
```tsx
<Link to={isAuthenticated ? '/' : '/login'} className="text-sm text-blue-600 hover:text-blue-500">
  &larr; {isAuthenticated ? 'Back' : 'Back to login'}
</Link>
```

**File 2:** `frontend/src/pages/TermsPage.tsx`

Identical change:
- Add `import { useAuth } from '../contexts/AuthContext';`
- Add `const { isAuthenticated } = useAuth();` inside the component.
- Update the `<Link>` the same way.

**Important caveat:** These pages are rendered under both public and protected routes.
`useAuth()` requires `AuthProvider` in the component tree. Since `AuthProvider` wraps the
entire `<Routes>` in `App.tsx`, this is safe. If the pages are ever rendered outside
`AuthProvider` (unlikely), this will throw. In that case, wrap the hook in a try/catch
or use an optional context.

**Verify:**
- Visit `/privacy` while logged out → shows "Back to login" → links to `/login`.
- Visit `/privacy` while logged in → shows "Back" → links to `/`.
- Same for `/terms`.

**Documentation check:**
- [ ] No docs reference the back-link behaviour — no doc updates needed.

</details>

---

## ✅ Acknowledged — No action needed

- **Email on account deletion uses `on_commit`** — correct, prevents email on rollback.
- **`@db_transaction.atomic` on `delete_account`** — correct, whole deletion is atomic.
- **`BudgetAccount` deleted before workspace** — correct workaround for the `PROTECT`
  constraint on `default_currency`; the inline comment explains why.
- **Admin panel is read-only for `UserConsent`** — appropriate for an audit trail.
- **`cache.clear()` in test `setUp`** — prevents rate-limit state leaking between tests.
- **`fail_silently=True` + logger on email failure** — correct non-blocking error handling.

---

## Task Priority Summary

| # | Severity | Area | Effort | Dependencies |
|---|----------|------|--------|--------------|
| 1 | 🔴 Critical | Consent record retention on deletion | S | None |
| 2 | 🔴 Critical | Move templates + use Django loader (fixes cache flakiness) | S | None |
| 3 | 🟡 Medium | Navigation race condition in `AuthContext` | XS | None |
| 4 | 🟡 Medium | Wrong version in `get_consent_status` | XS | None |
| 5 | 🟡 Medium | IP extraction duplicated 3x | S | None |
| 6 | 🟢 Minor | `withdraw_consent` invalid type → 404 | XS | None |
| 7 | 🟢 Minor | `blocking_workspaces` untyped `list[dict]` | XS | None |
| 8 | 🟢 Minor | Single checkbox for both legal docs | S | None |
| 9 | 🟢 Minor | N+1 queries in export | XS | None |
| 10 | 🟢 Minor | "Back to login" shown to authed users | XS | None |

**Recommended execution order:** 1, 2, 3, 4 (critical + medium bugs first), then 5
(refactor), then 6–10 in any order. All tasks are independent — no dependencies between
them, so they can be parallelized across developers.

**Effort key:** XS = < 30 min, S = 30 min – 1 hour.
