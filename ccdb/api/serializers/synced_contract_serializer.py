from rest_framework import serializers

from contracting.models import Contract


class SyncedContractSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField("get_client_name")
    status = serializers.SerializerMethodField("get_serialized_status", allow_null=True)

    def get_client_name(self, obj):
        return obj.client.name

    def get_serialized_status(self, obj):
        return {
            Contract.STATUS_NOT_STARTED: "not_started",
            Contract.STATUS_ACTIVE: "active",
            Contract.STATUS_TERMINATED: "terminated",
            Contract.STATUS_ENDED: "ended",
            Contract.STATUS_IN_REALISATION: "in_realisation",
            Contract.STATUS_ACCOUNTING_DEACTIVATED: "accounting_deactivated",
            Contract.STATUS_UNDEFINED: "undefined",
        }.get(obj.status)

    class Meta:
        model = Contract
        fields = [
            "name",
            "customer__number",
            "contract__number",
            "client",
            "valid_from",
            "valid_till",
            "status",
        ]
