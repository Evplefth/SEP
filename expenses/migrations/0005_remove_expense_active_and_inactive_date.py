from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0004_expense_is_paid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="expense",
            name="active",
        ),
        migrations.RemoveField(
            model_name="expense",
            name="inactive_date",
        ),
    ]
