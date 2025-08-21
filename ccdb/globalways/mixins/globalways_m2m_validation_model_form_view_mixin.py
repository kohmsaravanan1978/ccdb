from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

__all__ = ["GlobalwaysM2MValidationModelFormViewMixin"]


class GlobalwaysM2MValidationModelFormViewMixin:
    def form_valid(self, form):
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, e.message if hasattr(e, "message") else e)
            return self.form_invalid(form)
