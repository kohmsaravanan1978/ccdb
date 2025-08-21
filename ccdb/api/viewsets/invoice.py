from django_filters import rest_framework as filters
from rest_framework import viewsets

from api.serializers.invoice import InvoiceItemSerializer, InvoiceSerializer
from api.viewsets.mixins import EasybillMixin
from contracting.models import Invoice, InvoiceItem


class InvoiceFilterSet(filters.FilterSet):
    customer = filters.NumberFilter(field_name="booking_account__customer__number")
    contract = filters.NumberFilter(field_name="items__contract_item__contract__number")

    class Meta:
        model = Invoice
        fields = ("booking_account", "customer", "contract", "approved", "number")


class InvoiceViewSet(EasybillMixin, viewsets.ModelViewSet):
    queryset = (
        Invoice.objects.all()
        .select_related("booking_account")
        .select_related("booking_account__customer")
        .prefetch_related("items")
    )
    serializer_class = InvoiceSerializer
    filterset_class = InvoiceFilterSet


class InvoiceItemFilterSet(filters.FilterSet):
    customer = filters.NumberFilter(
        field_name="invoice__booking_account__customer__number"
    )
    booking_account = filters.NumberFilter(field_name="invoice__booking_account")
    invoice = filters.NumberFilter(field_name="invoice__number")
    invoice_id = filters.NumberFilter(field_name="invoice_id")
    contract = filters.NumberFilter(field_name="contract_item__contract__number")

    class Meta:
        model = InvoiceItem
        fields = [
            "booking_account",
            "customer",
            "invoice",
            "invoice_id",
            "contract",
            "contract_item",
        ]


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.all().select_related("invoice")
    serializer_class = InvoiceItemSerializer
    lookup_field = "number"
    filterset_class = InvoiceItemFilterSet
