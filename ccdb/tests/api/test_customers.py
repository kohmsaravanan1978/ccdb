import pytest

from contracting.models import BookingAccountSepa, Customer


@pytest.mark.django_db
def test_customer_create(admin_client):
    assert Customer.objects.all().count() == 0
    data = {
        "name": "New Test Customer",
        "number": 10023,
        "booking_accounts": [
            {
                "customer": 10023,
                "address_name": "New Test Account",
            }
        ],
    }
    response = admin_client.post(
        "/api/v1/customers/",
        data,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )
    assert response.status_code == 201, response.content.decode()
    assert Customer.objects.all().count() == 1
    customer = Customer.objects.all().first()
    assert customer.name == "New Test Customer"
    data = response.json()
    data["booking_accounts"][0].pop("id")
    assert data == {
        "name": "New Test Customer",
        "number": 10023,
        "crm_data": {"synced_data": {}},
        "crm_last_sync": None,
        "easybill_id": None,
        "easybill_data": {"synced_data": {}, "last_state": "unsynced"},
        "easybill_last_sync": None,
        "booking_accounts": [
            {
                "payment_type": "INVOICE",
                "invoice_type": "zugferd2_2",
                "invoice_delivery_email": False,
                "invoice_delivery_post": False,
                "payment_term": 14,
                "tax_rate": 19.0,
                "tax_option": "NULL",
                "address_email": None,
                "address_name": "New Test Account",
                "address_company": None,
                "address_street": None,
                "address_suffix": None,
                "address_city": None,
                "address_zip_code": None,
                "address_country": None,
                "comment": None,
                "xrechnung_buyer_reference": None,
                "easybill_id": None,
                "easybill_data": {"last_state": "unsynced", "synced_data": {}},
                "easybill_last_sync": None,
                "sepa": None,
            }
        ],
    }


@pytest.mark.django_db
def test_customer_api_update_create_sepa(account, admin_client):
    response = admin_client.get("/api/v1/customers/", HTTP_ACCEPT="application/json")
    data = response.json()
    customer = data["results"][0]
    assert not customer["booking_accounts"][0]["sepa"]
    assert BookingAccountSepa.objects.all().count() == 0
    customer["name"] = "New Test Customer"
    customer["booking_accounts"][0]["address_name"] = "New Address Name"
    customer["booking_accounts"][0]["sepa"] = {
        "account_owner": "Sepa Owner",
        "bank_name": "Sepa bank name",
        "bic": "BELADEBEXXX",
        "iban": "DE02120300000000202051",
        "reference": "customer reference",
        "address_street": "Test street",
        "address_zip_code": "test zip code",
        "address_city": "Berlin",
    }

    response = admin_client.patch(
        f"/api/v1/customers/{customer['number']}/",
        customer,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )
    assert response.status_code == 200, response.content.decode()
    data = response.json()
    account.customer.refresh_from_db()
    account.refresh_from_db()

    assert data["name"] == "New Test Customer"
    assert account.customer.name == "New Test Customer"
    assert data["booking_accounts"][0]["address_name"] == "New Address Name"
    assert account.address_name == "New Address Name"
    assert BookingAccountSepa.objects.all().count() == 1
    sepa = BookingAccountSepa.objects.all().first()
    assert sepa.account == account
    assert sepa.account_owner == "Sepa Owner"


@pytest.mark.django_db
def test_customer_api_update_sepa(account, sepa, admin_client):
    # Test that double nested updates work
    response = admin_client.get("/api/v1/customers/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    customer = data["results"][0]
    account = customer["booking_accounts"][0]
    assert account["sepa"]

    account["sepa"]["account_owner"] = "New Sepa Owner"
    response = admin_client.patch(
        f"/api/v1/customers/{customer['number']}/",
        customer,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    sepa.refresh_from_db()
    assert account["sepa"]["account_owner"] == "New Sepa Owner"
    assert sepa.account_owner == "New Sepa Owner"


# def test_account_api_create_customer_with_account
# def test_account_api_update_cutomer_create_account
# def test_account_api_update_cutomer_update_account
# from dirty_equals.pytest_plugin import insert_assert
