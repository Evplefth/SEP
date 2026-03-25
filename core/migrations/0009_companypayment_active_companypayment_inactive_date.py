from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_companypayment_companies_opening_totals"),
    ]

    operations = [
        migrations.AddField(
            model_name="companypayment",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="companypayment",
            name="inactive_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
