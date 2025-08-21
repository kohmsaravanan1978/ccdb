from django.core.management.base import BaseCommand

from contracting.utils import cbs_import


class Command(BaseCommand):
    """This command is meant to be run once, though running it repeatedly
    SHOULD not change any data.

    It is meant to take data from our archival models (only used to keep historical
    data around) and transform it into our active data model.
    Not all historical models are migrated, as some (like delivery tracking)
    aren't in scope anymore."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all data first",
        )
        parser.add_argument(
            "--only-invoices",
            action="store_true",
            help="Import invoices, nothing else (fails if contracts are missing!)",
        )
        parser.add_argument(
            "--only-contracts",
            action="store_true",
            help="Import contracts, nothing else (fails if accounts/customers are missing!)",
        )
        parser.add_argument(
            "--only-accounts",
            action="store_true",
            help="Import accounts and customers, nothing else",
        )

    def handle(self, *args, **options):
        delete = options.get("delete")
        invoices = options.get("only_invoices")
        contracts = options.get("only_contracts")
        accounts = options.get("only_accounts")

        if not any([invoices, contracts, accounts]):
            # importing everything
            invoices = contracts = accounts = True

        if delete:
            from contracting.models import (
                BookingAccount,
                Contract,
                ContractItem,
                Customer,
                Invoice,
                InvoiceItem,
            )

            if invoices:
                InvoiceItem.objects.all().delete()
                Invoice.objects.all().delete()
            if contracts:
                if not invoices:
                    raise Exception(
                        "Can't delete just contracts, either re-import everything or include --only-invoices"
                    )
                ContractItem.objects.all().delete()
                Contract.objects.all().delete()
            if accounts:
                if not invoices or not contracts:
                    raise Exception(
                        "Can't delete just accounts. If you need to re-import accounts, you'll have to re-import the entire database."
                    )
                BookingAccount.objects.all().delete()
                Customer.objects.all().delete()

        cbs_import.import_all(invoices=invoices, contracts=contracts, accounts=accounts)
