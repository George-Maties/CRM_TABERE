from django.urls import reverse

from apps.oportunitati.models import Status

from .models import Camp, Task


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


def test_opportunity_page_has_no_tasks(seller_client, seller, make_opportunity):
    response = seller_client.get(make_opportunity(seller).get_absolute_url())

    assert "task_form" not in response.context


def test_camp_page_hides_contacts_the_seller_cannot_see(
    seller_client, other_seller, contact, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    contact.assigned_to = other_seller
    contact.save()
    make_opportunity(other_seller, status=Status.WON, camp=camp)

    html = seller_client.get(camp.get_absolute_url()).content.decode()

    assert contact.name in html
    assert contact.get_absolute_url() not in html
    assert contact.phone not in html
