from django.db import models


class WorkspaceScopedQuerySet(models.QuerySet):
    """QuerySet with for_workspace() filtering.

    Supports two patterns during migration:
    - Direct workspace_id FK (preferred, after migration)
    - WORKSPACE_FILTER constant with nested path (legacy, before migration)
    """

    def for_workspace(self, workspace_id: int):
        if not workspace_id:
            raise ValueError(
                f'workspace_id is required for {self.model.__name__}.for_workspace(), got {workspace_id!r}'
            )
        workspace_filter = getattr(self.model, 'WORKSPACE_FILTER', 'workspace_id')
        return self.filter(**{workspace_filter: workspace_id})
