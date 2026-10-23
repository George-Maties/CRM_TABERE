from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.oportunitati.models import Task as OpportunityTask
from apps.tabere.models import Camp, Task


def test_wall_shows_my_open_tasks_and_activity(seller_client, seller, founder, make_opportunity):
    opportunity = make_opportunity(seller)
    camp = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    yesterday = timezone.localdate() - timedelta(days=1)
    open_task = Task.objects.create(camp=camp, title="Sună", assigned_to=seller, due_date=yesterday)
    Task.objects.create(camp=camp, title="Gata", assigned_to=seller, done=True)
    Task.objects.create(camp=camp, title="A Paulei", assigned_to=founder)
    opportunity.notes.create(author=seller, text="Am vorbit cu mama.")

    response = seller_client.get(reverse("wall:index"))

    assert list(response.context["camp_tasks"]) == [open_task]
    assert open_task.is_overdue
    assert [note.text for note in response.context["activity"]] == ["Am vorbit cu mama."]


def test_activity_shows_only_the_latest_20(founder_client, founder, make_opportunity):
    opportunity = make_opportunity(founder)
    for number in range(25):
        opportunity.notes.create(author=founder, text=f"Nota {number}")

    activity = founder_client.get(reverse("wall:index")).context["activity"]

    assert [note.text for note in activity] == [f"Nota {n}" for n in range(24, 4, -1)]
    # Older entries are only hidden from the wall: the opportunity keeps its whole history.
    assert opportunity.notes.count() == 25


def test_seller_sees_only_activity_on_their_opportunities(
    client, seller, other_seller, founder, make_opportunity
):
    mine = make_opportunity(seller)
    theirs = make_opportunity(other_seller)
    mine.notes.create(author=seller, text="A mea")
    mine.notes.create(author=founder, text="Paula pe a mea")
    theirs.notes.create(author=other_seller, text="A lui Ion")

    client.force_login(seller)
    seller_page = client.get(reverse("wall:index"))
    client.force_login(founder)
    founder_page = client.get(reverse("wall:index"))

    assert {n.text for n in seller_page.context["activity"]} == {"A mea", "Paula pe a mea"}
    assert {n.text for n in founder_page.context["activity"]} == {
        "A mea",
        "Paula pe a mea",
        "A lui Ion",
    }
    assert "de pe oportunitățile dumneavoastră" in seller_page.content.decode()
    assert "ale echipei" in founder_page.content.decode()


def test_wall_has_three_columns_camp_tasks_opportunity_tasks_activity(
    seller_client, seller, founder, contact, make_opportunity
):
    opportunity = make_opportunity(seller)
    mine = OpportunityTask.objects.create(
        opportunity=opportunity, title="Trimite oferta", assigned_to=seller, created_by=founder
    )
    OpportunityTask.objects.create(
        opportunity=opportunity, title="Gata deja", assigned_to=seller, done=True
    )
    OpportunityTask.objects.create(opportunity=opportunity, title="A Paulei", assigned_to=founder)

    response = seller_client.get(reverse("wall:index"))

    assert list(response.context["opportunity_tasks"]) == [mine]
    page = response.content.decode()
    assert page.index("Sarcini tabere") < page.index("Sarcini oportunități")
    assert page.index("Sarcini oportunități") < page.index("Activitate recentă")
    assert f'href="{opportunity.get_absolute_url()}#sarcini"' in page


def test_wall_groups_tasks_by_camp_and_opportunity(
    seller_client, seller, contact, make_opportunity
):
    soon, later = timezone.localdate(), timezone.localdate() + timedelta(days=5)
    summer = Camp.objects.create(name="Vară 2027", start_date="2027-07-04")
    winter = Camp.objects.create(name="Iarnă 2027", start_date="2027-02-10")
    Task.objects.create(camp=summer, title="Cazare", assigned_to=seller, due_date=later)
    Task.objects.create(camp=winter, title="Instructori", assigned_to=seller, due_date=soon)
    Task.objects.create(camp=summer, title="Autocar", assigned_to=seller)
    opportunity = make_opportunity(seller)
    OpportunityTask.objects.create(opportunity=opportunity, title="Ofertă", assigned_to=seller)
    OpportunityTask.objects.create(opportunity=opportunity, title="Sună", assigned_to=seller)

    response = seller_client.get(reverse("wall:index"))

    camps = [
        (group["label"], [task.title for task in group["tasks"]])
        for group in response.context["camp_task_groups"]
    ]
    # The camp with the most urgent task first; without a deadline comes last.
    assert camps == [("Iarnă 2027", ["Instructori"]), ("Vară 2027", ["Cazare", "Autocar"])]
    [group] = response.context["opportunity_task_groups"]
    assert group["label"] == "Ana Pop" and len(group["tasks"]) == 2
    page = response.content.decode()
    assert page.count('class="task-group"') == 3
    assert page.count('class="task-group-count"') == 2
