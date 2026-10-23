import pytest
from django.urls import reverse

from .models import Contact


@pytest.mark.django_db
def test_user_without_role_cannot_see_contacts(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(username="fara-rol"))

    response = client.get(reverse("contacte:list"))

    assert response.status_code == 403


def test_seller_sees_and_searches_contacts(seller_client, contact):
    Contact.objects.create(name="Mihai Popa")

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
