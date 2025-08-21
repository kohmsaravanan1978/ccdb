from rest_framework.decorators import action
from rest_framework.response import Response


class EasybillMixin:
    @action(detail=True, methods=["post"], url_path="easybill-sync")
    def easybill_sync(self):
        item = self.get_object()
        try:
            item.easybill_sync()
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        return Response(self.serializer_class(item).data)
