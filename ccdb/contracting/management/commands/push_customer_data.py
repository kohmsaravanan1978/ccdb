from django.core.management.base import BaseCommand
from tqdm import tqdm

from contracting.models import Customer


class Command(BaseCommand):
    """This command pushes customer data to Easybill.

    Use --customer to restrict to one customer."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer",
            help="Run only on one customer, by ID",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Sync all customers, even when their state is 'synced'",
        )

    def handle(self, *args, **options):
        customer = options.get("customer")
        force_all = options.get("force_all")

        customers = Customer.objects.all()
        if customer:
            customers = customers.filter(number=customer)
        if not force_all:
            customers = customers.exclude(easybill_sync_state=Customer.States.SYNCED)

        for customer in tqdm(customers, "Syncing customers"):
            customer.easybill_sync()
