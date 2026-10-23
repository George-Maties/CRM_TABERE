import pytest
from django.urls import reverse

from apps.tabere.models import Camp

from .models import Opportunity, Status


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


def test_founder_sees_all_opportunities(founder_client, seller, other_seller, make_opportunity):
    make_opportunity(seller)
    make_opportunity(other_seller)

    response = founder_client.get(reverse("oportunitati:list"))

    assert len(response.context["opportunity_list"]) == 2


def test_status_tabs_count_and_filter(founder_client, founder, make_opportunity):
    make_opportunity(founder)
    make_opportunity(founder)
    make_opportunity(founder, status=Status.WON)

    response = founder_client.get(reverse("oportunitati:list"), {"status": "potential"})

    tabs = response.context["status_tabs"]
    assert [tab["label"] for tab in tabs] == ["Potențial", "Câștigat", "Pierdut"]
    counts = {tab["value"]: tab["count"] for tab in tabs}
    assert counts["potential"] == 2 and counts["castigata"] == 1
    assert len(response.context["opportunity_list"]) == 2


def test_founder_filters_own_opportunities(founder_client, founder, seller, make_opportunity):
    mine = make_opportunity(founder)
    make_opportunity(seller)

    response = founder_client.get(reverse("oportunitati:list"), {"ale_mele": "1"})

    assert list(response.context["opportunity_list"]) == [mine]


def test_new_opportunity_is_potential(seller_client, seller, contact):
    contact.assignees.add(seller)
    form = seller_client.get(reverse("oportunitati:create"), {"contact": contact.pk}).context[
        "form"
    ]
    assert "owner" not in form.fields and "status" not in form.fields

    seller_client.post(reverse("oportunitati:create"), {"contact": contact.pk})

    assert Opportunity.objects.get().status == Status.POTENTIAL


def test_seller_creates_opportunity_from_contact(seller_client, seller, contact):
    contact.assignees.add(seller)

    response = seller_client.post(
        reverse("oportunitati:create"), {"contact": contact.pk, "note": "A răspuns."}
    )

    opportunity = Opportunity.objects.get()
    assert response.url == opportunity.get_absolute_url()
    assert opportunity.owner == seller
    assert opportunity.notes.get().text == "A răspuns."


def test_founder_assigns_opportunity_to_seller(founder_client, seller, contact):
    founder_client.post(
        reverse("oportunitati:create"),
        {"contact": contact.pk, "owner": seller.pk},
    )

    assert Opportunity.objects.get().owner == seller
    assert list(contact.assignees.all()) == [seller]


def test_seller_cannot_create_opportunity_for_contact_not_assigned_to_them(
    seller_client, other_seller, contact
):
    contact.assignees.add(other_seller)

    response = seller_client.post(reverse("oportunitati:create"), {"contact": contact.pk})

    assert response.context["form"].errors["contact"]
    assert not Opportunity.objects.exists()


def _change_status(client, opportunity, **data):
    return client.post(reverse("oportunitati:status", args=[opportunity.pk]), data)


def test_reason_is_asked_only_when_losing(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller, status=Status.LOST)

    response = _change_status(seller_client, opportunity, status="potential")

    assert response.status_code == 302
    opportunity.refresh_from_db()
    assert opportunity.status == Status.POTENTIAL
    change = opportunity.notes.get()
    assert change.status_change == "Pierdut → Potențial" and change.text == ""
    assert change.new_status == Status.POTENTIAL


def test_reason_field_shows_only_for_lost(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    page = seller_client.get(opportunity.get_absolute_url()).content.decode()

    assert 'data-show-if="id_status=pierduta"' in page
    assert "Motivul pierderii" in page
    assert "Comentariu" not in page


def test_status_change_rejects_same_status(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="potential")

    assert response.context["status_form"].errors["status"]


def test_lost_needs_a_reason(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="pierduta", reason="  ")

    assert response.context["status_form"].errors["reason"] == [
        "Scrieți motivul pentru care oportunitatea e pierdută."
    ]
    opportunity.refresh_from_db()
    assert opportunity.status == Status.POTENTIAL and opportunity.owner == seller


def test_lost_saves_the_reason_as_a_note_and_takes_the_seller_off(
    seller_client, seller, make_opportunity
):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="pierduta", reason="Prea scump.")

    # The seller can no longer open it, so they go back to their list.
    assert response.url == reverse("oportunitati:list")
    opportunity.refresh_from_db()
    assert opportunity.status == Status.LOST and opportunity.owner is None
    # Newest first: the status change, then the reason as an ordinary note.
    change, note = opportunity.notes.all()
    assert change.status_change == "Potențial → Pierdut" and change.text == ""
    assert change.new_status == Status.LOST
    assert note.text == "Prea scump." and note.status_change == "" and note.author == seller
    assert seller_client.get(opportunity.get_absolute_url()).status_code == 404


def test_reason_typed_for_another_status_is_not_kept(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    _change_status(
        seller_client, opportunity, status="castigata", camp=camp.pk, reason="Prea scump."
    )

    assert not opportunity.notes.exclude(status_change="").filter(text__gt="").exists()
    assert opportunity.notes.count() == 1


def test_founder_sees_lost_opportunity_without_owner(founder_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    opportunity.change_status(Status.LOST, seller, "A ales altă tabără.")

    response = founder_client.get(opportunity.get_absolute_url())

    assert response.status_code == 200
    assert "Nimeni (pierdut)" in response.content.decode()
    assert (
        "owner"
        not in founder_client.get(reverse("oportunitati:update", args=[opportunity.pk]))
        .context["form"]
        .fields
    )


def test_reopening_lost_opportunity_makes_you_responsible(
    founder_client, founder, seller, make_opportunity
):
    opportunity = make_opportunity(seller)
    opportunity.change_status(Status.LOST, seller, "Nu răspunde.")

    _change_status(founder_client, opportunity, status="potential")

    opportunity.refresh_from_db()
    assert opportunity.status == Status.POTENTIAL and opportunity.owner == founder


def test_won_needs_an_existing_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(
        seller_client,
        opportunity,
        status="castigata",
        camp_name="Iarnă 2027",
        camp_start="2027-02-10",
    )

    assert response.context["status_form"].errors["camp"]
    opportunity.refresh_from_db()
    assert opportunity.status == Status.POTENTIAL
    assert not Camp.objects.exists()
    assert "Nu există încă nicio tabără" in response.content.decode()


def test_won_joins_existing_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    response = _change_status(seller_client, opportunity, status="castigata", camp=camp.pk)

    assert response.url == opportunity.get_absolute_url()
    opportunity.refresh_from_db()
    assert opportunity.status == Status.WON and opportunity.camp == camp
    assert opportunity.owner == seller
    assert opportunity.notes.get().status_change == "Potențial → Câștigat · Vară 2027"


def test_leaving_won_takes_contact_out_of_camp(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    _change_status(seller_client, opportunity, status="potential")

    opportunity.refresh_from_db()
    assert opportunity.camp is None


def test_history_is_a_timeline_grouped_by_day(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    opportunity.notes.create(author=seller, text="A sunat înapoi.")
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity.change_status(Status.WON, seller, camp=camp)

    page = seller_client.get(opportunity.get_absolute_url()).content.decode()

    assert page.count('class="timeline-day"') == 1
    assert "Astăzi" in page
    assert '<div class="timeline-note text-prewrap">A sunat înapoi.</div>' in page
    assert "bi-trophy" in page and "text-success-emphasis" in page


def test_empty_note_shows_error(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(reverse("oportunitati:note", args=[opportunity.pk]), {"text": ""})

    assert response.status_code == 200
    assert response.context["note_form"].errors
    assert not opportunity.notes.exists()


def test_seller_cannot_delete_opportunity(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(reverse("oportunitati:delete", args=[opportunity.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_founder_has_no_user_management(founder):
    assert not founder.is_staff
    assert not founder.has_perm("auth.add_user")


def test_title_is_the_contact_name_numbered_when_there_are_several(
    seller_client, seller, contact, make_opportunity
):
    first = make_opportunity(seller)
    assert first.title == "Ana Pop"

    second = make_opportunity(seller)

    assert (first.number, second.number) == (1, 2)
    assert Opportunity.objects.get(pk=first.pk).title == "Ana Pop #1"
    titles = [
        o.title for o in seller_client.get(reverse("oportunitati:list")).context["opportunity_list"]
    ]
    assert sorted(titles) == ["Ana Pop #1", "Ana Pop #2"]


def test_numbers_are_kept_after_a_delete(founder, contact, make_opportunity):
    first = make_opportunity(founder)
    make_opportunity(founder)
    first.delete()

    third = make_opportunity(founder)

    assert third.number == 3
    assert third.title == "Ana Pop #3"


def test_moving_to_another_contact_takes_its_next_number(
    founder_client, founder, contact, make_opportunity
):
    from apps.contacte.models import Contact

    other = Contact.objects.create(name="Mihai Popa")
    Opportunity.objects.create(contact=other, owner=founder)
    opportunity = make_opportunity(founder)

    founder_client.post(
        reverse("oportunitati:update", args=[opportunity.pk]),
        {"contact": other.pk, "owner": founder.pk},
    )

    opportunity.refresh_from_db()
    assert (opportunity.contact, opportunity.number) == (other, 2)
