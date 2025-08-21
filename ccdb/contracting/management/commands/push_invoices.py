from django.core.management.base import BaseCommand
from tqdm import tqdm

from contracting.models import Invoice


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't push anything, just print what would happen",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        queryset = (
            Invoice.objects.filter(number__isnull=True)
            .exclude(easybill_sync_state=Invoice.States.PENDING)
            .select_related("booking_account")
            .prefetch_related("items", "items__contract_item")
        )
        email_delivery = 0
        sepa_xml = 0
        for invoice in tqdm(queryset):
            if dry_run:
                email_delivery += (
                    1 if invoice.booking_account.invoice_delivery_email else 0
                )
                sepa_xml += 1 if invoice.booking_account.payment_type == "SEPA" else 0
            else:
                try:
                    invoice.easybill_sync()
                except Exception as e:
                    print(e)
        if dry_run:
            print(f"Would push {len(queryset)} invoices to easybill.")
            print(f"Would send {email_delivery} emails.")
            print(f"Would create {sepa_xml} SEPA XML files.")
