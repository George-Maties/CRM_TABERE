import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.accounts.roles import FOUNDER, SELLER
from apps.contacte.models import Contact
from apps.oportunitati.models import Opportunity


@pytest.fixture(autouse=True)
def fast_passwords(settings):
    """Tests create many users; the production password hasher is slow on purpose."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Create the roles once, in the test database; every test starts from them."""
    with django_db_blocker.unblock():
        call_command("setup_roles", stdout=open("/dev/null", "w"))


@pytest.fixture
def roles(db):
    """The built-in roles (created once per run by django_db_setup)."""


def _user_with_role(django_user_model, username, role):
    user = django_user_model.objects.create_user(username=username, password="parola-sigura-123")
    user.groups.add(Group.objects.get(name=role))
    return user


@pytest.fixture
def founder(roles, django_user_model):
    return _user_with_role(django_user_model, "paula", FOUNDER)


@pytest.fixture
def seller(roles, django_user_model):
    return _user_with_role(django_user_model, "vilma", SELLER)


@pytest.fixture
def other_seller(roles, django_user_model):
    return _user_with_role(django_user_model, "ion", SELLER)


@pytest.fixture
def founder_client(client, founder):
    client.force_login(founder)
    return client


@pytest.fixture
def seller_client(client, seller):
    client.force_login(seller)
    return client


@pytest.fixture
def contact(db):
    return Contact.objects.create(name="Ana Pop", phone="0700 000 001")


@pytest.fixture
def make_opportunity(contact):
    def make(owner, **fields):
        return Opportunity.objects.create(contact=contact, owner=owner, **fields)

    return make
