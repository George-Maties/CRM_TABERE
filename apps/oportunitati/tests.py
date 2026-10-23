import pytest
from django.urls import reverse

from .models import Opportunity, Status, Task


def test_seller_sees_only_own_opportunities(seller_client, seller, other_seller, make_opportunity):
    mine = make_opportunity(seller)
    make_opportunity(other_seller)

    response = seller_client.get(reverse("oportunitati:list"))

    assert list(response.context["opportunity_list"]) == [mine]


def test_seller_cannot_open_someone_elses_opportunity(
    seller_client, other_seller, make_opportunity
):
    theirs = make_opportunity(other_seller)

    response = seller_client.get(theirs.get_absolute_url())

    assert response.status_code == 404


def test_seller_sees_opportunity_where_they_have_a_task(
    seller_client, seller, founder, make_opportunity
):
    theirs = make_opportunity(founder)
    Task.objects.create(opportunity=theirs, title="Sună", assigned_to=seller, created_by=founder)

    response = seller_client.get(theirs.get_absolute_url())

    assert response.status_code == 200


def test_founder_sees_all_opportunities(founder_client, seller, other_seller, make_opportunity):
    make_opportunity(seller)
    make_opportunity(other_seller)

    response = founder_client.get(reverse("oportunitati:list"))

    assert len(response.context["opportunity_list"]) == 2


def test_status_tabs_count_and_filter(founder_client, founder, make_opportunity):
    make_opportunity(founder, status=Status.CALLED)
    make_opportunity(founder, status=Status.CALLED)
    make_opportunity(founder, status=Status.WON)

    response = founder_client.get(reverse("oportunitati:list"), {"status": "sunat"})

    counts = {tab["value"]: tab["count"] for tab in response.context["status_tabs"]}
    assert counts["sunat"] == 2 and counts["hotarat"] == 1
    assert len(response.context["opportunity_list"]) == 2


def test_seller_creates_opportunity_from_contact(seller_client, seller, contact):
    form = seller_client.get(reverse("oportunitati:create"), {"contact": contact.pk})
    assert "owner" not in form.context["form"].fields

    response = seller_client.post(
        reverse("oportunitati:create"),
        {
            "contact": contact.pk,
            "title": "Tabăra de iarnă",
            "status": "sunat",
            "note": "A răspuns.",
        },
    )

    opportunity = Opportunity.objects.get(title="Tabăra de iarnă")
    assert response.url == opportunity.get_absolute_url()
    assert opportunity.owner == seller
    assert opportunity.notes.get().text == "A răspuns."


def test_founder_assigns_opportunity_to_seller(founder_client, seller, contact):
    founder_client.post(
        reverse("oportunitati:create"),
        {"contact": contact.pk, "title": "Grup școală", "status": "nou", "owner": seller.pk},
    )

    assert Opportunity.objects.get(title="Grup școală").owner == seller


def test_status_change_is_recorded_in_notes(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    seller_client.post(reverse("oportunitati:status", args=[opportunity.pk]), {"status": "hotarat"})

    opportunity.refresh_from_db()
    assert opportunity.status == Status.WON
    note = opportunity.notes.get()
    assert note.is_status_change and note.text == "Nou → Hotărât"


def test_empty_note_shows_error(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(reverse("oportunitati:note", args=[opportunity.pk]), {"text": ""})

    assert response.status_code == 200
    assert response.context["note_form"].errors
    assert not opportunity.notes.exists()


def test_seller_assigns_task_to_founder(seller_client, seller, founder, make_opportunity):
    opportunity = make_opportunity(seller)

    seller_client.post(
        reverse("oportunitati:task", args=[opportunity.pk]),
        {"title": "Aprobă reducerea", "assigned_to": founder.pk, "due_date": "2027-01-15"},
    )

    task = opportunity.tasks.get()
    assert task.assigned_to == founder and task.created_by == seller


def test_task_toggle(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    task = Task.objects.create(opportunity=opportunity, title="Sună", assigned_to=seller)

    seller_client.post(reverse("oportunitati:task-toggle", args=[task.pk]))

    task.refresh_from_db()
    assert task.done and task.done_at is not None


def test_seller_cannot_delete_opportunity(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(reverse("oportunitati:delete", args=[opportunity.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_founder_has_no_user_management(founder):
    assert not founder.is_staff
    assert not founder.has_perm("auth.add_user")
