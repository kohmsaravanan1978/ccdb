import datetime
import logging

from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import JSONField, Max, Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from globalways.model_validator import ModelValidator
from globalways.models import GlobalwaysCreatedUpdatedBy, GlobalwaysTool
from globalways.utils.decorators import historify
from main.queue import QueueModelMixin

__all__ = ["Contract"]

logger = logging.getLogger(__name__)


class DateFromTillQuerySet(models.QuerySet):
    def valid_before(self, datestamp):
        return self.filter(Q(Q(valid_till__gte=datestamp) | Q(valid_till__isnull=True)))

    def valid_after(self, datestamp):
        return self.filter(valid_from__lte=datestamp)

    def not_expired(self):
        return self.valid_before(datetime.date.today())

    def valid_on(self, datestamp):
        if not datestamp:
            return self.model.objects.none()
        return self.valid_before(datestamp).valid_after(datestamp)

    def valid_between(self, valid_from, valid_to):
        return self.valid_before(valid_to).valid_after(valid_from)

    def not_started(self):
        return self.filter(
            valid_from__gt=datetime.date.today(),
        )

    def ended(self):
        # This does not include the future (ended) contracts
        return self.filter(
            valid_till__lt=datetime.date.today(),
        )


class ContractQuerySet(DateFromTillQuerySet):
    def terminated(self):
        # This includes all contract that have a termination date set,
        # but still running (otherwise they are in .ended() or .not_started())
        return self.filter(
            termination_date__isnull=False,
            valid_from__lte=datetime.date.today(),
            valid_till__gte=datetime.date.today(),
        )

    def not_terminated(self):
        return self.filter(termination_date__isnull=True)

    def accounted_together_with(self, contract):
        """
        This returns a QuerySet that represent all contracts that will be accounted with the given contract.
        Following fields are enforced because otherwise a collective invoice may be invalid
          * collective_invoice : Must be common - nothing else makes sense
          * booking_account : We enforce that only contracts of one customer is in the collective invoice

        Note that this does not respect any time ranges. You may use the other QuerySet methods to filter this.
        """
        qs = self.filter(
            collective_invoice=contract.collective_invoice,
            booking_account=contract.booking_account,
        )
        return qs.distinct()


class ContractValidator(ModelValidator):
    def validate_sepa(self):
        if self.instance.sepa_enabled and (
            not self.instance.valid_till or self.instance.valid_till > now().date()
        ):
            sepa = getattr(self.instance.booking_account, "sepa", None)
            if not sepa or not sepa.is_valid():
                self.add_error(
                    _(
                        "customer SEPA information requirements are not met. Can not enable SEPA for this contract"
                    ),
                )

    def validate(self):
        self.validate_sepa()
        if (
            self.instance.valid_till
            and self.instance.valid_from > self.instance.valid_till
        ):
            self.add_error(_("contract valid from date must before valid till"))
        for ci in self.instance.items.all():
            try:
                ci.full_clean()
            except ValidationError as e:
                self.add_error(
                    _(
                        'contract "{}" (pk={}) item have conflicting value. (Error is: {})'
                    ).format(ci, ci.pk, list(e.error_dict.values()))
                )


@historify
class Contract(
    GlobalwaysTool, QueueModelMixin, GlobalwaysCreatedUpdatedBy, TimeStampedModel
):

    name = models.CharField(max_length=200)
    number = models.IntegerField(unique=True, verbose_name=_("contract number"))
    booking_account = models.ForeignKey(
        "contracting.BookingAccount", related_name="contracts", on_delete=models.PROTECT
    )

    order_date = models.DateField(
        null=True, blank=True, verbose_name=_("order date")
    )  # Auftragseingang
    termination_date = models.DateField(
        null=True, blank=True, verbose_name=_("termination date")
    )

    valid_from = models.DateField(verbose_name=_("valid from"))  # Vertragsbeginn
    valid_till = models.DateField(
        null=True, blank=True, verbose_name=_("valid till")
    )  # Vertragsende

    minimum_duration = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("minimum contract duration"),
        help_text=_("Minimum duration in months"),
    )
    notice_period = models.PositiveIntegerField(
        default=3, verbose_name=_("notice period")
    )
    automatic_extension = models.PositiveIntegerField(
        default=12, verbose_name=_("automatic extension")
    )
    collective_invoice = models.BooleanField(default=True)

    order_reference = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("order reference")
    )

    jira_offer_reference = models.CharField(
        max_length=300, blank=True, null=True, verbose_name=_("Jira offer reference")
    )
    jira_ticket = models.CharField(
        max_length=300, blank=True, null=True, verbose_name=_("Jira ticket")
    )
    ready_for_service = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name=_("Ready for Service"),
        help_text=_("Link to the Ready for Service document"),
    )

    comment = models.TextField(null=True, blank=True, verbose_name=_("comment"))
    special_conditions = models.TextField(
        null=True, blank=True, verbose_name=_("special conditions")
    )

    billing_data = JSONField(
        default=dict, null=True, blank=True
    )  # Unused at the moment
    imported_data = JSONField(
        default=dict, null=True, blank=True
    )  # Unused at the moment

    objects = ContractQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    model_icon = "fa-file-signature"
    queue_id_field = "number"
    queue_exchange = "contracts"
    queue_source = "contract"
    queue_message_type = "contract"
    queue_fields = [
        "number",
        "name",
        "order_date",
        "termination_date",
        "valid_from",
        "valid_till",
        "order_reference",
        "jira_offer_reference",
        "jira_ticket",
        "ready_for_service",
        "comment",
        "special_conditions",
        "next_cancelation_date",
        "next_possible_contract_end",
    ]
    queue_field_aliases = {
        "booking_account__customer__number": "customer_number",
        "minimum_duration": "minimum_duration_months",
        "notice_period": "notice_period_months",
        "automatic_extension": "automatic_extension_months",
    }

    class Meta:
        ordering = ("number",)
        verbose_name = _("contract")
        verbose_name_plural = _("contracts")
        base_manager_name = "objects"

    @cached_property
    def sepa_enabled(self):
        return self.booking_account.payment_type == self.booking_account.Types.SEPA

    def collective_invoice_common_fields_lookup(self):
        return {
            self._meta.get_field("booking_account").verbose_name: self.booking_account
        }

    @property
    def customer_number(self):
        return self.booking_account.customer.number

    def invoices(self):
        from .invoice import Invoice

        return Invoice.objects.filter(items__contract_item__contract=self)

    @property
    def next_cancelation_date(self):
        return (
            self.next_possible_contract_end
            - relativedelta(months=self.notice_period)
            - relativedelta(day=31)
        )

    @property
    def next_possible_contract_end(self):
        today = datetime.date.today()
        end_date = self.valid_from + relativedelta(months=self.minimum_duration)
        if self.automatic_extension:
            while end_date - relativedelta(months=(self.notice_period - 1)) <= today:
                end_date += relativedelta(months=self.automatic_extension)
        return end_date - relativedelta(days=1) - relativedelta(day=31)

    def save(self, **kwargs):
        if not self.number:
            max_number = (
                Contract.objects.all()
                .aggregate(max_number=Max("number"))
                .get("max_number")
                or 0
            )
            self.number = max_number + 1
        with transaction.atomic():
            super().save(**kwargs)
            self.full_clean()

    def clean(self):
        super().clean()
        validator = ContractValidator(self)
        validator.run()

    def cancel(self, date=None):
        self.termination_date = now()
        if date:
            if date < self.next_possible_contract_end:
                raise ValidationError(
                    {
                        "termination_date": f"Termination date must be after {self.next_possible_contract_end}, not {date}"
                    }
                )
            self.valid_till = date
        else:
            self.valid_till = self.next_possible_contract_end
            if now().date() > self.next_cancelation_date and self.automatic_extension:
                self.valid_till += relativedelta(months=self.automatic_extension)
        self.save()
        self.items.all().filter(
            valid_till__isnull=True, next_invoice__gte=self.valid_till
        ).update(next_invoice=None)

    def unpause(self):
        self.items.all().update(paused=False)

    def pause(self):
        self.items.all().update(paused=True)

    def collective_invoice_contracts(self):
        return Contract.objects.accounted_together_with(self)

    def get_easybill_customer(self):
        return self.booking_account.customer.easybill_customer

    @property
    def duration(self):
        end = self.valid_till or datetime.date.today()
        return end - self.valid_from

    @property
    def duration_months(self):
        end = self.valid_till or datetime.date.today()
        return len([dt for dt in rrule(MONTHLY, dtstart=self.valid_from, until=end)])

    @cached_property
    def customer(self):
        return self.booking_account.customer

    @property
    def is_reverse_charge(self):
        return self.booking_account.tax_option == self.booking_account.TaxOptions.IG

    def get_name(self):
        return "{} ({})".format(self.name, self.number)

    def get_absolute_url(self):
        return reverse("contracting:contract_detail", args=[str(self.pk)])

    @property
    def can_be_deleted(self):
        return False

    def get_status(self):
        # TODO. status logic!
        today = datetime.date.today()
        from .contract_item import ContractItem

        if not self.ready_for_service:
            return ContractItem.Status.IN_DELIVERY
        if self.valid_till:
            if self.valid_till >= today:
                # TODO terminated status
                return ContractItem.Status.ACTIVE
            else:
                return ContractItem.Status.ENDED
        else:
            if self.valid_from > today:
                return ContractItem.Status.IN_DELIVERY
            if self.ready_for_service:
                return ContractItem.Status.ACTIVE
            # TODO is this right
            return ContractItem.Status.PAUSED

    @property
    def activate_url(self):
        return reverse("contracting:contract_activate", args=[self.pk])

    def _serialize_queue_create(self):
        self.refresh_from_db()
        result = super()._serialize_queue_create()
        result["items"] = [
            item._serialize_queue_create(nested=True) for item in self.items.all()
        ]
        return result
