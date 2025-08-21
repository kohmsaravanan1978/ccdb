from django.apps import AppConfig


class ContractingConfig(AppConfig):
    name = "contracting"

    def ready(self):
        super().ready()
