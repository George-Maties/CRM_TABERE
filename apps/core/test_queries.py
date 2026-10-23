"""Each page runs a fixed number of SQL queries, however many rows it shows: one query per
row (N+1) would make the lists slow as the data grows."""

import pytest
from django.urls import reverse

from apps.cazari.models import Accommodation
from apps.contacte.models import Contact
from apps.oportunitati.models import Opportunity, Status
from apps.oportunitati.models import Task as OpportunityTask
from apps.tabere.models import Camp, Child, Room
from apps.tabere.models import Task as CampTask


@pytest.fixture
def lots(founder, seller):
    """30 contacts with assignees, two opportunities each, notes, children, tasks and rooms."""
    place = Accommodation.objects.create(name="Pensiunea Bradul", city="Bran", capacity=80)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04", accommodation=place)
    room = Room.objects.create(camp=camp, name="Camera 1", capacity=80)
    for number in range(30):
        contact = Contact.objects.create(name=f"Contact {number}", phone="0700")
        contact.assignees.add(seller, founder)
        won = Opportunity.objects.create(
            contact=contact, owner=seller, status=Status.WON, camp=camp, contact_goes=True
        )
        Opportunity.objects.create(contact=contact, owner=seller)
        won.notes.create(author=seller, text="Notă")
        Child.objects.create(opportunity=won, name=f"Copil {number}", age=9, room=room)
        OpportunityTask.objects.create(opportunity=won, title="Sună", assigned_to=founder)
        CampTask.objects.create(camp=camp, title="Pregătește", assigned_to=founder)
    return camp


@pytest.mark.parametrize(
    "url_name, args, most",
    [
        ("wall:index", [], 15),
        ("oportunitati:list", [], 12),
        ("contacte:list", [], 15),
        ("tabere:list", [], 10),
        ("tabere:detail", ["camp"], 15),
        ("tabere:configurator", ["camp"], 12),
        ("tabere:rooms-excel", ["camp"], 10),
        ("cazari:list", [], 8),
    ],
)
def test_pages_run_a_fixed_number_of_queries(
    founder_client, lots, django_assert_max_num_queries, url_name, args, most
):
    url = reverse(url_name, args=[lots.pk for _ in args])

    with django_assert_max_num_queries(most):
        response = founder_client.get(url)

    assert response.status_code == 200


def test_seller_contact_list_runs_a_fixed_number_of_queries(
    seller_client, lots, django_assert_max_num_queries
):
    with django_assert_max_num_queries(12):
        assert seller_client.get(reverse("contacte:list")).status_code == 200
