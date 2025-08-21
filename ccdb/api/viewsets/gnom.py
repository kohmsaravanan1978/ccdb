from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from contracting.models import Contract


@api_view()
@permission_classes([AllowAny])
def contract_view(request):
    """Response structure is a plain, unpaginated list with one entry per contract of the form:

    {
        "customer_number": 123,
        "customer_name": "test",
        "contract_number": 123,
        "product": "CCDB import",
        "start_date": "2020-01-01",
        "end_date": "2032-01-01":
        "ready_for_service": True/False,
    }
    """

    return Response(
        [
            {
                "customer_number": contract.booking_account.customer.number,
                "customer_name": contract.booking_account.customer.name
                or contract.booking_account.address_company,
                "contract_id": contract.number,
                "product": contract.name,
                "start_date": (
                    contract.valid_from.isoformat() if contract.valid_from else None
                ),
                "end_date": (
                    contract.valid_till.isoformat() if contract.valid_till else None
                ),
                "ready_for_service": any(
                    item.ready_for_service for item in contract.items.all()
                ),
            }
            for contract in Contract.objects.all().select_related(
                "booking_account", "booking_account__customer"
            )
        ]
    )
