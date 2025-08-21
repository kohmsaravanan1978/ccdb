import datetime as dt
from collections import defaultdict
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from tqdm import tqdm

from contracting.models import BookingAccount, ContractItem, Invoice, InvoiceItem
from main.models import LogEntry, LogLevels


def get_next_interval(interval, timestamp=None):
    timestamp = timestamp or now().date()
    # We grab the beginning of the next month
    timestamp = timestamp.replace(day=1)
    timestamp += relativedelta(months=1)

    # If the interval is 1, we are always going to take the beginning of the next month.
    # Otherwise, we need to get the correct interval start, which is always at month % interval == 1
    if interval != 1:
        current_start = timestamp.month % interval
        if current_start != 1:
            timestamp += relativedelta(months=(interval - current_start) + 1)
    return timestamp


def get_invoice_end(interval, item, timestamp=None):
    timestamp = get_next_interval(interval, timestamp)
    end = item.valid_till or item.contract.valid_till
    if end and end < timestamp:
        return end
    return timestamp - dt.timedelta(days=1)


def get_month_amount(start, end):
    total_amount = 0

    if start.day != 1:
        start_day = start.day
        start = start.replace(day=1)
        start += relativedelta(months=1)
        month_days = (start - (start - relativedelta(months=1))).days
        total_amount += round((month_days - start_day) / Decimal(month_days), 2)

    if end.day != 1:
        end_day = end.day
        end = end.replace(day=1)
        month_days = ((end + relativedelta(months=1)) - end).days
        total_amount += round(end_day / Decimal(month_days), 2)

    delta = relativedelta(end, start)
    total_amount += delta.months + 12 * delta.years
    return total_amount


def run_invoicing(_timestamp=None, dry_run=False, console_output=False):
    """_timestamp will only be used with dry_run=True!"""
    # Step 1: find all contract items that are due a new invoice
    timestamp = _timestamp if (_timestamp and dry_run) else now().date()
    if not dry_run:
        LogEntry.objects.create(
            log_level=LogLevels.DEBUG,
            origin="contracting.run_invoicing",
            text="Start des täglichen Rechnungslaufs",
        )

    is_valid = Q(valid_till__gte=timestamp) | Q(
        Q(valid_till__isnull=True)
        & Q(
            Q(contract__valid_till__gte=timestamp)
            | Q(contract__valid_till__isnull=True)
        )
    )
    contract_items = (
        ContractItem.objects.filter(
            Q(ready_for_service__isnull=False)
            | Q(contract__ready_for_service__isnull=False),
            Q(invoice_items__isnull=True) | Q(price_recurring__isnull=False),
            is_valid,
            next_invoice__lte=timestamp,
            paused=False,
            archived=False,
        )
        .distinct()
        .select_related("contract__booking_account", "contract")
    )

    # Step 2: validate items and sort into groups
    item_groups = defaultdict(list)

    for item in tqdm(contract_items, "Sorting"):
        billing_start = item.last_invoice_override
        if not billing_start:
            last_invoice = item.invoice_items.all().order_by("-invoice__date").first()
            billing_start = (
                (last_invoice.invoice.billing_end + dt.timedelta(days=1))
                if last_invoice
                else item.valid_from or item.contract.valid_from
            )

        billing_end = get_invoice_end(
            interval=item.accounting_period, item=item, timestamp=timestamp
        )
        item_groups[
            (
                item.contract.booking_account_id,
                billing_start,
                billing_end,
                item.contract.collective_invoice or item.contract.number,
            )
        ].append(item.pk)

    invoice_count = 0
    position_count = 0
    email_deliveries = 0
    post_deliveries = 0
    sepa_invoices = 0
    for key, items in tqdm(item_groups.items(), "Invoicing"):
        # TODO put this in a separate celery task
        account = key[0]
        i, p = create_new_invoice(
            items,
            billing_start=key[1],
            billing_end=key[2],
            account=account,
            _timestamp=timestamp,
            commit=not dry_run,
        )
        invoice_count += i
        position_count += p
        account = BookingAccount.objects.get(id=account)
        if account.invoice_delivery_email:
            email_deliveries += 1
        if account.invoice_delivery_post:
            post_deliveries += 1
        if account.payment_type == account.Types.SEPA:
            sepa_invoices += 1
    if dry_run:
        print(
            f"Would have created {invoice_count} invoices with {position_count} positions."
        )
        print(
            f"{email_deliveries} emails to be sent, {post_deliveries} letters to be sent, {sepa_invoices} SEPA payments to be created."
        )
    else:
        LogEntry.objects.create(
            log_level=LogLevels.INFO,
            origin="contracting.run_invoicing",
            text=f"Rechnungslauf abgeschlossen, {invoice_count} Rechnungen mit {position_count} Positionen erstellt.",
        )


@transaction.atomic()
def create_new_invoice(
    item_pks, billing_start, billing_end, account, _timestamp=None, commit=True
):
    timestamp = _timestamp or now().date()
    account = BookingAccount.objects.get(pk=account)
    items = ContractItem.objects.filter(pk__in=item_pks)
    next_invoice = billing_end + dt.timedelta(days=1)

    if commit:
        for item in items:
            end = item.valid_till or item.contract.valid_till
            if end and end < timestamp:
                item.next_invoice = None
            else:
                item.next_invoice = next_invoice
            item.last_invoice_override = None
            item.save()

    invoice_lines = []
    for item in items:
        if item.price_setup and not item.invoice_items.all().count():
            invoice_lines.append(
                {
                    "contract_item": item,
                    "name": f"{item.product_name} – Einrichtungsgebühr",
                    "description": item.product_description,
                    "amount": 1,
                    "price_single_net": item.price_setup,
                    "price_total_net": item.price_setup,
                    "is_recurring": False,
                }
            )
        if item.price_recurring is not None:
            amount = get_month_amount(billing_start, billing_end + dt.timedelta(days=1))
            invoice_lines.append(
                {
                    "contract_item": item,
                    "name": item.product_name,
                    "description": item.product_description,
                    "amount": amount,
                    "price_single_net": item.price_recurring,
                    "price_total_net": round(item.price_recurring * amount, 2),
                }
            )

    total_net = sum(line["price_total_net"] for line in invoice_lines)

    if not total_net or total_net < 0:
        return 0, 0

    invoice_args = {
        "booking_account": account,
        "date": timestamp,
        "total_net": total_net,
        "total_gross": round(
            total_net * ((100 + account.tax_rate) / Decimal("100")), 2
        ),
        "billing_start": billing_start,
        "billing_end": billing_end,
        "approved": True,
        # TODO sepa handling
        # "sepa_transaction_type": Invoice.SepaTypes.FIRST if not account.first_sepa_payment else Invoice.SepaTypes.RCUR,
    }
    if commit:
        invoice = Invoice.objects.create(**invoice_args)
    else:
        invoice = None
        # if any(line["amount"] != 1 for line in invoice_lines):
        #     print("\n")
        #     print(f"New invoice for account {account}")
        #     print(f"    for customer {account.customer.number}")
        #     print(f"    from {billing_start} until {next_invoice}")
        #     print(f"    for {len(item_pks)} positions")
        #     print(f"    date {timestamp.isoformat()}")
        #     print(f"    start {billing_start.isoformat()}")
        #     print(f"    end {invoice_args['billing_end'].isoformat()}")
        #     print(f"    total net {invoice_args['total_net']}")
        #     print(f"    total gross {invoice_args['total_gross']}")

    invoice_item_constants = {
        "invoice": invoice,
        "tax_rate": account.tax_rate,
        "billing_start": invoice_args["billing_start"],
        "billing_end": invoice_args["billing_end"],
    }
    for order, line in enumerate(invoice_lines):
        if commit:
            InvoiceItem.objects.create(order=order, **line, **invoice_item_constants)
        # else:
        #     if any(line["amount"] != 1 for line in invoice_lines):
        #         print(
        #             f"     - invoice line {order +1}: {line['contract_item']} / {line['name']}, {line['amount']} x {line['price_single_net']} = {line['price_total_net']}"
        #         )
    return 1, len(invoice_lines)


def easybill_sync_invoices(queryset=None):
    if not queryset:
        queryset = Invoice.objects.filter(number__isnull=True)

    LogEntry.objects.create(
        log_level=LogLevels.DEBUG,
        origin="contracting.easybill_sync_invoices",
        text=f"{len(queryset)} Rechnungen werden zu EasyBill synchronisiert",
    )
    success = 0
    fails = 0
    for invoice in queryset:
        try:
            invoice.easybill_sync()
            success += 1
        except Exception:
            fails += 1

    LogEntry.objects.create(
        log_level=LogLevels.INFO,
        origin="contracting.easybill_sync_invoices",
        text=f"EasyBill-Sync abgeschlossen, {success} Rechnungen synchronisiert, {fails} Fehler.",
    )
