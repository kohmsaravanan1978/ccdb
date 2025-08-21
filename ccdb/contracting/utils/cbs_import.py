"""These methods are meant to be run once, though running them repeatedly
SHOULD not change any data.

They are meant to take data from our archival models (only used to keep historical
data around) and transform it into our active data model.
Not all historical models are migrated, as some (like delivery tracking)
aren't in scope anymore.

These methods get called from the `import_cbs` admin command."""

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.db.models import F, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from tqdm import tqdm

from contracting.models import (
    BookingAccount,
    BookingAccountSepa,
    Contract,
    ContractItem,
    Customer,
    GwCbsBuchungskonto,
    GwCbsRechnungen,
    GwCbsVertrag,
    GwCbsVertragPosten,
    Invoice,
    InvoiceItem,
)


def get_postal_address(account):
    addr_field = account.zustellung.zustellung_post_an.strip("\r\n").split("\r\n")
    if len(addr_field) == 1:
        addr_field = addr_field[0].strip("\n").split("\n")

    if addr_field[-1] in ("DE", "Germany", "Deutschland"):
        addr_field = addr_field[:-1]

    customer_name = ""
    address_zip_code, address_city, address_street, address_suffix = 4 * [""]

    if addr_field[0] == "MUSS NOCH BEARBEITET WERDEN":
        customer_name = "Neuer Kunde"
    elif addr_field[0] in ["Fotoservice Weimar", "Hardwareversand Beier"]:
        customer_name = addr_field.pop(0)
        address_suffix = addr_field.pop()
        address_street = addr_field.pop()
        address_zip_code, address_city = addr_field.pop().split(" ", 1)
    elif addr_field[0] in [
        "Mark Müller",
        "Adao correia da costa",
        "mihay bozoki",
        "Heinz Cremer",
        "Jan Koerner",
        "Jürgen Marmann",
    ]:
        customer_name = addr_field.pop(0)
        address_street = addr_field.pop()
        address_zip_code, address_city = addr_field.pop().split(" ", 1)
    elif addr_field[0] == "Quinta da Plansel, S.A.":
        customer_name = addr_field.pop(0)
        address_street = addr_field.pop()
        address_suffix = addr_field.pop()
        address_zip_code, address_city = addr_field.pop().split(" ", 1)
    else:
        try:
            customer_name = addr_field.pop(0)
            address_zip_code, address_city = addr_field.pop().split(" ", 1)
            address_street = addr_field.pop() if addr_field else ""
        except Exception:
            address_street = addr_field.pop() if addr_field else ""
            address_zip_code, address_city = (
                addr_field.pop().split(" ", 1) if addr_field else ("", "")
            )
    # All remains are put in the suffix
    if addr_field:
        address_suffix += "\r\n" + "\r\n".join(addr_field)
        address_suffix = address_suffix.strip()
    if len(address_zip_code) != 5 and len(address_city) == 5:
        address_zip_code, address_city = address_city, address_zip_code
    if len(address_zip_code) > 10:
        address_city = f"{address_zip_code} {address_city}"
        address_zip_code = ""
    if not customer_name or customer_name == "Neuer Kunde":
        gwcontract = account.contracts.all().filter(firma__isnull=False).first()
        customer_name = customer_name or "Unbekannter Kunde"
        customer_name += f" {gwcontract.firma}"

    result = {
        "address_company": customer_name,
        "address_street": address_street,
        "address_suffix": address_suffix,
        "address_city": address_city,
        "address_zip_code": address_zip_code,
        "address_country": "DE",
    }

    return result


def get_address_data():
    with open(
        Path(__file__).parent.parent / "management" / "commands" / "import_cbs_data.csv"
    ) as fp:
        reader = csv.DictReader(fp)
        data = [row for row in reader]
    return {
        int(row["ID"]): {
            "address_company": row["Firma"],
            "address_street": row["Straße"],
            "address_suffix": row["Zusatz"],
            "address_city": row["Stadt"],
            "address_zip_code": row["PLZ"],
            "address_country": row["Land"],
        }
        for row in data
    }


def import_accounts():
    """Transforms GwCbsBuchungskonto to BookingAccount objects."""
    address_data = get_address_data()
    total_created = 0
    total = 0

    type_map = {
        "SEPAELV": BookingAccount.Types.SEPA,
        "UW": BookingAccount.Types.INVOICE,
        "GWKONTO": BookingAccount.Types.INVOICE,
        "ELV": BookingAccount.Types.NONE,  # only in historic data
        "BANKABBUCHUNG": BookingAccount.Types.NONE,  # only in historic data
    }
    accounts = (
        GwCbsBuchungskonto.objects.all()
        .filter(imported__isnull=True)
        .select_related("zustellung", "gwcbsbuchungskontosepaelv")
    )
    for old_account in tqdm(accounts, "Buchungskonten"):
        customer, _ = Customer.objects.get_or_create(number=old_account.kundeid)
        payment_type = type_map[old_account.zahlungsart]
        address_email = None
        invoice_delivery_email = False
        invoice_delivery_post = False
        tax_rate = 19
        tax_option = BookingAccount.TaxOptions.NULL

        if not old_account.zustellung:
            raise Exception(
                f"Account {old_account.buchungskontoid} is without delivery method."
            )

        # Have to correct some faulty data
        address_postal = {}
        if old_account.buchungskontoid in address_data:
            address_postal = address_data[old_account.buchungskontoid]
        elif (
            old_account.zustellung.zustellung_post == "J"
            or old_account.zustellung.zustellung_post_an
            or old_account.buchungskontoid in (16064, 16229, 16011, 16845)
        ):
            invoice_delivery_post = (
                old_account.zustellung.zustellung_post == "J"
                or old_account.zustellung.zustellung_email == "N"
            )
            if old_account.buchungskontoid == 16022:
                address_postal = {
                    "address_company": "NetCom BW GmbH",
                    "address_city": "Karlsruhe",
                    "address_zip_code": "76254",
                }
            else:
                address_postal = get_postal_address(old_account)
                if (
                    not address_postal["address_street"]
                    and not address_postal["address_city"]
                    and old_account.zustellung.zustellung_post == "J"
                ):
                    raise Exception(
                        f"Account {old_account.buchungskontoid} has post delivery but no address."
                    )
        if old_account.zustellung.zustellung_email == "J":
            invoice_delivery_email = True
            address_email = old_account.zustellung.zustellung_email_an
            if not address_email:
                if not address_postal or not any(v for v in address_postal.values()):
                    raise Exception(
                        f"Account {old_account.buchungskontoid} has email delivery but no address."
                    )
                invoice_delivery_email = False

        if old_account.mwst == "N":
            tax_rate = 0
            if old_account.ust_id_nr:
                tax_option = BookingAccount.TaxOptions.nStbUstID
            else:
                tax_option = BookingAccount.TaxOptions.nStbNoneUstID

        new, created = BookingAccount.objects.get_or_create(
            customer=customer,
            id=old_account.buchungskontoid,
            defaults={
                "payment_type": payment_type,
                "invoice_delivery_post": invoice_delivery_post,
                "invoice_delivery_email": invoice_delivery_email,
                "address_email": address_email,
                "payment_term": old_account.zahlungsfrist,
                "tax_rate": tax_rate,
                "tax_option": tax_option,
                "vat_id": old_account.ust_id_nr or None,
                "comment": old_account.bemerkung or None,
                **address_postal,
            },
        )
        old_account.imported = new
        old_account.save()
        if hasattr(old_account, "gwcbsbuchungskontosepaelv"):
            old_sepa = old_account.gwcbsbuchungskontosepaelv
            BookingAccountSepa.objects.create(
                account=new,
                confirmed=old_sepa.confirmed,
                revoked=old_sepa.revoked,
                first_used=old_sepa.first_used,
                last_used=old_sepa.last_used or old_sepa.first_used,
                account_owner=old_sepa.kontoinhaber,
                bank_name=old_sepa.kreditinstitut,
                bic=old_sepa.bic,
                iban=old_sepa.iban,
                reference=old_sepa.mandatsreferenz,
                address_street=old_sepa.anschrift,
                address_zip_code=old_sepa.plz,
                address_city=old_sepa.ort,
                # not imporing address_country, as all are DE and we need normalisation
            )
        elif payment_type == BookingAccount.Types.SEPA:
            print(
                f"Booking account {new} has payment type SEPA but no related sepa data!"
            )

        total_created += bool(created)
        total += 1
    return total, total_created


def import_contracts():
    total_created = 0
    total = 0
    billing_types = defaultdict(lambda: None)
    billing_types[""] = ContractItem.BillingTypes.ONCE
    billing_types["bulk_domain"] = ContractItem.BillingTypes.RECURRING
    billing_types["item_fix"] = ContractItem.BillingTypes.ONCE
    billing_types["item_he"] = ContractItem.BillingTypes.ONCE
    billing_types["item_lohn"] = ContractItem.BillingTypes.ONCE
    billing_types["item_subnetz"] = ContractItem.BillingTypes.RECURRING
    billing_types["item_tixi"] = ContractItem.BillingTypes.RECURRING
    billing_types["item_upstreamtraffic"] = ContractItem.BillingTypes.RECURRING
    billing_types["item_webspace"] = ContractItem.BillingTypes.RECURRING
    billing_types["meta_he"] = ContractItem.BillingTypes.RECURRING
    billing_types["meta_upstreamtraffic"] = ContractItem.BillingTypes.RECURRING
    billing_types["meta_voipcdr"] = ContractItem.BillingTypes.RECURRING

    contracts = (
        GwCbsVertrag.objects.filter(
            imported__isnull=True, buchungskontoid__imported__isnull=False
        )
        .prefetch_related("gwcbsvertragposten_set", "gwcbsvertragposten_set__sparte")
        .select_related("buchungskontoid")
    )
    _now = now().date()
    IMPORT_DISABLE = (2196,)
    for old_contract in tqdm(contracts, "Verträge"):
        with transaction.atomic():
            if (
                old_contract.ausgelaufen
                and old_contract.ende
                and old_contract.ende > _now
            ):
                if old_contract.id in (125730, 35591, 35592):
                    old_contract.ende = old_contract.beginn
            if (
                old_contract.gekuendigt or old_contract.gekuendigt_am
            ) and not old_contract.ende:
                old_contract.ende = (
                    old_contract.frist or old_contract.gekuendigt_am.date()
                )
            if (
                old_contract.beginn
                and old_contract.ende
                and old_contract.beginn > old_contract.ende
            ):
                old_contract.beginn = old_contract.ende

            next_invoice = old_contract.naechste_rechnung
            paused = old_contract.suspended and not old_contract.ende < _now

            contract, created = Contract.objects.get_or_create(
                number=old_contract.id,
                booking_account=old_contract.buchungskontoid.imported,
                defaults={
                    "name": old_contract.vname,
                    "order_date": old_contract.unterzeichnet_am,
                    "termination_date": old_contract.gekuendigt_am,
                    "valid_from": old_contract.beginn,
                    "valid_till": (
                        old_contract.ende
                        if old_contract.id not in IMPORT_DISABLE
                        else "2022-04-01"
                    ),
                    "notice_period": old_contract.kuend_frist,
                    "automatic_extension": old_contract.verlaengerung,
                    "collective_invoice": not old_contract.einzelrechnung,
                    "order_reference": old_contract.kunden_referenz_nummer or None,
                    "jira_ticket": old_contract.ticket_id or None,
                    "minimum_duration": old_contract.beginn_laufzeit or 1,
                    "comment": old_contract.kommentar or None,
                    "created": old_contract.erstellt,
                    "modified": old_contract.letzte_aenderung,
                },
            )
            old_contract.imported = contract
            old_contract.save()

            accounting_period = old_contract.rechnungsintervall
            if accounting_period in (11, 24):
                accounting_period = 12  # Only archived contracts anyways

            old_items = old_contract.gwcbsvertragposten_set.all()
            if created or contract.items.all().count() != old_items.count():
                contract.items.all().delete()
                for old_item in old_items:
                    billing_type = billing_types[old_item.typ]
                    price_recurring = (
                        Decimal(str(old_item.preis))
                        if billing_type == ContractItem.BillingTypes.RECURRING
                        else None
                    )
                    price_setup = (
                        Decimal(str(old_item.preis))
                        if billing_type == ContractItem.BillingTypes.ONCE
                        else None
                    )
                    if not billing_type:
                        print(old_item.typ)
                    item = ContractItem.objects.create(
                        number=old_item.id,
                        contract=contract,
                        order=old_item.reihenfolge,
                        product_name=old_item.name or "imported",
                        product_code=old_item.name[:50] or "imported",
                        product_description=old_item.beschreibung,
                        price_recurring=(
                            round(price_recurring, 2)
                            if price_recurring
                            else price_recurring
                        ),
                        price_setup=(
                            round(price_setup, 2) if price_setup else price_setup
                        ),
                        accounting_period=accounting_period,
                        billing_type=billing_type,
                        fibu_account=(
                            old_item.sparte.fibu_konto if old_item.sparte else None
                        ),
                        paused=paused or old_item.deleted,
                        next_invoice=next_invoice,
                        archived=old_item.abgerechnet == "J",
                    )
                    old_item.imported = item
                    old_item.save()
            total_created += bool(created)
            total += 1
    Contract.objects.all().annotate(
        new_created=Subquery(
            GwCbsVertrag.objects.filter(imported_id=OuterRef("id")).values("erstellt")[
                :1
            ]
        ),
        new_modified=Subquery(
            GwCbsVertrag.objects.filter(imported_id=OuterRef("id")).values(
                "letzte_aenderung"
            )[:1]
        ),
    ).update(
        created=F("new_created"), modified=Coalesce(F("new_modified"), F("new_created"))
    )
    ContractItem.objects.all().annotate(
        new_created=Subquery(
            ContractItem.objects.filter(id=OuterRef("id")).values("contract__created")[
                :1
            ]
        ),
        new_modified=Subquery(
            ContractItem.objects.filter(id=OuterRef("id")).values("contract__modified")[
                :1
            ]
        ),
    ).update(
        created=F("new_created"), modified=Coalesce(F("new_modified"), F("new_created"))
    )
    return total, total_created


def import_invoices():
    total_created = 0
    failures = 0

    old_invoices = (
        GwCbsRechnungen.objects.filter(imported__isnull=True)
        .select_related("transaction")
        .prefetch_related(
            "gwcbsrechnungenpositionen_set",
            "gwcbsrechnungenpositionen_set__buchungskonto",
        )
    )
    for old_invoice in tqdm(old_invoices, "Vertragsdaten"):
        try:
            with transaction.atomic():
                total_created += _import_invoice(old_invoice)
        except Exception as e:
            failures += 1
            print(e)
    return failures, total_created


def _import_invoice(old_invoice):
    if not old_invoice.transaction and not old_invoice.datum and not old_invoice.betrag:
        return 0
    positions = old_invoice.gwcbsrechnungenpositionen_set.all()
    starts = [p.von for p in positions if p.von]
    ends = [p.bis for p in positions if p.bis]
    invoice, created = Invoice.objects.get_or_create(
        booking_account=old_invoice.buchungskonto.imported,
        number=old_invoice.id,
        defaults={
            "date": old_invoice.datum,
            "total_net": old_invoice.betrag,
            "total_gross": (
                old_invoice.transaction.betrag
                if old_invoice.transaction
                else old_invoice.betrag * (1 + old_invoice.mwst)
            ),
            "canceled": old_invoice.storniert,
            "billing_start": min(starts) if starts else old_invoice.datum,
            "billing_end": max(ends) if ends else old_invoice.datum,
        },
    )
    old_invoice.imported = invoice
    old_invoice.save()

    tax_rate = old_invoice.mwst * 100
    # matching_contracts = GwCbsVertrag.objects.filter(buchungskontoid=old_invoice.buchungskonto)

    for pos, old_position in enumerate(positions):
        if old_position.buchungskonto != old_invoice.buchungskonto:
            raise Exception(
                f"Rechnungsposition mit abweichendem Buchungskonto in Rechnung {old_invoice.transaction.transaktionid}"
            )
        old_item = None
        if old_position.referenztyp == "gw_cbs_vertrag":
            try:
                old_item = GwCbsVertragPosten.objects.get(id=old_position.referenz)
            except Exception:
                pass
            if old_item and not old_item.imported:
                raise Exception(
                    f"Vertragsposition {old_item.id} (V {old_item.vertragid}) wurde noch nicht importiert!"
                )
        item = InvoiceItem.objects.create(
            order=pos,
            invoice=invoice,
            billing_start=old_position.von or invoice.date,
            billing_end=old_position.bis or invoice.date,
            amount=old_position.anzahl,
            price_single_net=old_position.preis,
            price_total_net=old_position.preis * old_position.anzahl,
            name=old_position.name,
            description=old_position.beschreibung,
            contract_item=old_item.imported if old_item else None,
            tax_rate=tax_rate,
        )
        old_position.imported = item
        old_position.save()
    return created


def import_all(accounts=True, contracts=True, invoices=True, delete=False):
    """Main entrypoint for the big data importer."""
    if accounts:
        total, total_created = import_accounts()
        print(f"Created {total_created} new accounts.")

    if contracts:
        total, total_created = import_contracts()
        print(f"Created {total_created} new contracts.")

    if invoices:
        failures, total_created = import_invoices()
        print(f"Created {total_created} new invoices, failed to create {failures}")


# export
# In [61]: for ba in BookingAccount.objects.all().order_by("id"):
#     ...:     if ba.gwcbs.zustellung.zustellung_post_an:
#     ...:         if ba.gwcbs.gwcbsrechnungen_set.all().filter(datum__year__gte=2021):
#     ...:             data.append({"ID": ba.id, "Original": ba.gwcbs.zustellung.zustellung_post_an, "Firma": ba.address_company, "Straße": ba.address_street, "Zusatz": ba.address_suffix, "Stadt": ba.address_city, "
#     ...: PLZ": ba.address_zip_code, "Land": ba.address_country})
#     ...:


# In [62]:

# In [62]: with open("/adressdaten.csv", "w") as fp:
#     ...:     fp.write('\ufeff')
#     ...:     fieldnames = ["ID", "Original", "Firma", "Zusatz", "Straße", "PLZ", "Stadt", "Land"]
#     ...:     writer = csv.DictWriter(fp, fieldnames=fieldnames)
#     ...:     writer.writeheader()
#     ...:     writer.writerows(data)
#     ...:
