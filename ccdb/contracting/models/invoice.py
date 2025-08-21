import os
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from contracting.utils.easybill import EasybillModel, easybill_request
from globalways.models import GlobalwaysModel


def path_with_hash(name):
    dir_name, file_name = os.path.split(name)
    file_root, file_ext = os.path.splitext(file_name)
    random = get_random_string(7)
    return os.path.join(dir_name, f"{file_root}_{random}{file_ext}")


def get_document_path(instance, filename):
    return f"documents/{instance.date.year}/{path_with_hash(filename)}"


class Transaction(GlobalwaysModel, EasybillModel):
    """This is the base class for invoices and credit notes, to make it easier to aggregate all payments against one account.
    We don't intend to instantiate it, but it's needed to provide easy access to credits and invoices in a single query.
    """

    number = models.PositiveIntegerField(null=True, blank=True)  # assigned by easybill
    booking_account = models.ForeignKey(
        "contracting.BookingAccount",
        related_name="transactions",
        on_delete=models.PROTECT,
    )

    total_net = models.DecimalField(
        default=0, decimal_places=2, max_digits=15, verbose_name=_("total amount (net)")
    )
    total_gross = models.DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=15,
        verbose_name=_("total amount (net)"),
    )
    document = models.FileField(
        null=True,
        blank=True,
        upload_to=get_document_path,
        verbose_name=_("File"),
    )

    canceled = models.BooleanField(default=False)

    date = models.DateField()

    billing_data = models.JSONField(default=dict)

    class Meta:
        ordering = ("date",)

    @property
    def document_url(self):
        if not self.document:
            return None
        return f"/downloads/invoice/{self.number}/"


class Invoice(Transaction):
    class SepaTypes(models.TextChoices):
        FIRST = "FRST", _("first SEPA transaction")
        RCUR = "RCUR", _("recurring SEPA transaction")

    # Billing start and end should be in sync with all items, but we still want convenient access
    billing_start = models.DateField()
    billing_end = models.DateField()

    approved = models.BooleanField(
        default=True
    )  # False blocks pushes to EasyBill until resolved

    sepa_transaction_type = models.CharField(
        null=True, blank=True, choices=SepaTypes.choices, max_length=4
    )

    easybill_keys = [
        "contact_id",
        "customer_id",
        "document_date",
        "service_date",
        "pdf_template",
        "text",
        "text_prefix",
        "is_draft",
    ]

    def get_easybill_data_items(self, with_objects=False):
        result = []
        grouped_items = defaultdict(list)
        for item in self.items.all().order_by("id"):
            if not item.contract_item:
                grouped_items[None].append(item)
            else:
                grouped_items[item.contract_item.contract].append(item)

        # group existing lines by contract
        for contract, invoice_lines in grouped_items.items():
            reference = ""
            if contract:
                if contract.order_reference:
                    reference = f" | Ihre Bestellreferenz {contract.order_reference}"
                result.append(
                    {
                        "description": f"<strong><br>Leistungen für Vertrag {contract.number}{reference}</strong>",
                        "item_type": "UNDEFINED",
                        "type": "TEXT",
                    }
                )
            else:
                result.append(
                    {
                        "description": "<strong><br>Sonstige Leistungen</strong>",
                        "item_type": "UNDEFINED",
                        "type": "TEXT",
                    }
                )
            for line in invoice_lines:
                description = line.description
                if line.name:
                    description = f"<b>{line.name}</b>:\r\n{description}"
                if line.contract_item and line.contract_item.order_reference:
                    description = f"{description}\r\nIhre Bestellreferenz {line.contract_item.order_reference}"
                data = {
                    "number": line.id,
                    "description": description,
                    "item_type": "PRODUCT",
                    "quantity": float(line.amount),
                    "single_price_gross": float(line.price_single_gross * 100),
                    "single_price_net": float(line.price_single_net * 100),
                    "vat_percent": int(line.tax_rate),
                    "type": "POSITION",
                    "booking_account": (
                        line.contract_item.fibu_account if line.contract_item else ""
                    ),
                }
                if with_objects:
                    data["obj"] = line
                if (
                    not line.is_recurring
                    and line.contract_item
                    and line.contract_item.price_recurring
                    and data["booking_account"] == 4440
                ):
                    # If the invoice line is a setup price (i.e. it is not
                    # recurring BUT the item has a recurring component), we
                    # adjust the booking account manually
                    data["booking_account"] = 4441
                result.append(data)
            if len(grouped_items) > 1 and contract:
                result.append(
                    {
                        "description": f'<strong>Summe für Vertrag {contract.number}: %position.gruppensumme(1)%</strong><div class="fr-second-toolbar"></div>',
                        "item_type": "UNDEFINED",
                        "type": "TEXT",
                    }
                )
        return result

    @property
    def xrechnung_order_reference(self):
        order_number = None
        for item in self.items.all():
            order_number = (
                item.contract_item.contract.order_reference
                if item.contract_item
                else None
            )
            if order_number:
                break
        return order_number or ""

    def get_easybill_data(self):
        data = {
            "contact_id": self.booking_account.easybill_id,
            "customer_id": self.booking_account.customer.easybill_id,
            "document_date": self.date.isoformat(),
            "service_date": {
                "type": "SERVICE",
                "date_from": self.billing_start.isoformat(),
                "date_to": self.billing_end.isoformat(),
            },
            "pdf_template": "DE",
            "type": "INVOICE",
            "items": self.get_easybill_data_items(),
        }
        if (
            self.booking_account.invoice_type
            == self.booking_account.InvoiceTypes.XRECHNUNG
        ):
            data["buyer_reference"] = (
                self.booking_account.xrechnung_buyer_reference or ""
            )
            data["order_number"] = self.xrechnung_order_reference
        if self.booking_account.tax_option != "NULL":
            data["vat_option"] = self.booking_account.tax_option
        if (
            self.booking_account.payment_type == self.booking_account.Types.SEPA
            and hasattr(self.booking_account, "sepa")
        ):
            sepa = self.booking_account.sepa
            if sepa.is_valid() and not sepa.revoked:
                data["text"] = (
                    f"""<strong>Zahlungsbedingungen</strong><br>
Die Zahlung wird per SEPA-Basis-Lastschrift ohne Abzug zum %DATUM+3TAGE% eingezogen:<br><br>
SEPA-Mandatsreferenz: {sepa.reference}<br>
Gläubiger-Identifikationsnummer: %FIRMA.SEPA-GLAEUBIGERID%<br>
Bankverbindung: IBAN: {sepa.iban} ({sepa.bank_name})<br><br>
Mit freundlichen Grüßen<br>
Globalways GmbH """.replace(
                        "\n", ""
                    )
                )
        return data

    def _easybill_sync(self):
        url = "documents"
        method = "POST"
        if self.easybill_id:
            url = f"{url}/{self.easybill_id}"
            method = "PUT"
        data = self.get_easybill_data()
        if not self.easybill_id:
            data["is_draft"] = True
        response = easybill_request(url, method=method, data=data)
        self.easybill_id = response["id"]
        self.easybill_data["synced_data"] = {
            k: v for k, v in response.items() if k in self.easybill_keys
        }
        item_data = self.get_easybill_data_items(with_objects=True)
        for local_item, easybill_item in zip(item_data, response["items"]):
            if "obj" not in local_item:
                continue
            item = local_item["obj"]
            item.easybill_last_sync = now()
            item.easybill_sync_state = self.States.SYNCED
            item.easybill_data["synced_data"] = easybill_item
            item.easybill_id = easybill_item["id"]
            item.save()

        # now finalize the document
        response = easybill_request(f"documents/{self.easybill_id}/done", method="PUT")
        self.number = response["number"]
        response = easybill_request(f"documents/{self.easybill_id}/pdf", method="GET")
        pdf_file = SimpleUploadedFile(f"{self.number}.pdf", response)
        self.document.save(f"{self.number}.pdf", pdf_file)

        self.easybill_last_sync = now()
        self.easybill_sync_state = self.States.SYNCED
        self.save()

    def _easybill_delivery(self):
        if settings.TEST_MODE:
            print("Skipping invoice delivery due to TEST_MODE=1")
            return
        if (
            self.booking_account.invoice_delivery_email
            and self.booking_account.address_email
        ):
            if self.easybill_data.get("email_delivery"):
                print(f"WARNING re-sending invoice email for {self.number}")
            data = {"document_file_type": self.booking_account.invoice_type}
            easybill_request(
                f"documents/{self.easybill_id}/send/email", method="POST", data=data
            )
            self.easybill_data["email_delivery"] = now().isoformat()
            self.save()

    def _easybill_sepa(self):
        if self.easybill_data.get("sepa"):
            print("Already has sepa payment")
            return
        if (
            self.booking_account.payment_type != self.booking_account.Types.SEPA
            or not hasattr(self.booking_account, "sepa")
        ):
            return
        sepa = self.booking_account.sepa
        if not sepa.is_valid() or sepa.revoked or not self.total_gross:
            return

        remittance_information = (
            f"RNr: {self.number} vom {self.date.strftime('%d.%m.%Y')}\n"
            f"KNr: {self.booking_account.customer.number}\n"
            f"Mandatsreferenz: {sepa.reference} vom {sepa.confirmed.strftime('%d.%m.%Y')}\n"
        )[:70]
        data = {
            "amount": int(self.total_gross * 100),
            "document_id": self.easybill_id,
            "reference": self.number,
            "remittance_information": remittance_information[:140],
            "type": "DEBIT",
            **sepa.easybill_invoicing_data(),
        }

        response = easybill_request("sepa-payments", method="POST", data=data)

        self.easybill_data["sepa"] = response
        self.easybill_sync_state = self.States.SYNCED
        self.save()
        sepa.update_used()

    def easybill_sync(self):
        if self.number:
            raise Exception(
                f"Invoice {self.number} already has a number, cannot push new data."
            )
        if self.booking_account.id == 11844:
            return

        if not self.approved:
            raise Exception(f"Not syncing unapproved invoice ID {self.id}")

        if self.easybill_sync_state == self.States.PENDING:
            raise Exception(f"Push already in progress for Invoice ID {self.id}")

        self.easybill_data["last_state"] = self.easybill_sync_state
        self.easybill_sync_state = self.States.PENDING
        self.save()
        try:
            if (
                not self.booking_account.easybill_id
                or self.booking_account.easybill_dirty
            ):
                self.booking_account.easybill_sync()
            self._easybill_sync()
            self._easybill_delivery()
            self._easybill_sepa()
        except Exception as e:
            print(f"Error syncing {self}: {e}")
            self.easybill_sync_state = self.easybill_data["last_state"]
            self.save()

    def update_totals(self):
        self.total_net = sum(item.price_total_net for item in self.items.all())
        self.total_gross = sum(item.price_total_gross for item in self.items.all())

    def save(self, *args, **kwargs):
        if self.id:
            self.update_totals()
        return super().save(*args, **kwargs)


class InvoiceItem(GlobalwaysModel, EasybillModel):
    order = models.PositiveIntegerField()
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="items")
    contract_item = models.ForeignKey(
        "contracting.ContractItem",
        on_delete=models.PROTECT,
        related_name="invoice_items",
        null=True,
        blank=True,
    )  # nullable for imported data

    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()

    amount = models.DecimalField(
        default=1,
        decimal_places=3,
        max_digits=15,
        verbose_name=_("Invoice line amount"),
    )
    price_single_net = models.DecimalField(
        default=0,
        decimal_places=2,
        max_digits=15,
        verbose_name=_("single item amount (net)"),
    )
    price_total_net = models.DecimalField(
        default=0, decimal_places=2, max_digits=15, verbose_name=_("total amount (net)")
    )
    tax_rate = models.DecimalField(
        default="19",
        choices=((Decimal("19"), "19"), (Decimal("0"), "0")),
        verbose_name=_("Tax rate"),
        decimal_places=1,
        max_digits=4,
    )
    is_recurring = models.BooleanField(default=True)

    billing_start = models.DateField()
    billing_end = models.DateField()

    class Meta:
        ordering = (
            "invoice",
            "order",
        )

    def save(self, *args, **kwargs):
        self.price_total_net = self.price_single_net * self.amount
        self.tax_rate = self.invoice.booking_account.tax_rate
        result = super().save(*args, **kwargs)
        self.invoice.update_totals()
        return result

    @property
    def tax_rate_factor(self):
        return 1 + (self.tax_rate / 100)

    @property
    def price_single_gross(self):
        return self.price_single_net * self.tax_rate_factor

    @property
    def price_total_gross(self):
        return self.price_total_net * self.tax_rate_factor


class CreditMemo(Transaction):
    pass
