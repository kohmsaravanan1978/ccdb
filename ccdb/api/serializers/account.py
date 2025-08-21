from rest_framework import serializers

from contracting.models import BookingAccount, BookingAccountSepa, Customer


class BookingAccountSepaSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAccountSepa
        fields = [
            "confirmed",
            "revoked",
            "first_used",
            "last_used",
            "account_owner",
            "bank_name",
            "bic",
            "iban",
            "reference",
            "address_street",
            "address_zip_code",
            "address_city",
            "address_country",
        ]


class NestedBookingAccountSerializer(serializers.ModelSerializer):
    sepa = BookingAccountSepaSerializer(read_only=False, required=False)

    def create(self, validated_data):
        sepa_data = validated_data.pop("sepa", None)
        account = BookingAccount.objects.create(**validated_data)
        if sepa_data:
            sepa_data["account"] = account.id
            BookingAccountSepa.objects.create(account=account, **sepa_data)
        return account

    def update(self, instance, validated_data):
        sepa_data = validated_data.pop("sepa", None)
        instance = super().update(instance, validated_data)
        if sepa_data:
            sepa_data["account"] = instance.id
            if getattr(instance, "sepa", None):
                serializer = BookingAccountSepaSerializer(
                    instance=instance.sepa, data=sepa_data
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
            else:
                serializer = BookingAccountSepaSerializer(data=sepa_data)
                serializer.is_valid(raise_exception=True)
                BookingAccountSepa.objects.create(
                    account=instance, **serializer.validated_data
                )
        return instance

    class Meta:
        model = BookingAccount
        fields = [
            "id",
            "payment_type",
            "invoice_type",
            "invoice_delivery_email",
            "invoice_delivery_post",
            "payment_term",
            "tax_rate",
            "tax_option",
            "address_email",
            "address_name",
            "address_company",
            "address_street",
            "address_suffix",
            "address_city",
            "address_zip_code",
            "address_country",
            "comment",
            "xrechnung_buyer_reference",
            "easybill_id",
            "easybill_data",
            "easybill_last_sync",
            "sepa",
        ]


class BookingAccountSerializer(NestedBookingAccountSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all()) # Ensure customer is set
    sepa = BookingAccountSepaSerializer(read_only=False, required=False)

    class Meta:
        model = BookingAccount
        fields = NestedBookingAccountSerializer.Meta.fields + ["customer"]
