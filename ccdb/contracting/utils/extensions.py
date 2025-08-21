from django.utils.timezone import now

from contracting.models import Contract, ContractItem


def run_extensions(dry_run=False):
    # We need to run on items and contracts separately
    contracts = Contract.objects.filter(
        valid_till__gt=now(), automatic_extension__gt=0, termination_date__isnull=True
    )
    items = ContractItem.objects.filter(
        valid_till__gt=now(),
        contract__automatic_extension__gt=0,
        termination_date__isnull=True,
    ).select_related("contract")

    for contract in contracts:
        if contract.next_possible_contract_end > contract.valid_till:
            new_valid_till = contract.next_possible_contract_end
            if dry_run:
                print(
                    f"Would extend contract {contract.number} by {contract.automatic_extension} months from {contract.valid_till.isoformat()} to {new_valid_till.isoformat()}"
                )
            else:
                contract.valid_till = new_valid_till
                contract.save()

    for item in items:
        contract = item.contract
        if contract.next_possible_contract_end > item.valid_till:
            new_valid_till = contract.next_possible_contract_end
            if dry_run:
                print(
                    f"Would extend contract item {item.number} of contract {contract.number} by {contract.automatic_extension} months from {item.valid_till.isoformat()} to {new_valid_till.isoformat()}"
                )
            else:
                item.valid_till = new_valid_till
                item.save()
