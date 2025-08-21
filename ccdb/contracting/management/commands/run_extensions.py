from django.core.management.base import BaseCommand

from contracting.utils.extensions import run_extensions


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't commit any data, just print what would happen",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        run_extensions(dry_run=dry_run)
