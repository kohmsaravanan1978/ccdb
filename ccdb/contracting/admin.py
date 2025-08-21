from django.contrib import admin
from django.db.models import JSONField, TextField
from django.forms import Textarea
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from jsoneditor.forms import JSONEditor
from contracting.resources import CustomerResource
from contracting.resources import BookingAccountResource
from contracting.resources import ContractResource

from contracting import models, tasks


@admin.register(models.ContractItem)
class ContractItemAdmin(admin.ModelAdmin):
    model = models.ContractItem
    permission_group_required = ()
    list_filter = [
        "paused",
        "contract__booking_account",
    ]
    search_fields = [
        "product_name",
        "product_description",
        "number",
        "contract__number",
    ]
    actions = ["pause", "unpause", "cancel"]

    def get_search_results(self, request, queryset, search_term):

        # Check if search term matches "Vertrag <number>" pattern
        if search_term.lower().startswith("vertrag "):
            try:
                contract_number = search_term.split(" ", 1)[1].strip()
                queryset = queryset.filter(contract__number=contract_number)
                return queryset, False
            except IndexError:
                pass

        return super().get_search_results(request, queryset, search_term)

    @admin.action(description=_("Pause all items in selected contracts"))
    def pause(self, request, queryset):
        for item in queryset:
            item.pause()

    @admin.action(description=_("Unpause all items in selected contracts"))
    def unpause(self, request, queryset):
        for item in queryset:
            item.unpause()

    @admin.action(description=_("Cancel all items in selected contracts"))
    def cancel(self, request, queryset):
        for item in queryset:
            item.cancel()


class ContractItemInlineAdmin(admin.StackedInline):
    model = models.ContractItem
    autocomplete_fields = [
        "predecessor",
        "parent_item",
    ]
    formfield_overrides = {
        TextField: {"widget": Textarea(attrs={"rows": 3})},
    }
    readonly_fields = ["number"]
    extra = 0

    def get_readonly_fields(self, request, obj):
        r = list(super().get_readonly_fields(request, obj))
        if obj and obj.ready_for_service:
            r += [
                "price_recurring",
                "price_setup",
            ]
        return r



@admin.register(models.Contract)
class ContractAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ContractResource
    permission_group_required = ()
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
        TextField: {"widget": Textarea(attrs={"rows": 3})},
    }
    inlines = [
        ContractItemInlineAdmin,
    ]
    line_model = models.ContractItem
    list_display = [
        "number",
        "name",
        "valid_from",
        "valid_till",
        "termination_date",
        "booking_account",
    ]
    list_filter = ["valid_from", "valid_till", "termination_date", "items__paused"]
    search_fields = [
        "number",
        "booking_account__id",
        "booking_account__address_name",
        "booking_account__address_company",
        "booking_account__customer__number",
        "items__number",
        "items__product_name",
        "items__product_description",
    ]
    list_editable = []
    autocomplete_fields = [
        "booking_account",
    ]

    # Number is not readonly anymore to allow manual assignment
    # Uniqueness is still guaranteed by the database
    # readonly_fields = ["number"]
    ordering = ("-number",)
    actions = ["pause", "unpause", "cancel", "run_invoicing"]

    @admin.action(description=_("Pause all items in selected contracts"))
    def pause(self, request, queryset):
        for item in queryset:
            item.pause()

    @admin.action(
        description=_("Run invoicing (for all contracts, not just selected ones)")
    )
    def run_invoicing(self, request, queryset):
        tasks.run_invoicing.apply_async()

    @admin.action(description=_("Unpause all items in selected contracts"))
    def unpause(self, request, queryset):
        for item in queryset:
            item.unpause()

    @admin.action(description=_("Cancel all items in selected contracts"))
    def cancel(self, request, queryset):
        for item in queryset:
            item.cancel()

    def get_queryset(self, *args, **kwargs):
        return (
            super()
            .get_queryset(*args, **kwargs)
            .select_related("booking_account", "booking_account__customer")
            .prefetch_related("items", "items__predecessor", "items__parent_item")
        )


class SepaAdmin(admin.StackedInline):
    model = models.BookingAccountSepa
    readonly_fields = ["first_used", "last_used"]
    extra = 0


@admin.register(models.BookingAccount)
class BookingAccountAdmin(ImportExportModelAdmin): 
    resource_class = BookingAccountResource

    search_fields = [
        "id", "customer__number", "payment_type", "address_name",
        "address_email", "address_city", "address_company", "easybill_sync_state",
    ]
    list_filter = ["easybill_sync_state", "tax_rate", "invoice_type"]
    inlines = [SepaAdmin]
    permission_group_required = ()
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    autocomplete_fields = ["customer"]

    actions = ["easybill_sync"]

    @admin.action(description=_("Push data to easybill"))
    def easybill_sync(self, request, queryset):
        for item in queryset:
            item.easybill_sync()


@admin.register(models.Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource

    list_display = ["number", "name"]
    search_fields = [
        "number",
        "name",
        "booking_accounts__id",
        "booking_accounts__address_name",
        "booking_accounts__address_company",
    ]
    readonly_fields = [
        "easybill_data",
        "crm_data",
        "crm_last_sync",
        "easybill_last_sync",
    ]
    list_filter = ["easybill_sync_state"]
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }

    @admin.action(description=_("Push data to easybill"))
    def easybill_sync(self, request, queryset):
        for item in queryset:
            item.easybill_sync()

    @admin.action(description=_("Pull CRM data"))
    def crm_sync(self, request, queryset):
        for item in queryset:
            item.crm_sync()


class InvoiceLineInlineAdmin(admin.StackedInline):
    model = models.InvoiceItem
    readonly_fields = ["price_total_net", "tax_rate"]
    autocomplete_fields = [
        "contract_item",
    ]
    formfield_overrides = {
        TextField: {"widget": Textarea(attrs={"rows": 3})},
    }
    readonly_fields = [
        "easybill_data",
        "easybill_last_sync",
        "easybill_sync_state",
        "easybill_id",
    ]
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        r = list(super().get_readonly_fields(request, obj))
        if obj and obj.invoice.number:
            r += [
                "contract_item",
                "name",
                "description",
                "amount",
                "price_single_net",
                "billing_start",
                "billing_end",
            ]
        return r


class InvoiceHasNumberFilter(admin.SimpleListFilter):
    title = _("Has invoice number")
    parameter_name = "has_number"

    def lookups(self, request, model_admin):
        return ((1, _("Yes")), (0, _("No")))

    def queryset(self, request, queryset):
        if self.value() in ("1", 1):
            isnull = False
        elif self.value() in ("0", 0):
            isnull = True
        else:
            return queryset
        return queryset.filter(number__isnull=isnull)


@admin.register(models.Invoice)
class InvoiceAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    permission_group_required = ()
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
        TextField: {"widget": Textarea(attrs={"rows": 3})},
    }
    inlines = [
        InvoiceLineInlineAdmin,
    ]
    line_model = models.InvoiceItem
    autocomplete_fields = [
        "booking_account",
    ]
    list_display = [
        "number",
        "booking_account",
        "date",
        "total_net",
        "total_gross",
        "canceled",
        "billing_start",
        "billing_end",
        "easybill_sync_state",
    ]
    list_filter = ["date", "easybill_sync_state", "approved", InvoiceHasNumberFilter]
    search_fields = [
        "number",
        "easybill_id",
        "booking_account__id",
        "booking_account__address_name",
        "booking_account__address_company",
        "booking_account__customer__number",
        "items__id",
        "items__name",
        "items__description",
        "items__contract_item__contract__number",
    ]
    list_editable = []
    autocomplete_fields = [
        "booking_account",
    ]
    readonly_fields = [
        "number",
        "total_net",
        "total_gross",
        "document_link",
        "easybill_data",
        "easybill_last_sync",
        "easybill_sync_state",
        "easybill_id",
    ]
    ordering = ("-number",)
    fieldsets = (
        (
            "Basics",
            {
                "fields": (
                    "number",
                    "approved",
                    "booking_account",
                    "date",
                    "billing_start",
                    "billing_end",
                    "canceled",
                    "easybill_sync_state",
                    "document_link",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "total_net",
                    "total_gross",
                    "sepa_transaction_type",
                )
            },
        ),
    )
    actions = [
        "easybill_sync",
        "approve",
    ]

    @admin.action(description=_("Push data to easybill"))
    def easybill_sync(self, request, queryset):
        for item in queryset:
            item.easybill_sync()

    @admin.action(description=_("Approve invoice"))
    def approve(self, request, queryset):
        queryset.update(approved=True)

    def document_link(self, obj):
        if obj.document_url:
            return mark_safe(
                '<a href="{}" target="_blank">{}</a>'.format(
                    obj.document_url, "Download invoice"
                )
            )
        return ""
