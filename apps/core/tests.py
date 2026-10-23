import pytest
from django.apps import apps
from django.urls import reverse

from apps.core.navigation import MenuItem, sidebar_items

SECTIONS = ["wall:index", "oportunitati:list", "contacte:list", "tabere:list"]
MENU = ["Wall", "Oportunități", "Contacte", "Tabere"]


@pytest.mark.django_db
def test_health(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("url_name", SECTIONS)
def test_section_requires_login(client, url_name):
    url = reverse(url_name)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={url}"


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", SECTIONS)
def test_section_renders_with_sidebar(admin_client, url_name):
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200
    items = response.context["sidebar_items"]
    assert [item["label"] for item in items] == MENU
    assert [item["url"] for item in items if item["active"]] == [reverse(url_name)]


@pytest.mark.django_db
def test_sidebar_hides_items_without_permission(rf, django_user_model, monkeypatch):
    secret = MenuItem(label="Secret", url_name="wall:index", icon="bi-lock", permission="x.y")
    monkeypatch.setattr(apps.get_app_config("wall"), "menu_items", (secret,))
    request = rf.get("/")
    request.user = django_user_model.objects.create_user(username="ana")

    labels = [item["label"] for item in sidebar_items(request)]

    assert "Secret" not in labels


@pytest.mark.django_db
def test_sidebar_by_role(rf, django_user_model, seller):
    request = rf.get("/")

    request.user = seller
    assert [item["label"] for item in sidebar_items(request)] == MENU

    request.user = django_user_model.objects.create_user(username="fara-rol")
    assert [item["label"] for item in sidebar_items(request)] == ["Wall"]


def test_messages_show_as_notifications(seller_client):
    response = seller_client.post(
        reverse("contacte:create"), {"name": "Elena Stan", "kind": "parinte"}, follow=True
    )

    html = response.content.decode()
    assert 'class="notification notification-success"' in html
    assert "Contactul „Elena Stan” a fost adăugat." in html
    # Blueprints for notify() in JavaScript, one per type
    assert html.count("data-notification-template=") == 4
