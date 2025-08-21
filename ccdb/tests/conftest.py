import pytest

from contracting.models import (
    BookingAccount,
    BookingAccountSepa,
    Contract,
    ContractItem,
    Customer,
)


@pytest.fixture
def customer():
    return Customer.objects.create(
        name="Test Customer",
        number=10001,
    )


@pytest.fixture
def account(customer):
    return BookingAccount.objects.create(customer=customer, address_name="Test Account")


@pytest.fixture
def sepa(account):
    return BookingAccountSepa.objects.create(
        account=account,
        account_owner="Sepa Owner",
        bank_name="Sepa bank name",
        bic="BELADEBEXXX",
        iban="DE02120300000000202051",
        reference="customer reference",
        address_street="Test street",
        address_zip_code="test zip code",
        address_city="Berlin",
    )


@pytest.fixture
def contract(account):
    contract = Contract.objects.create(
        name="Test-Vertrag",
        booking_account=account,
        valid_from="2022-09-07",
    )
    ContractItem.objects.create(
        contract=contract,
        product_code="test product setup",
        product_name="Test-Produkt-Setup",
        price_setup=100,
        accounting_period=1,
    )
    ContractItem.objects.create(
        contract=contract,
        product_code="test product",
        product_name="Test-Produkt",
        price_recurring=200,
        accounting_period=1,
    )
    return contract
