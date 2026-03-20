"""Shared permission utilities for API endpoints."""

from common.exceptions import PermissionDeniedError
from workspaces.models import WorkspaceMember


def require_role(user, workspace_id: int, allowed_roles: list[str]) -> str:
    """Raise 403 if user is not a member or their role is not in allowed_roles. Returns the role."""
    cached_role = getattr(user, '_workspace_member_role', None)
    if cached_role is not None and user.current_workspace_id == workspace_id:
        role = cached_role
    else:
        try:
            member = WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
            role = member.role
        except WorkspaceMember.DoesNotExist:
            raise PermissionDeniedError('Not a member of this workspace')
    if role not in allowed_roles:
        raise PermissionDeniedError(
            f'Insufficient permissions. Required: {", ".join(allowed_roles)}. Your role: {role}'
        )
    return role
