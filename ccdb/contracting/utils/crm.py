import requests
from django.conf import settings
from django.utils.timezone import now
from tqdm import tqdm

from contracting.models import Customer

CRM_URL = "https://backend.globalways.net/v1/graphql"


def _get_data(customer_ids):
    ids = ",".join(str(cid) for cid in customer_ids)
    query = (
        """{
  customer(where: {customerno: {_in: [%s]}}) {
    customerno
    company_name
    street
    houseno
    housenoadd
    zip
    city
    country
    tel
    ustid
    email
  }
}
    """
        % ids
    )
    settings.GLOBALWAYS_CRM_KEY = "backstab-banister"
    headers = {
        "content-type": "application/json",
        "x-hasura-admin-secret": settings.GLOBALWAYS_CRM_KEY,
    }
    response = requests.post(CRM_URL, headers=headers, json={"query": query})
    response.raise_for_status()
    return response.json()


def apply_batch_data(data):
    _now = now()
    for customer_data in tqdm(data["data"]["customer"], "Saving data"):
        customer = Customer.objects.get(number=customer_data["customerno"])
        customer.crm_data["synced_data"] = customer_data
        customer.crm_last_sync = _now
        customer.name = customer_data["company_name"]
        customer.save()


def pull_batch_data(batch):
    data = _get_data(batch)
    apply_batch_data(data)


def pull_customer_data(customers=None, batch_size=100):
    batch_size = batch_size or 100
    customers = customers or list(
        Customer.objects.all().values_list("number", flat=True)
    )

    i = 0
    for i in range(0, len(customers), batch_size):
        print(f"Pulling customer data, step {i + 1}")
        batch = customers[i : i + batch_size]
        if batch:
            pull_batch_data(batch)
