from django.core.exceptions import ValidationError
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.contract import ContractSerializer
from api.serializers.contract_item import ContractItemSerializer
from contracting.models import Contract, ContractItem


class TerminationDateSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)


class ContractFilterSet(filters.FilterSet):
    customer = filters.NumberFilter(field_name="booking_account__customer__number")
    paused = filters.BooleanFilter(field_name="items__paused")

    class Meta:
        model = Contract
        fields = ["booking_account", "customer", "paused"]


class ContractViewSet(viewsets.ModelViewSet):
    queryset = (
        Contract.objects.all()
        .prefetch_related("items", "items__successor", "items__predecessor")
        .select_related("booking_account", "booking_account__customer")
    )
    serializer_class = ContractSerializer
    lookup_field = "number"
    filterset_class = ContractFilterSet

    @swagger_auto_schema(request_body=TerminationDateSerializer, method="post")
    @action(detail=True, methods=["post"])
    def terminate(self, request, number=None):
        """Terminates a contract. You can pass {"date": "YYYY-MM-DD"} if you don't want to use the next possible termination date."""
        # TODO block pausing via normal serializer
        item = self.get_object()
        serializer = TerminationDateSerializer(data=request.data)
        if serializer.is_valid():
            date = serializer.validated_data.get("date")
        else:
            return Response(serializer.errors, status=400)
        try:
            item.cancel(date=date)
        except ValidationError as e:
            return Response({"error": e.error_dict}, status=400)
        return Response(self.serializer_class(item).data)

    @swagger_auto_schema(request_body=no_body, method="post")
    @action(detail=True, methods=["post"])
    def pause(self, number=None):
        # TODO block pausing via normal serializer
        item = self.get_object()
        item.pause()
        return Response(self.serializer_class(item).data)

    @swagger_auto_schema(request_body=no_body, method="post")
    @action(detail=True, methods=["post"])
    def unpause(self, number=None):
        # TODO block pausing via normal serializer
        item = self.get_object()
        item.unpause()
        return Response(self.serializer_class(item).data)


class ContractItemFilterSet(filters.FilterSet):
    customer = filters.NumberFilter(
        field_name="contract__booking_account__customer__number"
    )
    booking_account = filters.NumberFilter(field_name="contract__booking_account")
    contract = filters.NumberFilter(field_name="contract__number")

    class Meta:
        model = ContractItem
        fields = ["booking_account", "customer", "contract", "paused"]


class ContractItemViewSet(viewsets.ModelViewSet):
    queryset = ContractItem.objects.all().select_related("successor", "predecessor")
    serializer_class = ContractItemSerializer
    lookup_field = "number"
    filterset_class = ContractItemFilterSet

    @swagger_auto_schema(request_body=TerminationDateSerializer, method="post")
    @action(detail=True, methods=["post"])
    def terminate(self, request, number=None):
        """Terminates a contract. You can pass {"date": "YYYY-MM-DD"} if you don't want to use the next possible termination date."""
        item = self.get_object()
        serializer = TerminationDateSerializer(data=request.data)
        if serializer.is_valid():
            date = serializer.validated_data.get("date")
        else:
            return Response(serializer.errors, status=400)
        try:
            item.cancel(date=date)
        except ValidationError as e:
            return Response({"error": e.error_dict}, status=400)
        return Response(self.serializer_class(item).data)

    @swagger_auto_schema(request_body=no_body, method="post")
    @action(detail=True, methods=["post"])
    def pause(self, number=None):
        # TODO block pausing via normal serializer
        item = self.get_object()
        item.pause()
        return Response(self.serializer_class(item).data)

    @swagger_auto_schema(request_body=no_body, method="post")
    @action(detail=True, methods=["post"])
    def unpause(self, number=None):
        # TODO block pausing via normal serializer
        item = self.get_object()
        item.unpause()
        return Response(self.serializer_class(item).data)
