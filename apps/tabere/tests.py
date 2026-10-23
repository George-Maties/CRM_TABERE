from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cazari.models import Accommodation
from apps.oportunitati.models import Status

from .models import Camp, CampStatus, Child, Task


def test_camp_list_counts_only_won_participants(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    make_opportunity(seller, status=Status.WON, camp=camp)

    response = seller_client.get(reverse("tabere:list"))

    assert response.context["camp_list"][0].participant_count == 1


def test_camp_page_lists_participants(seller_client, seller, other_seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    mine = make_opportunity(seller, status=Status.WON, camp=camp)
    theirs = make_opportunity(other_seller, status=Status.WON, camp=camp)

    response = seller_client.get(camp.get_absolute_url())

    assert set(response.context["participants"]) == {mine, theirs}
    # The seller sees every child in the camp but can open only their own opportunity.
    assert response.context["visible_ids"] == {mine.pk}


def test_seller_creates_but_cannot_edit_camp(seller_client):
    seller_client.post(reverse("tabere:create"), {"name": "Iarnă", "start_date": "2027-02-10"})
    camp = Camp.objects.get(name="Iarnă")

    response = seller_client.get(reverse("tabere:update", args=[camp.pk]))

    assert response.status_code == 403


def test_camp_end_cannot_be_before_start(founder_client):
    response = founder_client.post(
        reverse("tabere:create"),
        {"name": "Greșită", "start_date": "2027-02-10", "end_date": "2027-02-01"},
    )

    assert response.context["form"].errors["end_date"]


def test_camp_with_participants_cannot_be_deleted(founder_client, founder, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    make_opportunity(founder, status=Status.WON, camp=camp)

    response = founder_client.post(reverse("tabere:delete", args=[camp.pk]))

    assert response.url == camp.get_absolute_url()
    assert Camp.objects.filter(pk=camp.pk).exists()


def test_seller_assigns_camp_task_to_founder(seller_client, seller, founder):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    seller_client.post(
        reverse("tabere:task", args=[camp.pk]),
        {"title": "Rezervă autocarul", "assigned_to": founder.pk, "due_date": "2027-06-01"},
    )

    task = camp.tasks.get()
    assert task.assigned_to == founder and task.created_by == seller


def test_task_without_title_shows_error(seller_client, seller):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    response = seller_client.post(
        reverse("tabere:task", args=[camp.pk]), {"title": "", "assigned_to": seller.pk}
    )

    assert response.context["task_form"].errors["title"]
    assert not camp.tasks.exists()


def test_task_toggle(seller_client, seller):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    task = Task.objects.create(camp=camp, title="Sună", assigned_to=seller)

    seller_client.post(reverse("tabere:task-toggle", args=[task.pk]))

    task.refresh_from_db()
    assert task.done and task.done_at is not None


def test_camp_page_hides_contacts_the_seller_cannot_see(
    seller_client, other_seller, contact, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    contact.assignees.add(other_seller)
    make_opportunity(other_seller, status=Status.WON, camp=camp)

    html = seller_client.get(camp.get_absolute_url()).content.decode()

    assert contact.name in html
    assert contact.get_absolute_url() not in html
    assert contact.phone not in html


def test_seller_adds_child_under_their_contact(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    response = seller_client.post(
        reverse("tabere:child-add", args=[opportunity.pk]),
        {"name": "Matei Pop", "age": "9", "city": "Brașov", "medical_notes": "Alergic la arahide."},
    )

    assert response.url == f"{camp.get_absolute_url()}#participant-{opportunity.pk}"
    child = Child.objects.get()
    assert child.opportunity == opportunity
    assert child.name == "Matei Pop" and child.created_by == seller
    assert (child.age, child.city, child.medical_notes) == (9, "Brașov", "Alergic la arahide.")
    page = seller_client.get(camp.get_absolute_url())
    assert page.context["child_count"] == 1
    html = page.content.decode()
    assert 'class="child-row"' in html and "Matei Pop" in html and "9 ani" in html
    assert "Brașov" in html and "Alergic la arahide." in html
    assert f'data-bs-target="#copil-{opportunity.pk}"' in html


def test_contact_can_bring_several_children(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)
    for name in ("Matei Pop", "Ana Pop"):
        seller_client.post(
            reverse("tabere:child-add", args=[opportunity.pk]), {"name": name, "age": "8"}
        )

    response = seller_client.get(camp.get_absolute_url())

    [participant] = response.context["participants"]
    assert [c.name for c in participant.children.all()] == ["Ana Pop", "Matei Pop"]
    assert "2 copii" in response.content.decode()


def test_child_without_name_reopens_the_form_with_the_error(
    seller_client, seller, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    response = seller_client.post(
        reverse("tabere:child-add", args=[opportunity.pk]), {"name": "", "age": "40"}
    )

    assert response.status_code == 200
    assert response.context["child_form_for"] == opportunity.pk
    assert response.context["child_form"].errors["name"]
    assert response.context["child_form"].errors["age"] == ["Vârsta nu poate fi mai mare de 30."]
    assert 'class="child-form-row collapse show"' in response.content.decode()
    assert not Child.objects.exists()


def test_seller_cannot_add_children_to_someone_elses_contact(
    seller_client, other_seller, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    theirs = make_opportunity(other_seller, status=Status.WON, camp=camp)

    response = seller_client.post(reverse("tabere:child-add", args=[theirs.pk]), {"name": "X"})
    page = seller_client.get(camp.get_absolute_url()).content.decode()

    assert response.status_code == 404
    assert not Child.objects.exists()
    assert f'data-bs-target="#copil-{theirs.pk}"' not in page


def test_children_only_for_contacts_in_a_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(
        reverse("tabere:child-add", args=[opportunity.pk]), {"name": "Matei"}
    )

    assert response.status_code == 404


def test_seller_removes_child(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)
    child = Child.objects.create(opportunity=opportunity, name="Matei Pop")

    response = seller_client.post(reverse("tabere:child-delete", args=[child.pk]))

    assert response.url == f"{camp.get_absolute_url()}#participant-{opportunity.pk}"
    assert not Child.objects.exists()


def test_founder_adds_child_to_any_contact(founder_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    founder_client.post(
        reverse("tabere:child-add", args=[opportunity.pk]), {"name": "Ioana", "age": "11"}
    )

    assert opportunity.children.get().name == "Ioana"


def test_camp_picks_its_accommodation_from_the_list(founder_client):
    place = Accommodation.objects.create(name="Pensiunea Bradul", city="Bran", capacity=40)
    founder_client.post(
        reverse("tabere:create"),
        {"name": "Vară 2027", "start_date": "2027-07-04", "accommodation": place.pk},
    )
    camp = Camp.objects.get()

    detail = founder_client.get(camp.get_absolute_url()).content.decode()
    listing = founder_client.get(reverse("tabere:list")).content.decode()

    assert camp.accommodation == place
    assert "Pensiunea Bradul" in detail and "Bran" in detail and "din 40 de locuri" in detail
    assert ">Cazare</th>" in listing and "Pensiunea Bradul" in listing
    form = founder_client.get(reverse("tabere:update", args=[camp.pk])).context["form"]
    assert "location" not in form.fields
    assert [label for _, label in form.fields["accommodation"].choices] == [
        "Nealeasă încă",
        "Pensiunea Bradul, Bran · 40 locuri",
    ]


def test_camp_cannot_use_an_accommodation_not_in_the_list(founder_client):
    response = founder_client.post(
        reverse("tabere:create"),
        {"name": "Vară 2027", "start_date": "2027-07-04", "accommodation": "999"},
    )

    assert response.context["form"].errors["accommodation"]


def test_contact_goes_to_camp_and_takes_a_seat(seller_client, seller, make_opportunity):
    place = Accommodation.objects.create(name="Pensiunea Bradul", city="Bran", capacity=40)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04", accommodation=place)
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)
    Child.objects.create(opportunity=opportunity, name="Matei", age=9)
    Child.objects.create(opportunity=opportunity, name="Ana", age=7)

    response = seller_client.post(
        reverse("tabere:participant-goes", args=[opportunity.pk]), {"contact_goes": "1"}
    )

    assert response.url == f"{camp.get_absolute_url()}#participant-{opportunity.pk}"
    opportunity.refresh_from_db()
    assert opportunity.contact_goes
    page = seller_client.get(camp.get_absolute_url())
    assert (page.context["child_count"], page.context["adult_count"]) == (2, 1)
    html = page.content.decode()
    assert "2 copii și 1 adult · 3 din 40 de locuri" in html
    assert '<span class="participant-children">2 copii</span>' in html
    assert f'id="merge-{opportunity.pk}" checked' in html

    seller_client.post(reverse("tabere:participant-goes", args=[opportunity.pk]), {})

    opportunity.refresh_from_db()
    assert not opportunity.contact_goes


def test_seller_cannot_tick_someone_elses_participant(
    seller_client, other_seller, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    theirs = make_opportunity(other_seller, status=Status.WON, camp=camp)

    response = seller_client.post(
        reverse("tabere:participant-goes", args=[theirs.pk]), {"contact_goes": "1"}
    )

    assert response.status_code == 404
    theirs.refresh_from_db()
    assert not theirs.contact_goes


def _camp_starting_in(days, length=6, **fields):
    start = timezone.localdate() + timedelta(days=days)
    return Camp.objects.create(
        name=fields.pop("name", f"Tabăra {days}"),
        start_date=start,
        end_date=start + timedelta(days=length) if length is not None else None,
        **fields,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "days, length, status",
    [
        (15, 6, CampStatus.PREPARING),
        (14, 6, CampStatus.FINAL_DETAILS),
        (1, 6, CampStatus.FINAL_DETAILS),
        (0, 6, CampStatus.RUNNING),
        (-6, 6, CampStatus.RUNNING),
        (-7, 6, CampStatus.FINISHED),
        (0, None, CampStatus.RUNNING),
        (-1, None, CampStatus.FINISHED),
    ],
)
def test_camp_status_follows_the_dates(days, length, status):
    camp = _camp_starting_in(days, length)

    assert camp.status == status
    # The database works it out the same way, for filtering.
    assert Camp.objects.with_status().get(pk=camp.pk).period_status == status


def test_camp_list_filters_by_status_and_searches(seller_client):
    place = Accommodation.objects.create(name="Pensiunea Bradul", city="Bran", capacity=40)
    _camp_starting_in(60, name="Vară Bran", accommodation=place)
    _camp_starting_in(5, name="Iarnă Predeal")
    _camp_starting_in(-2, name="Primăvară")
    _camp_starting_in(-30, name="Toamnă trecută")

    response = seller_client.get(reverse("tabere:list"), {"status": "ultimele_detalii"})

    assert [c.name for c in response.context["camp_list"]] == ["Iarnă Predeal"]
    counts = {tab["label"]: tab["count"] for tab in response.context["status_tabs"]}
    assert counts == {
        "Toate": 4,
        "În lucru": 1,
        "Ultimele detalii": 1,
        "În desfășurare": 1,
        "Finalizată": 1,
    }
    html = response.content.decode()
    assert 'data-auto-search="rezultate"' in html and "Ultimele detalii" in html

    found = seller_client.get(reverse("tabere:list"), {"q": "bran"})
    assert [c.name for c in found.context["camp_list"]] == ["Vară Bran"]


def test_camp_page_shows_its_status(seller_client):
    camp = _camp_starting_in(-1, name="Vară")

    html = seller_client.get(camp.get_absolute_url()).content.decode()

    assert "În desfășurare" in html
