from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_insurancecompany_insurancecontract_memberinsurance"),
    ]

    operations = [
        migrations.AddField(
            model_name="companies",
            name="opening_invoice_total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="companies",
            name="opening_payment_total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.CreateModel(
            name="CompanyPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference", models.CharField(blank=True, max_length=100, null=True)),
                ("notes", models.TextField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="core.companies")),
            ],
            options={
                "verbose_name": "Πληρωμή εταιρίας",
                "verbose_name_plural": "Πληρωμές εταιριών",
                "ordering": ["-payment_date", "-id"],
            },
        ),
    ]
