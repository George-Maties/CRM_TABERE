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
    make_opportunity(founder, status=Status.CALLED)
    make_opportunity(founder, status=Status.CALLED)
    make_opportunity(founder, status=Status.WON)

    response = founder_client.get(reverse("oportunitati:list"), {"status": "sunat"})

    counts = {tab["value"]: tab["count"] for tab in response.context["status_tabs"]}
    assert counts["sunat"] == 2 and counts["castigata"] == 1
    assert len(response.context["opportunity_list"]) == 2


def test_create_form_offers_only_open_statuses(seller_client, contact):
    form = seller_client.get(reverse("oportunitati:create"), {"contact": contact.pk}).context[
        "form"
    ]

    assert "owner" not in form.fields
    assert [value for value, _ in form.fields["status"].choices] == [
        "nou",
        "sunat",
        "raspuns",
        "in_lucru",
    ]


def test_create_with_status_needs_note(seller_client, contact):
    response = seller_client.post(
        reverse("oportunitati:create"),
        {"contact": contact.pk, "title": "Tabăra de iarnă", "status": "sunat", "note": ""},
    )

    assert response.context["form"].errors["note"]


def test_seller_creates_opportunity_from_contact(seller_client, seller, contact):
    contact.assigned_to = seller
    contact.save()

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
    contact.refresh_from_db()
    assert contact.assigned_to == seller


def test_seller_cannot_create_opportunity_for_contact_not_assigned_to_them(
    seller_client, other_seller, contact
):
    contact.assigned_to = other_seller
    contact.save()

    response = seller_client.post(
        reverse("oportunitati:create"), {"contact": contact.pk, "title": "X", "status": "nou"}
    )

    assert response.context["form"].errors["contact"]
    assert not Opportunity.objects.exists()


def _change_status(client, opportunity, **data):
    return client.post(reverse("oportunitati:status", args=[opportunity.pk]), data)


def test_status_change_is_recorded_with_comment(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    _change_status(seller_client, opportunity, status="sunat", comment="Revin joi.")

    opportunity.refresh_from_db()
    assert opportunity.status == Status.CALLED
    note = opportunity.notes.get()
    assert note.status_change == "Nou → Sunat" and note.text == "Revin joi."


def test_status_change_requires_comment(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="pierduta", comment="")

    assert response.context["status_form"].errors["comment"]
    opportunity.refresh_from_db()
    assert opportunity.status == Status.NEW


def test_status_change_rejects_same_status(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="nou", comment="Nimic nou.")

    assert response.context["status_form"].errors["status"]


def test_lost_records_the_reason(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    _change_status(seller_client, opportunity, status="pierduta", comment="Prea scump.")

    note = opportunity.notes.get()
    assert note.status_change == "Nou → Pierdută" and note.text == "Prea scump."


def test_won_needs_a_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="castigata", comment="Da!")

    assert response.context["status_form"].errors["camp_name"]
    opportunity.refresh_from_db()
    assert opportunity.status == Status.NEW


def test_won_joins_existing_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    _change_status(
        seller_client, opportunity, status="castigata", camp=camp.pk, comment="Avans plătit."
    )

    opportunity.refresh_from_db()
    assert opportunity.status == Status.WON and opportunity.camp == camp
    assert opportunity.notes.get().status_change == "Nou → Câștigată · Vară 2027"


def test_won_creates_new_camp(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    _change_status(
        seller_client,
        opportunity,
        status="castigata",
        camp_name="Iarnă 2027",
        camp_start="2027-02-10",
        camp_end="2027-02-16",
        comment="Confirmat.",
    )

    opportunity.refresh_from_db()
    assert opportunity.camp.name == "Iarnă 2027"
    assert opportunity.camp.created_by == seller


def test_leaving_won_takes_contact_out_of_camp(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    _change_status(seller_client, opportunity, status="pierduta", comment="A renunțat.")

    opportunity.refresh_from_db()
    assert opportunity.camp is None


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
