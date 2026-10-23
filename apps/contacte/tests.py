import pytest
from django.urls import reverse

from apps.oportunitati.models import Opportunity

from .models import Contact


@pytest.mark.django_db
def test_user_without_role_cannot_see_contacts(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(username="fara-rol"))

    response = client.get(reverse("contacte:list"))

    assert response.status_code == 403


def test_seller_sees_and_searches_contacts(seller_client, seller, contact):
    contact.assignees.add(seller)
    Contact.objects.create(name="Mihai Popa").assignees.add(seller)

    response = seller_client.get(reverse("contacte:list"), {"q": "ana"})

    assert response.status_code == 200
    assert list(response.context["contact_list"]) == [contact]


def test_seller_adds_contact(seller_client, seller):
    response = seller_client.post(
        reverse("contacte:create"), {"name": "Elena Stan", "kind": "parinte", "phone": "0700"}
    )

    contact = Contact.objects.get(name="Elena Stan")
    assert response.url == contact.get_absolute_url()
    assert contact.created_by == seller
    # What a seller adds is theirs, so it stays in their list.
    assert list(contact.assignees.all()) == [seller]


def test_seller_cannot_delete_contact(seller_client, contact):
    response = seller_client.post(reverse("contacte:delete", args=[contact.pk]))

    assert response.status_code == 403
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_founder_deletes_contact(founder_client, contact):
    response = founder_client.post(reverse("contacte:delete", args=[contact.pk]))

    assert response.url == reverse("contacte:list")
    assert not Contact.objects.filter(pk=contact.pk).exists()


def test_contact_page_lists_only_visible_opportunities(
    seller_client, seller, other_seller, contact, make_opportunity
):
    mine = make_opportunity(seller)
    make_opportunity(other_seller)

    response = seller_client.get(contact.get_absolute_url())

    assert list(response.context["opportunities"]) == [mine]


def test_teacher_is_a_contact_kind(seller_client):
    seller_client.post(reverse("contacte:create"), {"name": "Prof. Ana Vasile", "kind": "profesor"})

    assert Contact.objects.get(name="Prof. Ana Vasile").get_kind_display() == "Profesor"


def test_only_parent_and_teacher_kinds(seller_client):
    assert Contact.Kind.choices == [("parinte", "Părinte"), ("profesor", "Profesor")]

    response = seller_client.post(reverse("contacte:create"), {"name": "Firma X", "kind": "firma"})

    assert response.context["form"].errors["kind"]


def test_contact_filters_are_tabs_with_counts(founder_client, seller, contact):
    teacher = Contact.objects.create(name="Prof. Ion Pop", kind=Contact.Kind.TEACHER)
    teacher.assignees.add(seller)
    Contact.objects.create(name="Mihai Popa", kind=Contact.Kind.TEACHER)

    response = founder_client.get(reverse("contacte:list"), {"tip": "profesor"})

    assert {c.name for c in response.context["contact_list"]} == {"Prof. Ion Pop", "Mihai Popa"}
    kinds = {tab["label"]: tab["count"] for tab in response.context["kind_tabs"]}
    assert kinds == {"Toate": 3, "Părinte": 1, "Profesor": 2}
    # Person tabs count within the chosen kind.
    people = {tab["label"]: tab["count"] for tab in response.context["assignee_tabs"]}
    assert people["Neatribuite"] == 1 and people["vilma"] == 1
    page = response.content.decode()
    assert 'data-auto-search="rezultate"' in page and ">Caută</button>" not in page
    assert 'class="status-tabs-divider"' in page


def test_seller_sees_only_kind_tabs(seller_client, seller, other_seller, contact):
    contact.assignees.add(seller)

    response = seller_client.get(reverse("contacte:list"), {"atribuit": other_seller.pk})

    assert list(response.context["contact_list"]) == [contact]
    assert response.context["assignee_tabs"] == []


def test_seller_sees_only_contacts_assigned_to_them(seller_client, seller, other_seller):
    mine = Contact.objects.create(name="Al meu")
    mine.assignees.add(seller)
    Contact.objects.create(name="Al altcuiva").assignees.add(other_seller)
    Contact.objects.create(name="Neatribuit")

    response = seller_client.get(reverse("contacte:list"))

    assert list(response.context["contact_list"]) == [mine]
    assert "assignable" not in response.context


def test_seller_cannot_open_contact_assigned_to_someone_else(seller_client, other_seller, contact):
    contact.assignees.add(other_seller)

    assert seller_client.get(contact.get_absolute_url()).status_code == 404
    assert seller_client.get(reverse("contacte:update", args=[contact.pk])).status_code == 404


def test_seller_sees_contact_of_their_own_opportunity(
    seller_client, seller, other_seller, contact, make_opportunity
):
    contact.assignees.add(other_seller)
    make_opportunity(seller)

    assert seller_client.get(contact.get_absolute_url()).status_code == 200


def test_founder_sees_all_contacts_and_filters_unassigned(founder_client, seller, contact):
    Contact.objects.create(name="Mihai Popa").assignees.add(seller)

    everyone = founder_client.get(reverse("contacte:list"))
    unassigned = founder_client.get(reverse("contacte:list"), {"atribuit": "nimeni"})
    sellers = founder_client.get(reverse("contacte:list"), {"atribuit": seller.pk})

    assert len(everyone.context["contact_list"]) == 2
    assert list(unassigned.context["contact_list"]) == [contact]
    assert [c.name for c in sellers.context["contact_list"]] == ["Mihai Popa"]


def test_founder_assigns_contacts_in_bulk(founder_client, founder, seller, contact):
    other = Contact.objects.create(name="Mihai Popa")
    opportunity = Opportunity.objects.create(contact=contact, owner=founder)

    response = founder_client.post(
        reverse("contacte:assign"),
        {
            "contacts": [contact.pk, other.pk],
            "assignees": [seller.pk],
            "next": "/contacte/?atribuit=nimeni",
        },
    )

    assert response.url == "/contacte/?atribuit=nimeni"
    assert list(contact.assignees.all()) == [seller]
    assert list(other.assignees.all()) == [seller]
    # Assigning a contact doesn't touch its opportunities.
    opportunity.refresh_from_db()
    assert opportunity.owner == founder


def test_contact_can_have_several_sellers(
    founder_client, seller, other_seller, contact, client, make_opportunity
):
    response = founder_client.post(
        reverse("contacte:assign"),
        {"contacts": [contact.pk], "assignees": [seller.pk, other_seller.pk]},
        follow=True,
    )

    assert set(contact.assignees.all()) == {seller, other_seller}
    assert "Contactul a fost atribuit lui ion și vilma." in response.content.decode()
    client.force_login(other_seller)
    assert list(client.get(reverse("contacte:list")).context["contact_list"]) == [contact]


def test_reassigning_replaces_previous_people(
    founder_client, founder, seller, other_seller, contact
):
    contact.assignees.add(seller)

    founder_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assignees": [other_seller.pk]}
    )

    assert list(contact.assignees.all()) == [other_seller]


def test_assign_list_has_only_founders_and_sellers(
    founder_client, founder, seller, contact, django_user_model
):
    django_user_model.objects.create_superuser(username="nati", password="parola-sigura-123")
    django_user_model.objects.create_user(username="fara-rol")
    django_user_model.objects.create_user(username="plecat", is_active=False).groups.add(
        *seller.groups.all()
    )

    response = founder_client.get(contact.get_absolute_url())

    assert set(response.context["assignable"]) == {founder, seller}
    page = response.content.decode()
    assert "Atribuie" in page and "Modifică" not in page
    assert "Mută și oportunitățile" not in page


def test_assigned_contact_shows_change_button(founder_client, seller, contact):
    contact.assignees.add(seller)

    page = founder_client.get(contact.get_absolute_url()).content.decode()

    assert "Modifică" in page


def test_cannot_assign_to_dev_account(founder_client, contact, django_user_model):
    nati = django_user_model.objects.create_superuser(username="nati", password="parola-123-sigura")

    founder_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assignees": [nati.pk]}
    )

    assert not contact.assignees.exists()


def test_founder_unassigns_contact(founder_client, seller, contact):
    contact.assignees.add(seller)

    founder_client.post(
        reverse("contacte:update", args=[contact.pk]), {"name": contact.name, "kind": "parinte"}
    )

    assert not contact.assignees.exists()


def test_founder_sets_several_assignees_on_edit(founder_client, seller, other_seller, contact):
    response = founder_client.post(
        reverse("contacte:update", args=[contact.pk]),
        {"name": contact.name, "kind": "parinte", "assignees": [seller.pk, other_seller.pk]},
    )

    assert response.url == contact.get_absolute_url()
    assert set(contact.assignees.all()) == {seller, other_seller}


def test_assign_without_selection_shows_error(founder_client, seller):
    response = founder_client.post(
        reverse("contacte:assign"), {"assignees": [seller.pk]}, follow=True
    )

    assert "Selectați cel puțin un contact." in response.content.decode()


def test_assign_without_person_changes_nothing(founder_client, seller, contact):
    contact.assignees.add(seller)

    response = founder_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk]}, follow=True
    )

    assert "Alegeți cui atribuiți contactele." in response.content.decode()
    assert list(contact.assignees.all()) == [seller]


def test_seller_cannot_assign_contacts(seller_client, seller, other_seller, contact):
    contact.assignees.add(seller)

    response = seller_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assignees": [other_seller.pk]}
    )

    assert response.status_code == 403
    assert list(contact.assignees.all()) == [seller]


def test_seller_edit_keeps_assignee(seller_client, seller, contact):
    contact.assignees.add(seller)

    seller_client.post(
        reverse("contacte:update", args=[contact.pk]),
        {"name": "Ana Pop-Ionescu", "kind": "parinte"},
    )

    contact.refresh_from_db()
    assert contact.name == "Ana Pop-Ionescu"
    assert list(contact.assignees.all()) == [seller]
