from rest_framework import serializers

from api.serializers.account import (
    BookingAccountSerializer,
    NestedBookingAccountSerializer,
)
from contracting.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    booking_accounts = NestedBookingAccountSerializer(many=True)

    def create(self, validated_data):
        booking_accounts = validated_data.pop("booking_accounts", [])
        customer = Customer.objects.create(**validated_data)

        for account_data in booking_accounts:
            account_data["customer"] = customer.number
            serializer = BookingAccountSerializer(data=account_data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return customer

    def update(self, instance, validated_data):
        booking_accounts = validated_data.pop("booking_accounts", [])
        customer = super().update(instance, validated_data)

        if booking_accounts:
            own_accounts = {acc.id: acc for acc in customer.booking_accounts.all()}

            for account in booking_accounts:
                if not account or not any(account.values()):
                   continue  # skip empty dicts like [{}]
                account["customer"] = customer.number  

                account_id = account.get("id")
                if account_id:
                    try:
                        account_id = int(account_id)
                    except ValueError:
                        raise Exception(f"Invalid ID format: {account_id}")

                    existing_account = own_accounts.get(account_id)
                    if not existing_account:
                        raise Exception(f"Unknown BookingAccount with ID {account_id}")

                    print(f"Updating BookingAccount ID: {account_id}")
                    account_serializer = BookingAccountSerializer(
                        instance=existing_account, data=account
                    )
                else:
                    print("Creating new BookingAccount")
                    account_serializer = BookingAccountSerializer(data=account)


                account_serializer.is_valid(raise_exception=True)
                account_serializer.save()

        return customer


    class Meta:
        model = Customer
        fields = [
            "name",
            "booking_accounts",
            "number",
            "crm_data",
            "crm_last_sync",
            "easybill_id",
            "easybill_data",
            "easybill_last_sync",
        ]

