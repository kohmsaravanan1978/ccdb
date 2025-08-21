from rest_framework import serializers

from contracting.models import Contract, ContractItem


class ItemNumberSerializer(serializers.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_representation(self, obj):
        return getattr(obj, "number", None)

    def to_internal_value(self, data):
        return ContractItem.objects.get(number=data)


class ManyItemNumberSerializer(serializers.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_representation(self, obj):
        return [getattr(o, "number", None) for o in obj.all() if o] if obj.all() else []

    def to_internal_value(self, data):
        return ContractItem.objects.filter(number__in=data)


class ContractItemInlineSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField(allow_null=True)
    successor = ItemNumberSerializer(required=False, allow_null=True)
    predecessor = ItemNumberSerializer(required=False, allow_null=True)
    parent_item = ItemNumberSerializer(required=False, allow_null=True)
    child_items = ManyItemNumberSerializer(required=False, allow_null=True)
    number = serializers.IntegerField(required=False)


    def get_status(self, obj):
        return obj.status

    def validate(self, data):
        valid_from = data.get("valid_from")
        ready_for_service = data.get("ready_for_service")
        if self.partial:
            instance = getattr(self, "instance", None)
            if "valid_from" not in data:
                valid_from = getattr(instance, "valid_from", None)
            if "ready_for_service" not in data:
                ready_for_service = getattr(instance, "ready_for_service", None)

        if not valid_from and ready_for_service:
            raise serializers.ValidationError(
                "Cannot have empty valid_from when ready_for_service is set!"
            )
        return data

    def create(self, validated_data):
        children = validated_data.pop("child_items", None)
        validated_data["contract"] = validated_data.get("contract") or self.context.get(
            "contract"
        )
        item = super().create(validated_data)
        if children is not None:
            item.child_items.set(children)
        return item

    def update(self, instance, validated_data):
        children = validated_data.pop("child_items", None)
        validated_data["contract"] = validated_data.get("contract") or self.context.get(
            "contract"
        )
        item = super().update(instance, validated_data)
        if children is not None:
            item.child_items.set(children)
        return item

    class Meta:
        model = ContractItem
        fields = [
            "id",
            "number",
            "status",
            "predecessor",
            "successor",
            "parent_item",
            "child_items",
            "product_code",
            "product_name",
            "product_description",
            "valid_from",
            "valid_till",
            "termination_date",
            "minimum_duration",
            "notice_period",
            "order_reference",
            "netbox_reference",
            "realization_site",
            "realization_location",
            "realization_rack",
            "realization_he",
            "availability_guaranteed",
            "availability_hours",
            "fibu_account",
            "price_recurring",
            "price_setup",
            "accounting_period",
            "billing_type",
            "paused",
            "ready_for_service",
            "realization_variant",
            "billing_data",
            "imported_data",
            "attributes",
            "next_invoice",
        ]


class ContractItemSerializer(ContractItemInlineSerializer):
    contract = serializers.PrimaryKeyRelatedField(queryset=Contract.objects.all()) # Ensure contract is set

    class Meta(ContractItemInlineSerializer.Meta):
        fields = ContractItemInlineSerializer.Meta.fields + ["contract"]
