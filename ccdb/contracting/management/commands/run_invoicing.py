from django.core.management.base import BaseCommand

from contracting.utils.invoicing import run_invoicing


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't commit any data, just print what would happen",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        run_invoicing(dry_run=dry_run, console_output=True)
