import datetime as dt

import pytest

from contracting.models import Contract, ContractItem


@pytest.mark.django_db
def test_contract_list(contract, admin_client):
    response = admin_client.get("/api/v1/contracts/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    contract_data = data["results"][0]

    assert contract_data["booking_account"]
    assert len(contract_data["items"]) == 2


@pytest.mark.django_db
def test_contract_list_and_create(contract, admin_client):
    response = admin_client.get("/api/v1/contracts/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    contract_data = data["results"][0]
    assert Contract.objects.count() == 1
    assert ContractItem.objects.count() == 2

    # Try to create the same contract again
    old_number = contract_data.pop("number")
    contract_data["items"][0].pop("number")
    contract_data["items"][1].pop("number")

    response = admin_client.post(
        "/api/v1/contracts/",
        contract_data,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["number"] == old_number + 1
    assert Contract.objects.count() == 2
    assert ContractItem.objects.count() == 4


@pytest.mark.django_db
def test_contract_list_and_update(contract, admin_client):
    response = admin_client.get("/api/v1/contracts/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    contract_data = data["results"][0]
    assert Contract.objects.count() == 1
    assert ContractItem.objects.count() == 2

    # Change only the contract's name and one item's price
    contract_data["name"] = "New Contract Name"
    contract_data["items"][0]["price_setup"] = 1

    response = admin_client.patch(
        f"/api/v1/contracts/{contract_data['number']}/",
        contract_data,
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    contract.refresh_from_db()
    assert data["number"] == contract_data["number"]
    assert data["name"] == "New Contract Name"
    assert contract.name == "New Contract Name"
    item = contract.items.first()
    assert item.price_setup == 1
    assert Contract.objects.count() == 1
    assert ContractItem.objects.count() == 2


@pytest.mark.django_db
def test_contract_terminate(contract, admin_client):
    assert not contract.termination_date
    response = admin_client.post(
        f"/api/v1/contracts/{contract.number}/terminate/",
        {},
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    contract.refresh_from_db()
    assert data["termination_date"]
    assert contract.termination_date


@pytest.mark.django_db
def test_contract_terminate_given_date(contract, admin_client):
    assert not contract.termination_date
    next_date = contract.next_possible_contract_end
    response = admin_client.post(
        f"/api/v1/contracts/{contract.number}/terminate/",
        {"date": next_date},
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    contract.refresh_from_db()
    assert data["termination_date"]
    assert contract.termination_date


@pytest.mark.django_db
def test_contract_terminate_given_date_too_early(contract, admin_client):
    assert not contract.termination_date
    next_date = contract.next_possible_contract_end
    response = admin_client.post(
        f"/api/v1/contracts/{contract.number}/terminate/",
        {"date": next_date - dt.timedelta(days=1)},
        HTTP_ACCEPT="application/json",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    contract.refresh_from_db()
    assert data["error"]["termination_date"]
    assert not contract.termination_date


# TODO
# def test_contract_list_add_predecessor
# def test_contract_list_add_successor
# def test_contract_list_remove_predecessor
# def test_contract_list_remove_successor
# def test_contract_list_add_parent
# def test_contract_list_add_child
# def test_contract_list_remove_parent
# def test_contract_list_remove_child
