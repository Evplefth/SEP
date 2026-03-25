from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_remove_members_member_registry_number_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="companies_members",
            name="member_registry_number",
        ),
        migrations.AddField(
            model_name="members",
            name="member_registry_number",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                unique=True,
                verbose_name="Αριθμός Βιβλίου Μητρώου Μελών",
            ),
        ),
    ]
