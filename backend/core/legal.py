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

    return meta, text[end + 5 :].strip()


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
