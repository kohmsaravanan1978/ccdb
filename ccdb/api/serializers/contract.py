from rest_framework import serializers

from api.serializers.contract_item import ContractItemInlineSerializer
from contracting.models import Contract, ContractItem

from django.core.exceptions import ObjectDoesNotExist


class ContractSerializer(serializers.ModelSerializer):
    items = ContractItemInlineSerializer(many=True)
    number = serializers.IntegerField(required=False)
    valid_till = serializers.DateField(required=False, allow_null=True)

    def to_internal_value(self, data):
        for date_field in ("valid_till", "termination_date"):
            if data.get(date_field) in ("", None):
                data[date_field] = None
        return super().to_internal_value(data)


    def create(self, validated_data):
        items = validated_data.pop("items", None) or []
        contract = super().create(validated_data)
        for item in items:
            item["contract"] = contract.pk
            serializer = ContractItemInlineSerializer(
                data=item, context={"contract": contract}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return contract


    def update(self, instance, validated_data):
        items = validated_data.pop("items", None) or []
        contract = super().update(instance, validated_data)

        for item in items:
            existing_item = None
            if item.get("number"):
                try:
                    existing_item = ContractItem.objects.get(
                        number=item["number"], contract=contract
                    )
                except ObjectDoesNotExist:
                    existing_item = None  # Treat as new

            # Always pass contract into item data for new or existing
            item["contract"] = contract.pk

            serializer = ContractItemInlineSerializer(
                instance=existing_item,
                data=item,
                context={"contract": contract}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return contract



    class Meta:
        model = Contract
        fields = [
            "name",
            "number",
            "booking_account",
            "order_date",
            "termination_date",
            "valid_from",
            "valid_till",
            "items",
            "minimum_duration",
            "notice_period",
            "automatic_extension",
            "collective_invoice",
            "order_reference",
            "jira_offer_reference",
            "jira_ticket",
            "ready_for_service",
            "special_conditions",
            "comment",
            "billing_data",
            "imported_data",
        ]
