from rest_framework import serializers

from api.serializers.account import BookingAccountSerializer
from contracting.models import Invoice, InvoiceItem


class InvoiceItemInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "order",
            "contract_item",
            "name",
            "description",
            "amount",
            "price_single_net",
            "price_total_net",
            "tax_rate",
            "billing_start",
            "billing_end",
            "easybill_id",
            "easybill_data",
            "easybill_last_sync",
        ]


class InvoiceItemSerializer(InvoiceItemInlineSerializer):
    class Meta(InvoiceItemInlineSerializer.Meta):
        fields = InvoiceItemInlineSerializer.Meta.fields + ["invoice"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemInlineSerializer(many=True)
    booking_account = BookingAccountSerializer()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "document_url",
            "booking_account",
            "items",
            "total_net",
            "total_gross",
            "canceled",
            "date",
            "billing_data",
            "billing_start",
            "billing_end",
            "approved",
            "document",
            "sepa_transaction_type",
            "easybill_id",
            "easybill_data",
            "easybill_last_sync",
        ]
