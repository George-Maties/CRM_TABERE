import pytest
from django.urls import reverse

from apps.tabere.models import Camp

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
    assert [tab["label"] for tab in tabs] == ["Toate", "Potențial", "Câștigat", "Pierdut"]
    counts = {tab["value"]: tab["count"] for tab in tabs}
    assert counts == {None: 3, "potential": 2, "castigata": 1, "pierduta": 0}
    assert [tab["label"] for tab in tabs if tab["active"]] == ["Potențial"]
    assert len(response.context["opportunity_list"]) == 2


def test_search_runs_as_you_type(founder_client, founder, contact, make_opportunity):
    make_opportunity(founder)

    response = founder_client.get(reverse("oportunitati:list"), {"q": "ana"})

    page = response.content.decode()
    assert len(response.context["opportunity_list"]) == 1
    assert 'data-auto-search="rezultate"' in page and 'id="rezultate"' in page
    assert ">Caută</button>" not in page and "Doar ale mele" not in page


def test_founder_filters_by_seller(founder_client, founder, seller, other_seller, make_opportunity):
    sellers = make_opportunity(seller)
    make_opportunity(seller, status=Status.WON)
    make_opportunity(other_seller)
    make_opportunity(founder)

    response = founder_client.get(
        reverse("oportunitati:list"), {"responsabil": seller.pk, "status": "potential"}
    )

    assert list(response.context["opportunity_list"]) == [sellers]
    counts = {tab["value"]: tab["count"] for tab in response.context["status_tabs"]}
    assert counts == {None: 2, "potential": 1, "castigata": 1, "pierduta": 0}
    # Seller tabs count within the chosen status: one potential opportunity each.
    owner_counts = {tab["value"]: tab["count"] for tab in response.context["owner_tabs"]}
    assert owner_counts == {str(founder.pk): 1, str(seller.pk): 1, str(other_seller.pk): 1}
    page = response.content.decode()
    assert 'class="status-tabs-divider"' in page
    # The selected seller's tab clears the filter and keeps the status.
    assert 'href="?status=potential" class="status-tab active"' in page


def test_seller_cannot_filter_by_another_seller(
    seller_client, seller, other_seller, make_opportunity
):
    mine = make_opportunity(seller)
    make_opportunity(other_seller)

    response = seller_client.get(reverse("oportunitati:list"), {"responsabil": other_seller.pk})

    assert list(response.context["opportunity_list"]) == [mine]
    assert response.context["owner_tabs"] == []
    assert "status-tabs-divider" not in response.content.decode()


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
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    response = _change_status(seller_client, opportunity, status="castigata", camp=camp.pk)

    assert response.status_code == 302
    opportunity.refresh_from_db()
    assert opportunity.status == Status.WON
    change = opportunity.notes.get()
    assert change.text == "" and change.new_status == Status.WON


@pytest.mark.parametrize("closed", [Status.WON, Status.LOST])
def test_closed_opportunity_never_becomes_potential_again(
    seller_client, seller, make_opportunity, closed
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(
        seller, status=closed, camp=camp if closed == Status.WON else None
    )

    response = _change_status(seller_client, opportunity, status="potential")

    form = response.context["status_form"]
    assert form.errors["status"]
    assert [value for value, _ in form.fields["status"].choices] == ["castigata", "pierduta"]
    opportunity.refresh_from_db()
    assert opportunity.status == closed
    page = response.content.decode()
    assert "nu mai poate redeveni „Potențial”" in page
    assert f"/oportunitati/adauga/?contact={opportunity.contact.pk}" in page
    with pytest.raises(ValueError):
        opportunity.change_status(Status.POTENTIAL, seller)


def test_potential_opportunity_offers_every_status(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.get(opportunity.get_absolute_url())

    choices = [value for value, _ in response.context["status_form"].fields["status"].choices]
    assert choices == ["potential", "castigata", "pierduta"]
    assert "Oportunitatea e închisă" not in response.content.decode()


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


def test_lost_saves_the_reason_as_a_note_and_keeps_the_seller(
    seller_client, seller, make_opportunity
):
    opportunity = make_opportunity(seller)

    response = _change_status(seller_client, opportunity, status="pierduta", reason="Prea scump.")

    assert response.url == opportunity.get_absolute_url()
    opportunity.refresh_from_db()
    assert opportunity.status == Status.LOST and opportunity.owner == seller
    # Newest first: the status change, then the reason as an ordinary note.
    change, note = opportunity.notes.all()
    assert change.status_change == "Potențial → Pierdut" and change.text == ""
    assert change.new_status == Status.LOST
    assert note.text == "Prea scump." and note.status_change == "" and note.author == seller
    assert seller_client.get(opportunity.get_absolute_url()).status_code == 200


def test_reason_typed_for_another_status_is_not_kept(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")

    _change_status(
        seller_client, opportunity, status="castigata", camp=camp.pk, reason="Prea scump."
    )

    assert not opportunity.notes.exclude(status_change="").filter(text__gt="").exists()
    assert opportunity.notes.count() == 1


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

    _change_status(seller_client, opportunity, status="pierduta", reason="A renunțat.")

    opportunity.refresh_from_db()
    assert opportunity.status == Status.LOST and opportunity.camp is None


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


def test_seller_adds_task_on_opportunity_for_founder(
    seller_client, seller, founder, make_opportunity
):
    opportunity = make_opportunity(seller)

    response = seller_client.post(
        reverse("oportunitati:task", args=[opportunity.pk]),
        {"title": "Sună joi", "assigned_to": founder.pk, "due_date": "2027-06-01"},
    )

    assert response.url == f"{opportunity.get_absolute_url()}#sarcini"
    task = opportunity.tasks.get()
    assert task.assigned_to == founder and task.created_by == seller
    page = seller_client.get(opportunity.get_absolute_url()).content.decode()
    assert "Sună joi" in page and 'id="sarcini"' in page


def test_opportunity_task_goes_only_to_its_seller_or_a_founder(
    founder_client, seller, other_seller, make_opportunity
):
    opportunity = make_opportunity(seller)

    response = founder_client.post(
        reverse("oportunitati:task", args=[opportunity.pk]),
        {"title": "Sună", "assigned_to": other_seller.pk},
    )

    assert response.context["task_form"].errors["assigned_to"]
    assert not opportunity.tasks.exists()


def test_task_without_title_shows_error(seller_client, seller, make_opportunity):
    opportunity = make_opportunity(seller)

    response = seller_client.post(
        reverse("oportunitati:task", args=[opportunity.pk]), {"assigned_to": seller.pk}
    )

    assert response.status_code == 200
    assert response.context["task_form"].errors["title"]


def test_opportunity_task_toggle(seller_client, seller, make_opportunity):
    task = Task.objects.create(
        opportunity=make_opportunity(seller), title="Sună", assigned_to=seller
    )

    seller_client.post(reverse("oportunitati:task-toggle", args=[task.pk]))

    task.refresh_from_db()
    assert task.done and task.done_at


def test_seller_cannot_add_or_toggle_tasks_on_someone_elses_opportunity(
    seller_client, other_seller, make_opportunity
):
    opportunity = make_opportunity(other_seller)
    task = Task.objects.create(opportunity=opportunity, title="Sună", assigned_to=other_seller)

    add = seller_client.post(reverse("oportunitati:task", args=[opportunity.pk]), {"title": "X"})
    toggle = seller_client.post(reverse("oportunitati:task-toggle", args=[task.pk]))

    assert add.status_code == 404 and toggle.status_code == 404
    task.refresh_from_db()
    assert not task.done


def test_contact_is_chosen_by_typing_not_from_a_list(founder_client, contact):
    Contact = type(contact)
    Contact.objects.bulk_create(Contact(name=f"Ion {number}") for number in range(50))

    empty = founder_client.get(reverse("oportunitati:create")).content.decode()
    chosen = founder_client.get(reverse("oportunitati:create"), {"contact": contact.pk})

    # No <option> per contact: the page stays small however many contacts there are.
    assert "Ion 49" not in empty
    assert 'data-autocomplete="/contacte/cauta/"' in empty
    html = chosen.content.decode()
    assert f'name="contact" id="id_contact" value="{contact.pk}"' in html
    assert 'value="Ana Pop"' in html


def test_autocomplete_never_shows_a_contact_the_seller_cannot_see(
    seller_client, other_seller, contact
):
    contact.assignees.add(other_seller)

    response = seller_client.post(reverse("oportunitati:create"), {"contact": contact.pk})

    assert response.context["form"].errors["contact"]
    assert "Ana Pop" not in response.content.decode()
