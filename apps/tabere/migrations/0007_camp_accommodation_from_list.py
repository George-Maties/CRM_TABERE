import django.db.models.deletion
from django.db import migrations, models


def to_accommodation_list(apps, schema_editor):
    """Guesthouses typed on camps become entries in the Cazări list (same name and town:
    one entry). Their number of seats is unknown, left at 0 to be filled in."""
    Camp = apps.get_model("tabere", "Camp")
    Accommodation = apps.get_model("cazari", "Accommodation")
    for camp in Camp.objects.exclude(accommodation_name=""):
        camp.accommodation, _ = Accommodation.objects.get_or_create(
            name=camp.accommodation_name.strip(), city=camp.location.strip(), defaults={"capacity": 0}
        )
        camp.save(update_fields=["accommodation"])


def back_to_text(apps, schema_editor):
    Camp = apps.get_model("tabere", "Camp")
    for camp in Camp.objects.exclude(accommodation=None).select_related("accommodation"):
        camp.accommodation_name = camp.accommodation.name
        camp.location = camp.accommodation.city
        camp.save(update_fields=["accommodation_name", "location"])


class Migration(migrations.Migration):

    dependencies = [
        ("cazari", "0001_initial"),
        ("tabere", "0006_child_age_city_medical"),
    ]

    operations = [
        migrations.RenameField(
            model_name="camp", old_name="accommodation", new_name="accommodation_name"
        ),
        migrations.AddField(
            model_name="camp",
            name="accommodation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="camps",
                to="cazari.accommodation",
                verbose_name="cazare",
            ),
        ),
        migrations.RunPython(to_accommodation_list, back_to_text),
        migrations.RemoveField(model_name="camp", name="accommodation_name"),
        migrations.RemoveField(model_name="camp", name="location"),
    ]
