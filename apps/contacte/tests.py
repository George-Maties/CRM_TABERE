import pytest
from django.urls import reverse

from apps.oportunitati.models import Opportunity, Status

from .models import Contact


@pytest.mark.django_db
def test_user_without_role_cannot_see_contacts(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(username="fara-rol"))

    response = client.get(reverse("contacte:list"))

    assert response.status_code == 403


def test_seller_sees_and_searches_contacts(seller_client, seller, contact):
    contact.assigned_to = seller
    contact.save()
    Contact.objects.create(name="Mihai Popa", assigned_to=seller)

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
    assert contact.assigned_to == seller


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


def test_seller_sees_only_contacts_assigned_to_them(seller_client, seller, other_seller):
    mine = Contact.objects.create(name="Al meu", assigned_to=seller)
    Contact.objects.create(name="Al altcuiva", assigned_to=other_seller)
    Contact.objects.create(name="Neatribuit")

    response = seller_client.get(reverse("contacte:list"))

    assert list(response.context["contact_list"]) == [mine]
    assert "assign_form" not in response.context


def test_seller_cannot_open_contact_assigned_to_someone_else(seller_client, other_seller, contact):
    contact.assigned_to = other_seller
    contact.save()

    assert seller_client.get(contact.get_absolute_url()).status_code == 404
    assert seller_client.get(reverse("contacte:update", args=[contact.pk])).status_code == 404


def test_seller_sees_contact_of_their_own_opportunity(
    seller_client, seller, other_seller, contact, make_opportunity
):
    contact.assigned_to = other_seller
    contact.save()
    make_opportunity(seller)

    assert seller_client.get(contact.get_absolute_url()).status_code == 200


def test_founder_sees_all_contacts_and_filters_unassigned(founder_client, seller, contact):
    Contact.objects.create(name="Mihai Popa", assigned_to=seller)

    everyone = founder_client.get(reverse("contacte:list"))
    unassigned = founder_client.get(reverse("contacte:list"), {"atribuit": "nimeni"})
    sellers = founder_client.get(reverse("contacte:list"), {"atribuit": seller.pk})

    assert len(everyone.context["contact_list"]) == 2
    assert list(unassigned.context["contact_list"]) == [contact]
    assert [c.name for c in sellers.context["contact_list"]] == ["Mihai Popa"]


def test_founder_assigns_contacts_in_bulk(founder_client, founder, seller, contact):
    other = Contact.objects.create(name="Mihai Popa")
    open_one = Opportunity.objects.create(contact=contact, title="Vară", owner=founder)
    won = Opportunity.objects.create(
        contact=contact, title="Iarnă", owner=founder, status=Status.WON
    )

    response = founder_client.post(
        reverse("contacte:assign"),
        {
            "contacts": [contact.pk, other.pk],
            "assigned_to": seller.pk,
            "move_opportunities": "on",
            "next": "/contacte/?atribuit=nimeni",
        },
    )

    assert response.url == "/contacte/?atribuit=nimeni"
    assert set(Contact.objects.values_list("assigned_to", flat=True)) == {seller.pk}
    open_one.refresh_from_db()
    won.refresh_from_db()
    # Open opportunities follow the contact; finished ones keep who closed them.
    assert open_one.owner == seller
    assert won.owner == founder


def test_assigning_can_leave_opportunities_where_they_are(founder_client, founder, seller, contact):
    opportunity = Opportunity.objects.create(contact=contact, title="Vară", owner=founder)

    founder_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assigned_to": seller.pk}
    )

    opportunity.refresh_from_db()
    assert opportunity.owner == founder


def test_founder_unassigns_contact(founder_client, seller, contact):
    contact.assigned_to = seller
    contact.save()

    founder_client.post(
        reverse("contacte:update", args=[contact.pk]),
        {"name": contact.name, "kind": "parinte", "assigned_to": ""},
    )

    contact.refresh_from_db()
    assert contact.assigned_to is None


def test_assign_without_selection_shows_error(founder_client, seller):
    response = founder_client.post(
        reverse("contacte:assign"), {"assigned_to": seller.pk}, follow=True
    )

    assert "Selectați cel puțin un contact." in response.content.decode()


def test_assign_without_person_changes_nothing(founder_client, seller, contact):
    contact.assigned_to = seller
    contact.save()

    response = founder_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assigned_to": ""}, follow=True
    )

    assert "Alegeți cui atribuiți contactele." in response.content.decode()
    contact.refresh_from_db()
    assert contact.assigned_to == seller


def test_seller_cannot_assign_contacts(seller_client, seller, other_seller, contact):
    contact.assigned_to = seller
    contact.save()

    response = seller_client.post(
        reverse("contacte:assign"), {"contacts": [contact.pk], "assigned_to": other_seller.pk}
    )

    assert response.status_code == 403
    contact.refresh_from_db()
    assert contact.assigned_to == seller


def test_changing_assignee_on_edit_moves_open_opportunities(
    founder_client, founder, seller, contact
):
    opportunity = Opportunity.objects.create(contact=contact, title="Vară", owner=founder)

    founder_client.post(
        reverse("contacte:update", args=[contact.pk]),
        {"name": contact.name, "kind": "parinte", "assigned_to": seller.pk},
    )

    opportunity.refresh_from_db()
    assert opportunity.owner == seller


def test_seller_edit_keeps_assignee(seller_client, seller, contact):
    contact.assigned_to = seller
    contact.save()

    seller_client.post(
        reverse("contacte:update", args=[contact.pk]),
        {"name": "Ana Pop-Ionescu", "kind": "parinte"},
    )

    contact.refresh_from_db()
    assert contact.name == "Ana Pop-Ionescu"
    assert contact.assigned_to == seller
