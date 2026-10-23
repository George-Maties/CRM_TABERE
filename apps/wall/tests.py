from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.oportunitati.models import Task


def test_wall_shows_my_open_tasks_and_activity(seller_client, seller, founder, make_opportunity):
    opportunity = make_opportunity(seller)
    yesterday = timezone.localdate() - timedelta(days=1)
    open_task = Task.objects.create(
        opportunity=opportunity, title="Sună", assigned_to=seller, due_date=yesterday
    )
    Task.objects.create(opportunity=opportunity, title="Gata", assigned_to=seller, done=True)
    Task.objects.create(opportunity=opportunity, title="A Paulei", assigned_to=founder)
    opportunity.notes.create(author=seller, text="Am vorbit cu mama.")

    response = seller_client.get(reverse("wall:index"))

    assert list(response.context["my_tasks"]) == [open_task]
    assert open_task.is_overdue
    assert [note.text for note in response.context["activity"]] == ["Am vorbit cu mama."]
