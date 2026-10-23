from io import BytesIO

import pytest
from django.urls import reverse
from openpyxl import load_workbook

from apps.oportunitati.models import Status

from .models import Camp, Child, Room


@pytest.fixture
def camp(db):
    return Camp.objects.create(name="Vară 2027", start_date="2027-07-04")


@pytest.fixture
def family(camp, seller, make_opportunity):
    """Ana Pop in the camp, coming along, with two children."""
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp, contact_goes=True)
    Child.objects.create(opportunity=opportunity, name="Matei Pop", age=9, medical_notes="Astm")
    Child.objects.create(opportunity=opportunity, name="Ioana Pop", age=7, city="Brașov")
    return opportunity


def _move(client, camp, occupant, room=""):
    return client.post(
        reverse("tabere:occupant-move", args=[camp.pk]), {"occupant": occupant, "room": room}
    )


def test_configurator_is_for_founders(client, founder, seller, camp, family):
    client.force_login(founder)
    page = client.get(reverse("tabere:configurator", args=[camp.pk]))
    camp_page = client.get(camp.get_absolute_url()).content.decode()

    assert page.status_code == 200
    html = page.content.decode()
    # Right: the participants, the contact first, then the children
    assert html.index("Ana Pop") < html.index("Matei Pop")
    assert 'data-occupant="adult-' in html and "(adult)" in html
    assert "Configurator" in camp_page
    client.force_login(seller)
    assert client.get(reverse("tabere:configurator", args=[camp.pk])).status_code == 403
    assert "Configurator" not in client.get(camp.get_absolute_url()).content.decode()


def test_seller_cannot_move_or_download(seller_client, camp, family):
    child = family.children.first()

    assert _move(seller_client, camp, f"copil-{child.pk}").status_code == 403
    assert seller_client.get(reverse("tabere:rooms-excel", args=[camp.pk])).status_code == 403


def test_rooms_are_added_in_batches_and_numbered(founder_client, camp):
    founder_client.post(reverse("tabere:rooms-add", args=[camp.pk]), {"count": 3, "capacity": 4})
    founder_client.post(reverse("tabere:rooms-add", args=[camp.pk]), {"count": 2, "capacity": 2})

    rooms = [(room.name, room.capacity) for room in camp.rooms.all()]
    assert rooms == [
        ("Camera 1", 4),
        ("Camera 2", 4),
        ("Camera 3", 4),
        ("Camera 4", 2),
        ("Camera 5", 2),
    ]


def test_room_batch_needs_numbers(founder_client, camp):
    response = founder_client.post(
        reverse("tabere:rooms-add", args=[camp.pk]), {"count": 0, "capacity": ""}
    )

    assert response.status_code == 200
    assert set(response.context["room_form"].errors) == {"count", "capacity"}
    assert not camp.rooms.exists()


def test_children_and_the_contact_who_goes_are_placed(founder_client, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=3)
    matei = family.children.get(name="Matei Pop")

    child_move = _move(founder_client, camp, f"copil-{matei.pk}", room.pk)
    adult_move = _move(founder_client, camp, f"adult-{family.pk}", room.pk)

    assert child_move.json() == {"room": room.pk} and adult_move.status_code == 200
    matei.refresh_from_db()
    family.refresh_from_db()
    assert matei.room == room and family.contact_room == room
    page = founder_client.get(reverse("tabere:configurator", args=[camp.pk]))
    assert page.context["placed_count"] == 2 and page.context["people_count"] == 3
    assert "1 loc liber" in page.content.decode()

    _move(founder_client, camp, f"copil-{matei.pk}", "")

    matei.refresh_from_db()
    assert matei.room is None


def test_full_room_refuses_one_more(founder_client, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=1)
    matei, ioana = family.children.order_by("name").reverse()

    _move(founder_client, camp, f"copil-{matei.pk}", room.pk)
    response = _move(founder_client, camp, f"copil-{ioana.pk}", room.pk)

    assert response.status_code == 409
    assert response.json() == {"error": "Camera 1 e plină."}
    ioana.refresh_from_db()
    assert ioana.room is None


def test_contact_who_does_not_go_cannot_be_placed(founder_client, camp, family):
    family.contact_goes = False
    family.save()
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=2)

    response = _move(founder_client, camp, f"adult-{family.pk}", room.pk)

    assert response.status_code == 404


def test_rooms_of_another_camp_are_refused(founder_client, camp, family):
    other = Camp.objects.create(name="Iarnă", start_date="2027-02-10")
    room = Room.objects.create(camp=other, name="Camera 1", capacity=4)
    child = family.children.first()

    response = _move(founder_client, camp, f"copil-{child.pk}", room.pk)

    assert response.status_code == 404


def test_untick_goes_frees_the_contacts_bed(founder_client, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=2)
    family.contact_room = room
    family.save()

    founder_client.post(reverse("tabere:participant-goes", args=[family.pk]), {})

    family.refresh_from_db()
    assert family.contact_room is None


def test_leaving_the_camp_frees_the_beds(founder, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=4)
    family.children.update(room=room)
    family.contact_room = room
    family.save()

    family.change_status(Status.LOST, founder, "Au renunțat.")

    assert not room.children.exists() and not room.adults.exists()


def test_deleting_a_room_leaves_its_people_without_a_room(founder_client, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=4)
    family.children.update(room=room)

    response = founder_client.post(reverse("tabere:room-delete", args=[room.pk]))

    assert response.url == reverse("tabere:configurator", args=[camp.pk])
    assert not Room.objects.exists()
    assert family.children.filter(room__isnull=True).count() == 2


def test_rooms_download_as_excel(founder_client, camp, family):
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=3)
    Room.objects.create(camp=camp, name="Camera 2", capacity=2)
    family.children.filter(name="Matei Pop").update(room=room)

    response = founder_client.get(reverse("tabere:rooms-excel", args=[camp.pk]))

    assert response["Content-Disposition"] == 'attachment; filename="cazare-vara-2027.xlsx"'
    rows = list(load_workbook(BytesIO(response.content)).active.values)
    assert rows[0][:3] == ("Camera", "Locuri", "Nume")
    assert rows[1] == (
        "Camera 1",
        3,
        "Matei Pop",
        "Copil",
        9,
        None,
        "Ana Pop",
        "0700 000 001",
        "Astm",
    )
    # An empty room still has its line; then whoever has no room yet.
    assert rows[2][:3] == ("Camera 2", 2, None)
    assert {row[2] for row in rows[3:]} == {"Ana Pop", "Ioana Pop"}
    assert {row[0] for row in rows[3:]} == {"Fără cameră"}
