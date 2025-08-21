import pytest

from contracting.models import BookingAccountSepa


@pytest.mark.django_db
def test_customer_api_get(account, sepa, admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200

    response = admin_client.get("/api/v1/customers/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    customer = data["results"][0]
    account_data = customer.pop("booking_accounts")[0]
    assert customer == {
        "name": "Test Customer",
        "number": 10001,
        "crm_data": {"synced_data": {}},
        "crm_last_sync": None,
        "easybill_id": None,
        "easybill_data": {"last_state": "unsynced", "synced_data": {}},
        "easybill_last_sync": None,
    }
    account_data.pop("id")
    assert account_data == {
        "payment_type": "INVOICE",
        "invoice_type": "zugferd2_2",
        "invoice_delivery_email": False,
        "invoice_delivery_post": False,
        "payment_term": 14,
        "tax_rate": 19.0,
        "tax_option": "NULL",
        "address_email": None,
        "address_name": "Test Account",
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
        "sepa": {
            "confirmed": None,
            "revoked": None,
            "first_used": None,
            "last_used": None,
            "account_owner": "Sepa Owner",
            "bank_name": "Sepa bank name",
            "bic": "BELADEBEXXX",
            "iban": "DE02120300000000202051",
            "reference": "customer reference",
            "address_street": "Test street",
            "address_zip_code": "test zip code",
            "address_city": "Berlin",
            "address_country": "DE",
        },
    }


@pytest.mark.django_db
def test_account_api_get(account, sepa, admin_client):
    response = admin_client.get(
        "/api/v1/booking-accounts/", HTTP_ACCEPT="application/json"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    account_data = data["results"][0]
    account_data.pop("id")
    assert account_data == {
        "customer": 10001,
        "payment_type": "INVOICE",
        "invoice_type": "zugferd2_2",
        "invoice_delivery_email": False,
        "invoice_delivery_post": False,
        "payment_term": 14,
        "tax_rate": 19.0,
        "tax_option": "NULL",
        "address_email": None,
        "address_name": "Test Account",
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
        "sepa": {
            "confirmed": None,
            "revoked": None,
            "first_used": None,
            "last_used": None,
            "account_owner": "Sepa Owner",
            "bank_name": "Sepa bank name",
            "bic": "BELADEBEXXX",
            "iban": "DE02120300000000202051",
            "reference": "customer reference",
            "address_street": "Test street",
            "address_zip_code": "test zip code",
            "address_city": "Berlin",
            "address_country": "DE",
        },
    }


@pytest.mark.django_db
def test_account_api_update_create_sepa(account, admin_client):
    assert BookingAccountSepa.objects.all().count() == 0
    response = admin_client.get(
        "/api/v1/booking-accounts/", HTTP_ACCEPT="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    account_data = data["results"][0]
    assert not account_data["sepa"]

    account_data["address_name"] = "New Address Name"
    account_data["sepa"] = {
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
        f"/api/v1/booking-accounts/{account.id}/",
        account_data,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )
    assert response.status_code == 200
    account_data = response.json()
    account.refresh_from_db()

    assert account_data["address_name"] == "New Address Name"
    assert account.address_name == "New Address Name"
    assert BookingAccountSepa.objects.all().count() == 1
    sepa = BookingAccountSepa.objects.all().first()
    assert sepa.account == account
    assert sepa.account_owner == "Sepa Owner"


@pytest.mark.django_db
def test_account_api_update_sepa(account, sepa, admin_client):
    response = admin_client.get(
        "/api/v1/booking-accounts/", HTTP_ACCEPT="application/json"
    )
    assert response.status_code == 200

    data = response.json()
    account_data = data["results"][0]
    account_data["sepa"]["account_owner"] = "New Sepa Owner"

    response = admin_client.patch(
        f"/api/v1/booking-accounts/{account.id}/",
        account_data,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )
    assert response.status_code == 200
    account_data = response.json()
    sepa.refresh_from_db()

    assert account_data["sepa"]["account_owner"] == "New Sepa Owner"
    assert sepa.account_owner == "New Sepa Owner"


# TODO
# def test_account_api_create_account
# def test_account_api_update_account
# def test_account_api_delete_account
