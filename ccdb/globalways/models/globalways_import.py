from django.contrib.postgres.fields.jsonb import JSONField
from django.db import models

__all__ = ["GlobalwaysImport"]


class GlobalwaysImport(models.Model):
    # todo remove, only used for import
    import_iam_id = models.PositiveIntegerField(null=True, blank=True)
    import_data = JSONField(default=dict, blank=True)

    class Meta:
        abstract = True
