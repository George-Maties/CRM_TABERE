from django.db import migrations, models


def number_opportunities(apps, schema_editor):
    """Number each contact's opportunities 1, 2, 3… from the oldest."""
    Opportunity = apps.get_model("oportunitati", "Opportunity")
    numbers = {}
    for opportunity in Opportunity.objects.order_by("contact_id", "created_at", "pk"):
        numbers[opportunity.contact_id] = numbers.get(opportunity.contact_id, 0) + 1
        Opportunity.objects.filter(pk=opportunity.pk).update(
            number=numbers[opportunity.contact_id]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("oportunitati", "0003_delete_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="number",
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name="nr."),
            preserve_default=False,
        ),
        migrations.RunPython(number_opportunities, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.UniqueConstraint(
                fields=("contact", "number"), name="unique_opportunity_number_per_contact"
            ),
        ),
        migrations.RemoveField(model_name="opportunity", name="title"),
    ]
