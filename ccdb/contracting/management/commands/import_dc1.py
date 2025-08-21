import datetime as dt
from csv import DictReader
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils.timezone import now
from tqdm import tqdm

from contracting.models import Contract, ContractItem


def to_money(s):
    s = s.strip("€ -")
    if not s:
        return None
    s = s.replace(".", "")
    s = s.replace(",", ".")
    return Decimal(s)


class Command(BaseCommand):
    """This command is meant to be run once, though running it repeatedly
    SHOULD not change any data.

    It is meant to take data from our archived data (in the CSV file next to this)
    and import it **once**."""

    def get_contracts(self):
        next_contract_id = (
            Contract.objects.all().aggregate(max_id=Max("number")).get("max_number")
            or 0
        ) + 1
        contract_stuttgart = Contract.objects.create(
            booking_account_id=8,
            name="Importierte DC1-Verträge (Stuttgart)",
            valid_from=dt.date(2020, 1, 1),
            number=next_contract_id,
        )
        contract_nrw = Contract.objects.create(
            booking_account_id=10,
            name="Importierte DC1-Verträge (NRW)",
            valid_from=dt.date(2020, 1, 1),
            number=next_contract_id + 1,
        )
        return contract_stuttgart, contract_nrw

    def handle(self, *args, **options):
        csv_path = Path(__file__).parent / "import_dc1.csv"
        with open(csv_path) as csv_file:
            reader = DictReader(csv_file)
            data = list(reader)

        with transaction.atomic():
            # Create customers
            contract_28, contract_26 = self.get_contracts()
            contract_item_map = {}
            successor_map = {}

            base_number = (
                ContractItem.objects.all()
                .aggregate(max_number=Max("number"))
                .get("max_number")
                or 0
            ) + 1
            created = 0
            last_invoice = dt.date(2022, 5, 1)
            yesterday = (now() - dt.timedelta(days=1)).date()

            for line in tqdm(data):
                if not line["account-name"]:
                    continue

                # stuttgart = 20028 / nrw = 20026
                contract = (
                    contract_28 if str(line["account-name"]) == "20028" else contract_26
                )
                item = ContractItem.objects.create(
                    number=base_number + created,
                    order=created,
                    contract=contract,
                    price_setup=None,
                    accounting_period=1,
                    notice_period=2,
                    next_invoice=yesterday,
                    last_invoice_override=last_invoice,
                    valid_from=dt.datetime.strptime(line["posten-beginn"], "%d.%m.%Y"),
                    valid_till=(
                        dt.datetime.strptime(line["posten-ende"], "%d.%m.%Y")
                        if line["posten-ende"]
                        else None
                    ),
                    ready_for_service=(
                        None
                        if line["posten-status"] == "in Produktion"
                        else "importiert"
                    ),
                    archived=line["posten-status"]
                    in (
                        "ausgelaufen-posten_ist_ausgelaufen",
                        "ausgelaufen-posten_wurde_ersetzt",
                        "storniert",
                    ),
                    price_recurring=to_money(line["posten-preis-mrc"]),
                    product_code=line["posten-name"],
                    product_name=line["posten-name"],
                    product_description=line["posten-beschreibung"],
                    termination_date=(
                        dt.datetime.strptime(line["posten-ende"], "%d.%m.%Y")
                        if line["posten-status"] in ("aktiv-gekündigt",)
                        else None
                    ),
                    order_reference=line["AltePostenIDExcel_DC1_REF"],
                    gnom_id=line["Gnom_ID"],
                    network_information=line["Netz"],
                    internal_comment=line["GW Kommentar"],
                )
                created += 1
                contract_item_map[line["posten-id"]] = item.id

                if len(line["posten-ersatz"]) > 4:
                    successor_map[line["posten-id"]] = line["posten-ersatz"]

                if to_money(line["posten-preis-nrc"]):
                    item = ContractItem.objects.create(
                        number=base_number + created,
                        order=created,
                        contract=contract,
                        price_setup=to_money(line["posten-preis-nrc"]),
                        price_recurring=None,
                        accounting_period=1,
                        notice_period=2,
                        next_invoice=None,
                        last_invoice_override=None,
                        valid_from=dt.datetime.strptime(
                            line["posten-beginn"], "%d.%m.%Y"
                        ),
                        valid_till=(
                            dt.datetime.strptime(line["posten-ende"], "%d.%m.%Y")
                            if line["posten-ende"]
                            else None
                        ),
                        ready_for_service=(
                            None
                            if line["posten-status"] == "in Produktion"
                            else "importiert"
                        ),
                        archived=line["posten-status"]
                        in (
                            "ausgelaufen-posten_ist_ausgelaufen",
                            "ausgelaufen-posten_wurde_ersetzt",
                            "storniert",
                        ),
                        product_code=line["posten-name"],
                        product_name=line["posten-name"],
                        product_description=line["posten-beschreibung"],
                        termination_date=(
                            dt.datetime.strptime(line["posten-ende"], "%d.%m.%Y")
                            if line["posten-status"] in ("aktiv-gekündigt",)
                            else None
                        ),
                        order_reference=line["AltePostenIDExcel_DC1_REF"],
                        gnom_id=line["Gnom_ID"],
                        network_information=line["Netz"],
                        internal_comment=line["GW Kommentar"],
                    )
                    created += 1
                    contract_item_map[line["posten-id"]] = item.id

            for successor, predecessor in successor_map.items():
                mapped_successor = contract_item_map.get(successor)
                mapped_predecessor = contract_item_map.get(predecessor)
                if not mapped_predecessor and mapped_successor:
                    print(
                        f"Could not find matching successor for {successor}–{predecessor}"
                    )
                else:
                    try:
                        ContractItem.objects.filter(number=mapped_successor).update(
                            predecessor=mapped_predecessor
                        )
                    except Exception:
                        pass

            print(
                f"Imported {created} contract items in 2 contracts, with {len(successor_map)}."
            )
