from decimal import Decimal

from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from contracting.utils.easybill import EasybillModel, easybill_request
from globalways.models import GlobalwaysCreatedUpdatedBy, GlobalwaysTool
from globalways.utils.decorators import historify


@historify
class BookingAccount(
    GlobalwaysTool, GlobalwaysCreatedUpdatedBy, TimeStampedModel, EasybillModel
):
    """Buchungskonto.
    Named like this because just 'account' is too ambiguous."""

    model_icon = "fa-plug"

    easybill_keys = [
        "first_name",
        "last_name",
        "street",
        "city",
        "company_name",
        "zip_code",
        "country",
        "emails",
        "note",
        "personal",
        "salutation",
    ]
    easybill_attributes = [
        "address_email",
        "address_name",
        "address_company",
        "address_street",
        "address_suffix",
        "address_city",
        "address_zip_code",
        "address_country",
    ]

    class Types(models.TextChoices):
        SEPA = "SEPA", _("SEPA direct debit")
        INVOICE = "INVOICE", _("Invoice")
        NONE = "NONE", _("No data (historic import)")

    class InvoiceTypes(models.TextChoices):
        ZUGFERD = "zugferd2_2", _("Zugferd 2")
        XRECHNUNG = "xrechnung3_0_xml", _("XRechnung (XML)")

    class TaxOptions(models.TextChoices):
        """Follows the EasyBill document API"""

        NULL = "NULL", _("Normal steuerbar")
        nStb = "nStb", _("Nicht steuerbar (Drittland)")
        nStbUstID = "nStbUstID", _("Nicht steuerbar (EU mit USt-IdNr.)")
        nStbNoneUstID = "nStbNoneUstID", _("Nicht steuerbar (EU ohne USt-IdNr.)")
        nStbIm = "nStbIm", _("Nicht steuerbarer Innenumsatz")
        revc = "revc", _("Steuerschuldwechsel §13b (Inland)")
        IG = "IG", _("Innergemeinschaftliche Lieferung")
        AL = "AL", _("Ausfuhrlieferung")
        sStfr = "sStfr", _("sonstige Steuerbefreiung")
        smallBusiness = "smallBusiness", _("Kleinunternehmen (Keine MwSt.)")

    customer = models.ForeignKey(
        to="contracting.Customer",
        on_delete=models.PROTECT,
        related_name="booking_accounts",
    )

    payment_type = models.CharField(
        max_length=7,
        choices=Types.choices,
        default=Types.INVOICE,
        verbose_name=_("Account type"),
    )
    invoice_type = models.CharField(
        max_length=16,
        choices=InvoiceTypes.choices,
        default=InvoiceTypes.ZUGFERD,
        verbose_name=_("Invoice type"),
    )
    invoice_delivery_email = models.BooleanField(default=False)
    invoice_delivery_post = models.BooleanField(default=False)

    payment_term = models.PositiveIntegerField(
        default=14, verbose_name=_("Payment term"), help_text=_("In days")
    )
    tax_rate = models.DecimalField(
        default="19",
        choices=((Decimal("19.0"), "19"), (Decimal("0.0"), "0")),
        verbose_name=_("Tax rate"),
        decimal_places=1,
        max_digits=4,
    )
    tax_option = models.CharField(
        max_length=13,
        choices=TaxOptions.choices,
        default=TaxOptions.NULL,
        verbose_name=_("Tax options"),
    )
    xrechnung_buyer_reference = models.CharField(null=True, blank=True, max_length=200)

    address_email = models.CharField(max_length=200, null=True, blank=True)

    address_name = models.CharField(max_length=200, null=True, blank=True)
    address_company = models.CharField(max_length=200, null=True, blank=True)
    address_street = models.CharField(max_length=200, null=True, blank=True)
    address_suffix = models.CharField(max_length=200, null=True, blank=True)
    address_city = models.CharField(max_length=200, null=True, blank=True)
    address_zip_code = models.CharField(max_length=10, null=True, blank=True)
    address_country = models.CharField(max_length=200, null=True, blank=True)

    comment = models.TextField(null=True, blank=True)

    class Meta:
        abstract = False

    def __str__(self):
        return (
            "Buchungskonto "
            + (self.customer.name or self.address_company or self.address_name or "")
            + f" ({self.id}, Kunde {self.customer.number})"
        )

    def get_easybill_data(self):
        name = []
        if self.address_name:
            name = self.address_name.split(" ", maxsplit=1)
        if len(name) == 1:
            name = ["", name[0]]
        elif len(name) == 0:
            name = [None, None]
        return {
            "first_name": name[0],
            "last_name": name[1],
            "suffix_1": self.address_suffix,
            "street": self.address_street,
            "city": self.address_city,
            "company_name": self.address_company,
            "zip_code": self.address_zip_code,
            "country": self.address_country or "DE",  # Two letter code
            "emails": (
                [e.strip() for e in self.address_email.split(",")]
                if self.address_email
                else []
            ),
            "note": self.pk,
            "personal": False,
            "salutation": 0,  # empty
        }

    def _easybill_initial_sync(self):
        data = easybill_request(f"customers/{self.customer.easybill_id}/contacts")
        if data and data.get("items") and len(data["items"]):
            for contact in data["items"]:
                if str(contact["note"]) == str(self.pk):
                    self.easybill_id = contact["id"]
                    self.easybill_data["synced_data"] = {
                        k: v
                        for k, v in data["items"][0].items()
                        if k in self.easybill_keys
                    }
                    self.save()
                    break

    def _easybill_sync(self, create=False):
        url = f"customers/{self.customer.easybill_id}/contacts"
        if not create:
            url = f"{url}/{self.easybill_id}"
        method = "POST" if create else "PUT"
        response = easybill_request(url, method=method, data=self.get_easybill_data())
        if create:
            self.easybill_id = response["id"]
        self.easybill_data["synced_data"] = {
            k: v for k, v in response.items() if k in self.easybill_keys
        }
        self.easybill_last_sync = now()
        self.easybill_sync_state = self.States.SYNCED
        self.save()

    def easybill_sync(self, sync_customer=False):
        if not self.customer.easybill_id or (
            sync_customer
            and not self.customer.easybill_sync_state == self.customer.States.SYNCED
        ):
            self.customer.easybill_sync()
        sync_data = self.get_easybill_data()
        if not sync_data.get("street"):  # do not try to push empty data
            print(f"Not pushing empty data for booking account {self.id}")
            return
        self.easybill_data["last_state"] = self.easybill_sync_state
        self.easybill_sync_state = self.States.PENDING
        self.save()
        try:
            if not self.easybill_id:
                # Try to get this customer if it exists
                self._easybill_initial_sync()
            self._easybill_sync(create=not self.easybill_id)
        except Exception as e:
            print(f"Error syncing {self}: {e}")
            self.easybill_sync_state = self.easybill_data["last_state"]
            self.save()


@historify
class BookingAccountSepa(
    GlobalwaysTool, GlobalwaysCreatedUpdatedBy, TimeStampedModel, models.Model
):
    account = models.OneToOneField(
        BookingAccount, related_name="sepa", on_delete=models.CASCADE
    )

    confirmed = models.DateField(blank=True, null=True, verbose_name=_("confirmed on"))
    revoked = models.DateTimeField(blank=True, null=True, verbose_name=_("revoked on"))

    first_used = models.DateTimeField(blank=True, null=True)
    last_used = models.DateTimeField(blank=True, null=True)

    account_owner = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=64)
    bic = models.CharField(max_length=11)
    iban = models.CharField(max_length=34)
    reference = models.CharField(max_length=35)
    address_street = models.CharField(max_length=150)
    address_zip_code = models.CharField(max_length=20)
    address_city = models.CharField(max_length=100)
    address_country = models.CharField(max_length=2, default="DE")

    class Meta:
        abstract = False

    def is_valid(self):
        return (
            self.account_owner
            and self.bank_name
            and self.bic
            and self.iban
            and self.reference
            and self.address_street
            and self.address_zip_code
            and self.address_city
        )

    def easybill_invoicing_data(self):
        return {
            "debitor_bic": self.bic,
            "debitor_iban": self.iban,
            "debitor_name": self.account_owner,
            "debitor_address_line_1": self.address_street,
            "debitor_address_line_2": f"{self.address_zip_code} {self.address_city}",
            "debitor_country": self.address_country,
            "local_instrument": "CORE",
            "mandate_date_of_signature": self.confirmed.isoformat(),
            "mandate_id": self.reference,  # TODO get mandate id
            "sequence_type": (
                "FRST" if not (self.first_used or self.last_used) else "RCUR"
            ),
        }

    def update_used(self):
        self.first_used = self.first_used or now()
        self.last_used = now()
        self.save()
