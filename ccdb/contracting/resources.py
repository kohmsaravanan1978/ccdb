import json
from import_export import resources
from import_export.results import RowResult
from api.serializers.customer import CustomerSerializer
from api.serializers.contract import ContractSerializer
from contracting.models import Customer
from contracting.models import Contract, ContractItem
from api.serializers.account import BookingAccountSerializer
from contracting.models import BookingAccount
from import_export import fields
import logging
logger = logging.getLogger(__name__)


class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        import_id_fields = ("number",)
        fields = [
            "name",
            "number",
            "crm_data",
            "crm_last_sync",
            # Note: booking_accounts is handled manually
        ]

    def get_instance(self, instance_loader, row):
        number = row.get("number")
        return Customer.objects.filter(number=number).first() if number else None

    def import_row(self, row, instance_loader, **kwargs):
        return super().import_row(row, instance_loader, **kwargs)

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        dry_run = kwargs.get("dry_run", False)
        instance = self.get_instance(None, row)

        data = dict(row)

        def safe_json_parse(field, fallback):
            value = data.get(field)
            if isinstance(value, (dict, list)):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError as e:
                    logger.warning(f"[Row {row_number}] Invalid JSON in '{field}': {e}")
            return fallback

        data["crm_data"] = safe_json_parse("crm_data", {})

        booking_accounts_data = safe_json_parse("booking_accounts", [])
        data.pop("booking_accounts", None)

        if not booking_accounts_data or booking_accounts_data == [{}]:
            skip_booking_accounts = True
        else:
            skip_booking_accounts = False

        # Save customer
        serializer = CustomerSerializer(instance=instance, data=data, partial=True)

        if serializer.is_valid():
            if not dry_run:
                saved_customer = serializer.save()
                logger.info(f"{'Updated' if instance else 'Created'} customer: {saved_customer.number}")

                if not skip_booking_accounts:
                    for account_data in booking_accounts_data:
                        account_data["customer"] = saved_customer.id

                        # Normalize fields
                        if "tax_rate" in account_data and account_data["tax_rate"]:
                            try:
                                account_data["tax_rate"] = float(account_data["tax_rate"])
                            except ValueError:
                                account_data["tax_rate"] = None

                        for key in ["invoice_delivery_email", "invoice_delivery_post"]:
                            val = str(account_data.get(key, "")).strip().lower()
                            account_data[key] = val in ("true", "1", "yes")

                        # Create BookingAccount
                        booking_serializer = BookingAccountSerializer(data=account_data)
                        if booking_serializer.is_valid():
                            booking = booking_serializer.save()
                            logger.info(f"BookingAccount created: {booking.id}")
                        else:
                            logger.warning(f"BookingAccount error: {booking_serializer.errors}")
        else:
            row_result.errors.append(serializer.errors)
            logger.error(f"Row {row_number} validation error: {serializer.errors}")

        return row_result


class BookingAccountResource(resources.ModelResource):
    customer = fields.Field(attribute="customer", column_name="customer")
    class Meta:
        model = BookingAccount
        import_id_fields = ("id",)
        fields = [
            "id",
            "customer", 
            "address_company",
            "address_email",
            "address_city",
            "address_zip_code",
            "address_country",
            "invoice_type",
            "invoice_delivery_email",
            "invoice_delivery_post",
            "payment_type",
            "tax_rate",
            "payment_term",
            "comment",
        ]
    def dehydrate_customer(self, obj):
        return obj.customer.number if obj.customer else ""        

    def str_to_bool(self, value):
        return str(value).strip().lower() in ["true", "1", "yes"]

    def import_row(self, row, instance_loader, **kwargs):
        data = dict(row)
        row_result = RowResult()
        row_number = kwargs.get("row_number", "?")

        print(f"\n📥 ROW {row_number} | id={data.get('id')} | customer={data.get('customer')}")
        print(json.dumps(data, indent=2))
        raw_id = str(data.get("id", "")).strip()
        data["id"] = raw_id if raw_id else None

        # Resolve customer number to actual instance
        customer_number_raw = data.get("customer")
        customer_number = str(customer_number_raw).strip()

        try:
            customer = Customer.objects.get(number=customer_number)
        except Customer.DoesNotExist:
            msg = f"Customer with number={customer_number} does not exist (row {row_number})"
            print(msg)
            row_result.errors.append(("customer", msg))
            row_result.import_type = RowResult.IMPORT_TYPE_SKIP
            return row_result

        data["customer"] = customer.id # Use customer ID for the serializer

        # Convert booleans
        for key in ["invoice_delivery_email", "invoice_delivery_post"]:
            data[key] = self.str_to_bool(data.get(key, False))

        # Convert tax_rate
        if "tax_rate" in data and data["tax_rate"]:
            try:
                data["tax_rate"] = float(data["tax_rate"])
            except ValueError:
                data["tax_rate"] = None

        # Load instance for update if available
        instance = instance_loader.get_instance(row)
        serializer = BookingAccountSerializer(instance=instance, data=data)

        if serializer.is_valid():
            export_fields = self.get_export_fields()
            row_result.diff = []

            for field in export_fields:
                field_name = field.column_name

                # Get the value from the CSV/input
                if field_name == "customer":
                    try:
                        customer_id = int(data["customer"])
                        csv_val = Customer.objects.get(id=customer_id).number
                    except Exception:
                        csv_val = ""
                else:
                    csv_val = data.get(field_name, "")

                row_result.diff.append(str(csv_val))

            if kwargs.get("dry_run"):
                print("Dry run: validated but not saved.")
                row_result.import_type = (
                    RowResult.IMPORT_TYPE_UPDATE if instance else RowResult.IMPORT_TYPE_NEW
                )
                row_result.object_repr = "[Preview] BookingAccount"
            else:
                saved_instance = serializer.save()
                print(f"Saved BookingAccount with ID: {saved_instance.id}")
                row_result.import_type = (
                    RowResult.IMPORT_TYPE_UPDATE if instance else RowResult.IMPORT_TYPE_NEW
                )
                row_result.object_repr = str(saved_instance)


        return row_result

            
class ContractResource(resources.ModelResource):
    class Meta:
        model = Contract
        import_id_fields = ("number",)
        fields = [
            "name",
            "number",
            "booking_account",
            "order_date",
            "termination_date",
            "valid_from",
            "valid_till",
            "minimum_duration",
            "notice_period",
            "automatic_extension",
            "collective_invoice",
            "order_reference",
            "jira_offer_reference",
            "jira_ticket",
            "ready_for_service",
            "special_conditions",
            "comment",
            "billing_data",
            "imported_data",
            "items",
        ]

    
    def export(self, queryset=None, *args, **kwargs):
        dataset = super().export(queryset, *args, **kwargs)

        # Add a new column header for items
        dataset.headers.append("items")

        for i, row in enumerate(queryset):
            items = list(
                ContractItem.objects.filter(contract=row)
                .values("number", "product_name")
            )
            dataset.append_col([json.dumps(items, default=str)], header="items")

        return dataset


    def import_row(self, row, instance_loader, **kwargs):
        data = dict(row)
        row_result = RowResult()
        row_number = kwargs.get("row_number", "?")

        # Parse JSON strings
        for field in ["billing_data", "imported_data", "items"]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError as e:
                    row_result.errors.append({field: f"Invalid JSON - {str(e)}"})
                    return row_result

        instance = instance_loader.get_instance(row)
        serializer = ContractSerializer(instance=instance, data=data)

        if serializer.is_valid():
            if kwargs.get("dry_run"):
                row_result.import_type = (
                    RowResult.IMPORT_TYPE_UPDATE if instance else RowResult.IMPORT_TYPE_NEW
                )
                row_result.object_repr = data.get("number", "Contract")
                row_result.diff = [str(data.get(field.column_name, "")) for field in self.get_export_fields()]
            else:
                saved = serializer.save()
                row_result.import_type = (
                    RowResult.IMPORT_TYPE_UPDATE if instance else RowResult.IMPORT_TYPE_NEW
                )
                row_result.object_repr = str(saved)
                row_result.diff = [str(data.get(field.column_name, "")) for field in self.get_export_fields()]
            return row_result
        else:
            row_result.errors.append(serializer.errors)
            return row_result

    def before_import_row(self, row, row_number=None, **kwargs):
        # If booking_account is not in row, inject from form
        if not row.get("booking_account"):
            booking_account = kwargs.get("booking_account")
            if booking_account:
                row["booking_account"] = booking_account.id            

