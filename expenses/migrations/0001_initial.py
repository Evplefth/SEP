from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expense_code", models.CharField(max_length=30, unique=True, verbose_name="Κωδικός Εξόδου")),
                ("expense_date", models.DateField(verbose_name="Ημερομηνία")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Ποσό")),
                ("category", models.CharField(choices=[("efka", "Εισφορές ΕΦΚΑ"), ("ofe", "Εισφορές ΟΦΕ"), ("group", "Εισφορές Ομαδικών")], max_length=20, verbose_name="Κατηγορία")),
                ("subcategory", models.CharField(blank=True, choices=[("teka", "ΤΕΚΑ"), ("efka_main", "ΕΦΚΑ"), ("fmy", "Φόρος Μισθωτών Υπηρεσιών")], max_length=20, verbose_name="Υποκατηγορία")),
                ("detail_type", models.CharField(blank=True, choices=[("insurance", "Ασφάλιση"), ("camp", "Παιδικές Κατασκηνώσεις")], max_length=20, verbose_name="Είδος")),
                ("period_month", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Μήνας Περιόδου")),
                ("period_year", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Έτος Περιόδου")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="Περιγραφή")),
                ("notes", models.TextField(blank=True, verbose_name="Σημειώσεις")),
                ("pdf_file", models.FileField(blank=True, null=True, upload_to="expenses/%Y/", verbose_name="PDF")),
                ("active", models.BooleanField(default=True, verbose_name="Ενεργό")),
                ("inactive_date", models.DateField(blank=True, null=True, verbose_name="Ημ. Ανενεργού")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Έξοδο",
                "verbose_name_plural": "Έξοδα",
                "ordering": ["-expense_date", "-id"],
            },
        ),
    ]
