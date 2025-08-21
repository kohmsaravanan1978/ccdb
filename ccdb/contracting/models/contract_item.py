import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import JSONField, Max, Q
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from contracting.models.contract import DateFromTillQuerySet
from globalways.model_validator import ModelValidator
from globalways.models import GlobalwaysCreatedUpdatedBy, GlobalwaysTool
from globalways.utils.decorators import historify
from main.queue import QueueModelMixin

__all__ = ["ContractItem"]
logger = logging.getLogger(__name__)


def validate_accounting_periods(value):
    """
    We only support `accounting_period` completely fitting into a year. This means the accouting dates are the
    same in in every year. Everything else may mess up next bill calculation.
    """
    if not (value > 0 and 12 % value == 0):
        raise ValidationError(
            str(_("Value must be one of 1, 3, 6, 12, not {error}.")).format(error=value)
        )


class ContractItemQuerySet(DateFromTillQuerySet):
    def valid_before(self, datestamp):
        return self.filter(
            Q(
                Q(valid_till__gte=datestamp)
                | Q(valid_till__isnull=True, contract__valid_till__gte=datestamp)
                | Q(valid_till__isnull=True, contract__valid_till__isnull=True)
            )
        )

    def valid_after(self, datestamp):
        return self.filter(
            Q(
                Q(valid_from__lte=datestamp)
                | Q(valid_from__isnull=True, contract__valid_from__lte=datestamp)
            )
        )


class ContractItemValidator(ModelValidator):
    def validate_contract(self):
        if not getattr(self, "contract", None):
            return
        if (
            self.instance.valid_from or datetime.date.max
        ) < self.instance.contract.valid_from:
            self.add_field_error(
                "valid_from",
                _("valid from date must be after valid from date of the contract"),
            )
        if self.instance.contract.valid_till and self.instance.valid_till:
            if self.instance.valid_till > self.instance.contract.valid_till:
                self.add_field_error(
                    "valid_till",
                    _("valid till date of the contract must be after valid till date"),
                )

    def validate(self):
        self.validate_contract()
        if (self.instance.valid_from or datetime.date.min) > (
            self.instance.valid_till or datetime.date.max
        ):
            self.add_error(_("valid from date must before valid till"))
        if self.instance.price_recurring and int(
            self.instance.price_recurring * 100
        ) != (self.instance.price_recurring * 100):
            self.add_field_error(
                "price_recurring", _("only full cent prices are supported")
            )
        if self.instance.price_setup and int(self.instance.price_setup * 100) != (
            self.instance.price_setup * 100
        ):
            self.add_field_error(
                "price_setup", _("only full cent prices are supported")
            )


@historify
class ContractItem(
    GlobalwaysTool, QueueModelMixin, GlobalwaysCreatedUpdatedBy, TimeStampedModel
):

    class BillingTypes(models.TextChoices):
        ONCE = "once", _("One-off payment")
        RECURRING = "recurring", _("Recurring payments")

    class Status(models.TextChoices):
        IN_DELIVERY = "delivery", _("in delivery")
        ACTIVE = "active", _("active")
        PAUSED = "paused", _("active, paused")
        ENDED = "ended", _("ended")

    number = models.IntegerField(unique=True, verbose_name=_("contract item number"))
    order = models.PositiveIntegerField(default=0)

    contract = models.ForeignKey(
        "contracting.Contract", on_delete=models.CASCADE, related_name="items"
    )
    predecessor = models.OneToOneField(
        "contracting.ContractItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="successor",
    )
    parent_item = models.ForeignKey(
        "contracting.ContractItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_items",
    )

    product_code = models.CharField(max_length=50, verbose_name=_("product code"))
    product_name = models.CharField(max_length=200, verbose_name=_("product name"))
    product_description = models.TextField(
        null=True, blank=True, verbose_name=_("product description")
    )

    valid_from = models.DateField(null=True, blank=True, verbose_name=_("valid from"))
    valid_till = models.DateField(null=True, blank=True, verbose_name=_("valid till"))

    termination_date = models.DateField(
        null=True, blank=True, verbose_name=_("termination date")
    )
    minimum_duration = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("minimum contract duration"),
        help_text=_("Minimum duration in months"),
    )
    notice_period = models.PositiveIntegerField(
        default=3, verbose_name=_("notice period")
    )

    order_reference = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("order reference")
    )
    netbox_reference = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("NetBox reference")
    )
    fibu_account = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("FiBu account")
    )

    price_recurring = models.DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=15,
        verbose_name=_("Recurring price (net)"),
    )  # None means it's not a recurring price, 0 means it's supposed to be included in an invoice
    price_setup = models.DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=15,
        verbose_name=_("Setup price (net)"),
    )  # None means it's not a setup price, 0 means it's supposed to be included in an invoice
    accounting_period = models.PositiveIntegerField(
        validators=[validate_accounting_periods]
    )
    next_invoice = models.DateField(null=True, blank=True)
    last_invoice_override = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Last invoice (override)"),
        help_text=_(
            "Set this field to change the next invoice starting date, e.g. because there have been credits to this account."
        ),
    )

    billing_type = models.CharField(
        max_length=9,
        choices=BillingTypes.choices,
        default=BillingTypes.RECURRING,
        verbose_name=_("Billing type"),
    )
    paused = models.BooleanField(default=False, verbose_name=_("paused"))
    archived = models.BooleanField(
        default=False,
        verbose_name=_("archived"),
        help_text=_("Used to ignore old imported items"),
    )
    ready_for_service = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name=_("Ready for Service"),
        help_text=_("Link to the Ready for Service document"),
    )

    realization_variant = models.TextField(null=True, blank=True)

    realization_site = models.TextField(null=True, blank=True)  # building, by slug
    realization_location = models.TextField(null=True, blank=True)  # room
    realization_rack = models.TextField(null=True, blank=True)
    realization_he = models.TextField(null=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)  # Unused at the moment

    availability_guaranteed = models.DecimalField(
        null=True,
        blank=True,
        max_digits=7,
        decimal_places=5,
        verbose_name=_("Guaranteed availability"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    availability_hours = models.DecimalField(
        null=True,
        blank=True,
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Availability interval in hours"),
        help_text=_(
            "The interval for which availability is guaranteed. Put 8760 for a year, 720 for a month (30 days)."
        ),
    )

    billing_data = models.JSONField(default=dict, blank=True)
    imported_data = JSONField(default=dict, blank=True)  # Unused at the moment

    gnom_id = models.CharField(null=True, blank=True, max_length=200)
    network_information = models.CharField(max_length=200, null=True, blank=True)
    internal_comment = models.TextField(null=True, blank=True)

    objects = ContractItemQuerySet.as_manager()

    def __str__(self):
        return f"{self.number} – {self.product_name} (Vertrag {self.contract.number})"

    model_icon = "fa-clone"
    queue_id_field = "number"
    queue_exchange = "contracts"
    queue_source = "contract.item"
    queue_message_type = "contract"
    queue_create_type = "update"
    queue_delete_type = "update"
    queue_fields = (
        "number",
        "product_code",
        "product_name",
        "product_description",
        "valid_from",
        "valid_till",
        "termination_date",
        "order_reference",
        "netbox_reference",
        "fibu_account",
        "price_recurring",
        "price_setup",
        "billing_type",
        "paused",
        "archived",
        "ready_for_service",
        "realization_variant",
        "realization_site",
        "realization_location",
        "realization_rack",
        "realization_he",
        "availability_guaranteed",
        "availability_hours",
        "gnom_id",
        "network_information",
    )
    queue_field_aliases = {
        "predecessor__number": "predecessor_number",
        "successor__number": "successor_number",
        "parent_item__number": "parent_number",
        "minimum_duration": "minimum_duration_months",
        "notice_period": "notice_period_months",
        "accounting_period": "accounting_period_months",
    }

    def _serialize_queue_create(self, nested=False):
        # The nested version is called from Contract._serialize_queue_create, so we don't
        # need to add the outer contract layer.
        payload = super()._serialize_queue_create()
        if nested:
            return payload
        return {"number": self.contract.number, "items": [payload]}

    def _serialize_queue_update(self):
        payload = super()._serialize_queue_update()
        if len(payload) == 1:
            return payload
        return {"number": self.contract.number, "items": [payload]}

    def _serialize_queue_delete(self):
        return {
            "number": self.contract.number,
            "items": [{"number": self.number, "deleted": True}],
        }

    class Meta:
        ordering = ("number",)
        verbose_name = _("Contract Item")
        verbose_name_plural = _("Contract Items")
        base_manager_name = "objects"

    def save(self, **kwargs):
        if not self.number:
            max_number = (
                ContractItem.objects.all()
                .aggregate(max_number=Max("number"))
                .get("max_number")
                or 0
            )
            self.number = max_number + 1
        self.full_clean()
        super().save(**kwargs)

    def clean(self):
        super().clean()
        validator = ContractItemValidator(self)
        validator.run()

    def get_name(self):
        return self.number

    def get_absolute_url(self):
        return reverse("contracting:contract_item_detail", args=[str(self.pk)])

    @property
    def net_price_recurring_cent(self):
        return int(self.price_recurring * 100)

    @property
    def net_price_setup_cent(self):
        return int(self.price_setup * 100)

    @property
    def can_be_deleted(self):
        return False

    @property
    def status(self):
        # TODO double-check logic
        today = now().date()
        valid_from = self.valid_from or self.contract.valid_from
        valid_till = self.valid_till or self.contract.valid_till
        if not self.ready_for_service:
            return self.Status.IN_DELIVERY
        if not valid_from or today < valid_from:
            return self.Status.IN_DELIVERY
        if not valid_till or today <= valid_till:
            if self.paused:
                return self.Status.PAUSED
            return self.Status.ACTIVE
        return self.Status.ENDED

    def get_status_display(self):
        return self.status.label

    @staticmethod
    def get_next_number():
        last_contract = ContractItem.objects.order_by("number").last()
        return (last_contract.number if last_contract else 0) + 1

    def cancel(self, date=None):
        self.termination_date = now()
        if date:
            self.valid_till = date
        else:
            self.valid_till = self.contract.next_possible_contract_end
            if (
                now() > self.contract.next_cancelation_date
                and self.contract.automatic_extension
            ):
                self.valid_till += relativedelta(
                    months=self.contract.automatic_extension
                )
        if self.next_invoice >= self.valid_till:
            self.next_invoice = None
        self.save()

    def pause(self):
        self.paused = True
        self.save()

    def unpause(self):
        self.paused = False
        self.save()
