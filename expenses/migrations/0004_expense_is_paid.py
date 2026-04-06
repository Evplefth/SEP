from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0003_expenseattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="is_paid",
            field=models.BooleanField(default=False, verbose_name="Πληρωμένο"),
        ),
    ]
