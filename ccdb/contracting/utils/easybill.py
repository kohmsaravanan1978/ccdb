import time

import requests
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_lifecycle import BEFORE_UPDATE, LifecycleModel, hook

EASYBILL_SECONDS = 6 if settings.TEST_MODE else 1  #
EASYBILL_CACHE_KEY = "easybill_last_request"
EASYBILL_MAX_ATTEMPTS = 10


def easybill_request(path, method="GET", data=None, attempt=0):
    if not settings.EASYBILL_API_KEY or settings.EASYBILL_API_KEY.startswith("xxxxx"):
        raise Exception(
            "No API key present. Set EASYBILL_API_KEY in your django.env file!"
        )
    if not path.startswith("https"):
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.startswith("/rest/v1"):
            path = f"/rest/v1{path}"
        path = f"https://api.easybill.de{path}"

    headers = {
        "Authorization": f"Bearer {settings.EASYBILL_API_KEY}",
        "Content-Type": "application/json",
    }

    if method in ("POST", "PUT"):
        response = requests.request(method, path, json=data, headers=headers)
    else:
        response = requests.request(method, path, params=data, headers=headers)

    if response.status_code == 429 and attempt != EASYBILL_MAX_ATTEMPTS:
        # rate limit
        print("rate limit")
        time.sleep(EASYBILL_SECONDS + min(attempt**attempt, 60))
        return easybill_request(path, method=method, data=data, attempt=attempt + 1)
    try:
        response.raise_for_status()
    except Exception as e:
        print(response.content.decode())
        raise e
    if response.content:
        try:
            return response.json()
        except Exception:
            return response.content
    return {}


def get_default_data():
    return {"synced_data": {}, "last_state": "unsynced"}


class EasybillModel(LifecycleModel):
    """To use this model fully, provide a list of attributes that are in sync with easybill
    as easybill_attributes, and provide a get_easybill_data method."""

    easybill_attributes = None
    easybill_url = None

    class Meta:
        abstract = True

    class States(models.TextChoices):
        UNSYNCED = "unsynced", _("no initial sync")
        DIRTY = "dirty", _("not in sync")
        PENDING = "pending", _("pending")
        SYNCED = "synced", _("synced")

    easybill_id = models.BigIntegerField(null=True, blank=True)
    easybill_sync_state = models.CharField(
        choices=States.choices, max_length=8, default=States.UNSYNCED
    )
    easybill_data = models.JSONField(default=get_default_data)
    easybill_last_sync = models.DateTimeField(null=True, blank=True)

    def get_easybill_data(self):
        return {}

    @property
    def easybill_dirty(self):
        return self.easybill_sync_state == self.States.DIRTY

    @hook(BEFORE_UPDATE)
    def set_dirty(self):
        # No need to consider dirty models
        if self.easybill_sync_state == self.States.DIRTY:
            return

        # If we explicitly set sync state, we know what we are doing
        if self.has_changed("easybill_sync_state"):
            return

        if self.easybill_attributes and any(
            [self.has_changed(attr) for attr in self.easybill_attributes]
        ):
            self.easybill_sync_state = self.States.DIRTY
        else:
            data = self.get_easybill_data()
            if data and data != self.easybill_data.get("synced_data"):
                self.easybill_sync_state = self.States.DIRTY
