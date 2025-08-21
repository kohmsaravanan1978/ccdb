from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from contracting.utils.easybill import EasybillModel, easybill_request
from globalways.models import GlobalwaysCreatedUpdatedBy, GlobalwaysTool
from globalways.utils.decorators import historify


def get_default_data():
    return {"synced_data": {}}


@historify
class Customer(
    GlobalwaysTool, GlobalwaysCreatedUpdatedBy, TimeStampedModel, EasybillModel
):
    name = models.CharField(max_length=200, null=True, blank=True)
    number = models.PositiveIntegerField(unique=True, verbose_name=_("customer number"))

    crm_data = models.JSONField(default=get_default_data)
    crm_last_sync = models.DateTimeField(null=True, blank=True)

    model_icon = "fa-plug"

    easybill_attributes = [
        "crm_data"
    ]  # If this changes, the easybill sync state is set to "dirty"
    easybill_keys = [
        "company_name",
        "display_name",
        "last_name",
        "number",
        "street",
        "suffix_1",
        "zip_code",
        "city",
        "country",
        "phone_1",
        "vat_identifier",
        "emails",
    ]

    class Meta:
        abstract = False

    def __str__(self):
        return f"{self.name or _('Customer')} ({self.number})"

    def crm_sync(self):
        from contracting.utils.crm import pull_customer_data

        pull_customer_data(customers=[self.number])

    def get_easybill_data(self):
        if not self.crm_data.get("synced_data"):
            return {}
        data = self.crm_data["synced_data"]
        if "firmierung" not in data and "company_name" not in data:
            return {}

        result = {
            "company_name": self.name,
            "display_name": self.name,
            "last_name": "",
            "number": str(self.number),
            "vat_identifier": data["ustid"],
            "emails": [data["email"]] if data["email"] else None,
        }

        if "firmierung" in data:
            # Old CRM scheme
            country = data["land"]
            street = data["strasse"]
            street_number = data["hausnummer"]
            suffix = data["zusatz"]
            zip_code = data["plz"]
            city = data["ort"]
            phone = data["telefon"]
        elif "company_name" in data:
            # Current CRM scheme
            country = data["country"]
            street = data["street"]
            street_number = data["houseno"]
            suffix = data["housenoadd"]
            zip_code = data["zip"]
            city = data["city"]
            phone = data["tel"]

        result["country"] = {"Deutschland": "DE", "Luxembourg": "LU"}.get(country, "DE")
        result["street"] = (
            (street or "").strip() + " " + (street_number or "")
        ).strip()
        result["suffix_1"] = suffix
        result["zip_code"] = zip_code
        result["city"] = city
        result["phone_1"] = phone
        return result

    def _easybill_initial_sync(self):
        data = easybill_request(f"customers?number={self.number}")
        if data and data.get("items") and len(data["items"]):
            self.easybill_id = data["items"][0]["id"]
            self.easybill_data["synced_data"] = {
                k: v for k, v in data["items"][0].items() if k in self.easybill_keys
            }
            self.save()

    def _easybill_sync(self, create=False):
        url = "customers" if create else f"customers/{self.easybill_id}"
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

    def easybill_sync(self):
        sync_data = self.get_easybill_data()
        if not sync_data.get("company_name") or not sync_data.get(
            "street"
        ):  # do not try to push empty data
            return
        self.easybill_data["last_state"] = self.easybill_sync_state
        self.easybill_sync_state = self.States.PENDING
        self.save()
        try:
            if not self.easybill_id:
                # Try to get this customer if it exists
                self._easybill_initial_sync()
            self._easybill_sync(create=not self.easybill_id)

            for account in self.booking_accounts.all():
                account.easybill_sync()
        except Exception as e:
            print(f"Error syncing {self}: {e}")
            self.easybill_sync_state = self.easybill_data["last_state"]
            self.save()
