# Generated manually on 2026-03-19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_members_adt_alter_members_afm_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoices",
            name="scan_file",
            field=models.FileField(blank=True, null=True, upload_to="invoices/"),
        ),
        migrations.AddField(
            model_name="companies_members",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="companies_members",
            name="active_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="companies_members",
            name="inactive_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="companies_members",
            name="notes",
            field=models.TextField(blank=True, null=True),
        ),
    ]
