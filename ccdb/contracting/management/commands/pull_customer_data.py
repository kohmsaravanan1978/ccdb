from django.core.management.base import BaseCommand

from contracting.utils.crm import pull_customer_data

BATCH_SIZE = 100


class Command(BaseCommand):
    """This command pulls in customer data from the Globalways CRM.

    Use --customer to restrict to one customer."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer",
            help="Run only on one customer, by ID",
        )

    def handle(self, *args, **options):
        customer = options.get("customer")
        pull_customer_data(
            customers=[customer] if customer else None, batch_size=BATCH_SIZE
        )
