import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def give_lost_back_to_their_seller(apps, schema_editor):
    """Lost opportunities go back to whoever marked them lost (or worked them before)."""
    Opportunity = apps.get_model("oportunitati", "Opportunity")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    fallback = User.objects.filter(is_superuser=True).order_by("pk").first()
    for opportunity in Opportunity.objects.filter(owner__isnull=True):
        notes = opportunity.notes.exclude(author=None).order_by("-created_at")
        lost_by = notes.filter(new_status="pierduta").first() or notes.first()
        owner_id = lost_by.author_id if lost_by else opportunity.created_by_id
        opportunity.owner_id = owner_id or (fallback and fallback.pk)
        opportunity.save(update_fields=["owner"])


class Migration(migrations.Migration):

    dependencies = [
        ("oportunitati", "0006_note_status_entries"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(give_lost_back_to_their_seller, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="opportunity",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="opportunities",
                to=settings.AUTH_USER_MODEL,
                verbose_name="responsabil",
            ),
        ),
    ]
