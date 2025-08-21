from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404

from contracting.models import Invoice


def download_invoice(request, number):
    """Download an invoice as a PDF file."""
    if not request.user.is_authenticated:
        return HttpResponse(status=403)
    if not request.user.is_staff:
        return HttpResponse(status=403)
    invoice = get_object_or_404(Invoice, number=number)
    if not invoice.document:
        return HttpResponse(status=404)
    return FileResponse(
        invoice.document, as_attachment=True, filename=f"{invoice.number}.pdf"
    )
