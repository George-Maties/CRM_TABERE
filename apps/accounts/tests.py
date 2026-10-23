import pytest
from django.urls import reverse


def test_login_page_renders(client):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert 'name="username"' in response.content.decode()


@pytest.mark.django_db
def test_login_redirects_to_home(client, django_user_model):
    django_user_model.objects.create_user(username="ana", password="parola-sigura-123")

    response = client.post(
        reverse("accounts:login"), {"username": "ana", "password": "parola-sigura-123"}
    )

    assert response.status_code == 302
    assert response.url == reverse("wall:index")


@pytest.mark.django_db
def test_wrong_password_shows_error(client, django_user_model):
    django_user_model.objects.create_user(username="ana", password="parola-sigura-123")

    response = client.post(reverse("accounts:login"), {"username": "ana", "password": "gresit"})

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()


@pytest.mark.django_db
def test_logout_redirects_to_login(admin_client):
    response = admin_client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")


def test_login_page_shows_brand_name_not_domain(client, settings):
    settings.SITE_NAME = "Tabere Test"

    response = client.get(reverse("accounts:login"))

    assert "Tabere Test" in response.content.decode()


@pytest.mark.django_db
def test_wrong_password_message_uses_comma_below_diacritics(client, django_user_model):
    django_user_model.objects.create_user(username="ana", password="parola-sigura-123")

    response = client.post(reverse("accounts:login"), {"username": "ana", "password": "gresit"})

    message = response.context["form"].non_field_errors()[0]
    assert "ț" in message
    assert "ţ" not in message and "ş" not in message
