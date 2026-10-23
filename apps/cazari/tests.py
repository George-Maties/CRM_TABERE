import pytest
from django.urls import reverse

from apps.tabere.models import Camp

from .models import Accommodation


def test_founder_adds_accommodation(founder_client):
    response = founder_client.post(
        reverse("cazari:create"),
        {
            "name": "Pensiunea Bradul",
            "city": "Bran",
            "capacity": "40",
            "contact_name": "Ioan Bradu",
            "phone": "0268 000 101",
        },
    )

    assert response.url == reverse("cazari:list")
    place = Accommodation.objects.get()
    assert (place.city, place.capacity, place.contact_name) == ("Bran", 40, "Ioan Bradu")
    page = founder_client.get(reverse("cazari:list")).content.decode()
    assert "Pensiunea Bradul" in page and 'href="tel:0268 000 101"' in page


def test_only_name_and_seats_are_required(founder_client):
    response = founder_client.post(reverse("cazari:create"), {"name": "", "capacity": ""})

    errors = response.context["form"].errors
    assert set(errors) == {"name", "capacity"}

    founder_client.post(reverse("cazari:create"), {"name": "Cabana", "capacity": "12"})
    assert Accommodation.objects.get().name == "Cabana"


def test_seats_must_be_at_least_one(founder_client):
    response = founder_client.post(reverse("cazari:create"), {"name": "Cabana", "capacity": "0"})

    assert response.context["form"].errors["capacity"] == [
        "Cazarea trebuie să aibă cel puțin un loc."
    ]


def test_founder_edits_accommodation(founder_client):
    place = Accommodation.objects.create(name="Cabana", capacity=10)

    founder_client.post(
        reverse("cazari:update", args=[place.pk]), {"name": "Cabana Clăbucet", "capacity": "32"}
    )

    place.refresh_from_db()
    assert (place.name, place.capacity) == ("Cabana Clăbucet", 32)


@pytest.mark.parametrize("url_name", ["cazari:list", "cazari:create"])
def test_sellers_have_no_accommodation_section(seller_client, url_name):
    response = seller_client.get(reverse(url_name))

    assert response.status_code == 403
    wall = seller_client.get(reverse("wall:index"))
    assert "Cazări" not in [item["label"] for item in wall.context["sidebar_items"]]


def test_founder_sees_the_section_in_the_sidebar(founder_client):
    wall = founder_client.get(reverse("wall:index"))

    assert "Cazări" in [item["label"] for item in wall.context["sidebar_items"]]


def test_accommodation_used_by_a_camp_cannot_be_deleted(founder_client):
    place = Accommodation.objects.create(name="Cabana", capacity=10)
    Camp.objects.create(name="Iarnă", start_date="2027-02-10", accommodation=place)

    response = founder_client.post(reverse("cazari:delete", args=[place.pk]))

    assert response.url == place.get_absolute_url()
    assert Accommodation.objects.exists()


def test_unused_accommodation_is_deleted(founder_client):
    place = Accommodation.objects.create(name="Cabana", capacity=10)

    response = founder_client.post(reverse("cazari:delete", args=[place.pk]))

    assert response.url == reverse("cazari:list")
    assert not Accommodation.objects.exists()
