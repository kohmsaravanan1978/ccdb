import logging

from contracting.models import Contract
from contracting.utils import invoicing
from globalways.utils.celery import get_celery_app

logger = logging.getLogger(__name__)


app = get_celery_app()


@app.task
def task_update_contract_status():
    for contract in Contract.objects.all():
        new_status = contract.get_status()
        if new_status != contract.status:
            old_display = contract.get_status_display()
            contract.status = new_status
            new_display = contract.get_status_display()
            logger.info(
                "Update contract status of %s from %s to %s",
                contract.number,
                old_display,
                new_display,
            )
            try:
                contract.save()
            except Exception:
                logger.exception(
                    "Failed to update contract status for contract %s", contract.number
                )


@app.task
def run_invoicing():
    """Daily task creating new invoices"""
    invoicing.run_invoicing()


@app.task
def easybill_sync_invoices():
    """Daily task creating new invoices"""
    invoicing.easybill_sync_invoices()


@app.task
def create_test_log():
    """Testing that task running is working as intended."""
    from main.models import LogEntry

    LogEntry.objects.create(
        origin="contracting.create_test_log", text="Test log created with celery beat"
    )
