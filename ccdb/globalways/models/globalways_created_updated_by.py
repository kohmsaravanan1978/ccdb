from crum import get_current_user
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

__all__ = ["GlobalwaysCreatedUpdatedBy"]


class GlobalwaysCreatedUpdatedBy(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        editable=False,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        editable=False,
        related_name="%(app_label)s_%(class)s_modified_by",
    )

    def get_modified_by_username(self):
        if self.modified_by is None:
            return ""

        return self.modified_by.username

    def get_created_by_username(self):
        if self.created_by is None:
            return ""

        return self.created_by.username

    def save(self, **kwargs):
        user = get_current_user()

        set_created_by = kwargs.pop("set_created_by", True)
        set_modified_by = kwargs.pop("set_modified_by", True)

        if (
            set_created_by
            and self.pk is None
            and user
            and isinstance(user, get_user_model())
        ):
            self.created_by = user

        if set_modified_by and user and isinstance(user, get_user_model()):
            self.modified_by = user

        return super().save(**kwargs)

    class Meta:
        abstract = True
