from django_extensions.db.models import TimeStampedModel

from globalways.models.globalways_created_updated_by import GlobalwaysCreatedUpdatedBy
from globalways.models.globalways_tool import GlobalwaysTool


class GlobalwaysModel(GlobalwaysTool, GlobalwaysCreatedUpdatedBy, TimeStampedModel):
    class Meta:
        abstract = True
