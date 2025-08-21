import os

from django.apps import AppConfig
from django.conf import settings


class ApiConfig(AppConfig):
    name = "api"
    path = os.path.join(settings.BASE_DIR, "api")

    def ready(self):
        super().ready()
