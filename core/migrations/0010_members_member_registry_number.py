from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_companypayment_active_companypayment_inactive_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="members",
            name="member_registry_number",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name="Αριθμός Βιβλίου Μητρώου Μελών"),
        ),
    ]
