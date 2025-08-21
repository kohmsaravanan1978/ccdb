from django_filters import rest_framework as filters
from rest_framework import viewsets

from api.serializers.account import BookingAccountSerializer
from api.serializers.customer import CustomerSerializer
from api.viewsets.mixins import EasybillMixin
from contracting.models import BookingAccount, Customer


class BookingAccountFilterSet(filters.FilterSet):
    customer = filters.NumberFilter(field_name="customer__number")

    class Meta:
        model = BookingAccount
        fields = ["customer"]


class BookingAccountViewSet(EasybillMixin, viewsets.ModelViewSet):
    queryset = BookingAccount.objects.all().select_related("customer", "sepa")
    serializer_class = BookingAccountSerializer
    filterset_class = BookingAccountFilterSet


class CustomerViewSet(EasybillMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all().prefetch_related(
        "booking_accounts", "booking_accounts__sepa"
    )
    serializer_class = CustomerSerializer
    lookup_field = "number"
