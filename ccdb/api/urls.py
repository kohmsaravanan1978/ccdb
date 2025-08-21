from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from api.viewsets import gnom
from api.viewsets.contract import ContractItemViewSet, ContractViewSet
from api.viewsets.customer import BookingAccountViewSet, CustomerViewSet
from api.viewsets.invoice import InvoiceItemViewSet, InvoiceViewSet

app_name = "api"
router = routers.DefaultRouter()
router.register(r"contracts", ContractViewSet)
router.register(r"contract-items", ContractItemViewSet)
router.register(r"customers", CustomerViewSet)
router.register(r"booking-accounts", BookingAccountViewSet)
router.register(r"invoices", InvoiceViewSet)
router.register(r"invoice-items", InvoiceItemViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("gnom/contracts/", gnom.contract_view),
]

api_info = openapi.Info(
    title="CCDB API",
    default_version="v1",
)
schema_view = get_schema_view(
    api_info,
    public=True,
    permission_classes=[permissions.AllowAny],
    urlconf="ccdb.urls",
)
urlpatterns += [
    re_path(
        r"swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]
