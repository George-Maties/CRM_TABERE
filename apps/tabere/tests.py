from django.urls import reverse

from apps.oportunitati.models import Status

from .models import Camp, Child, Task


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


def test_camp_has_accommodation_and_town(founder_client):
    founder_client.post(
        reverse("tabere:create"),
        {
            "name": "Vară 2027",
            "start_date": "2027-07-04",
            "accommodation": "Pensiunea Bradul",
            "location": "Bran",
        },
    )
    camp = Camp.objects.get()

    detail = founder_client.get(camp.get_absolute_url()).content.decode()
    listing = founder_client.get(reverse("tabere:list")).content.decode()

    assert (camp.accommodation, camp.location) == ("Pensiunea Bradul", "Bran")
    assert "Pensiunea Bradul" in detail and "bi-house-door" in detail
    assert ">Cazare</th>" in listing and "Pensiunea Bradul" in listing
    form = founder_client.get(reverse("tabere:update", args=[camp.pk])).context["form"]
    assert form.fields["location"].label == "Oraș"


def test_age_is_required(seller_client, seller, make_opportunity):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)

    response = seller_client.post(
        reverse("tabere:child-add", args=[opportunity.pk]), {"name": "Matei"}
    )

    assert response.context["child_form"].errors["age"]
    assert not Child.objects.exists()


def test_medical_notes_are_hidden_from_other_sellers(
    client, seller, other_seller, founder, make_opportunity
):
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    opportunity = make_opportunity(seller, status=Status.WON, camp=camp)
    Child.objects.create(
        opportunity=opportunity, name="Matei Pop", age=9, medical_notes="Astm, are inhalator."
    )

    pages = {}
    for user in (seller, other_seller, founder):
        client.force_login(user)
        pages[user] = client.get(camp.get_absolute_url()).content.decode()

    assert "Astm, are inhalator." in pages[seller]
    assert "Astm, are inhalator." in pages[founder]
    # Another seller still sees who comes, not their medical data.
    assert "Matei Pop" in pages[other_seller]
    assert "Astm, are inhalator." not in pages[other_seller]
