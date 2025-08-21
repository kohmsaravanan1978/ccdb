import pytest


@pytest.mark.django_db
def test_setup(account):
    assert account.id
