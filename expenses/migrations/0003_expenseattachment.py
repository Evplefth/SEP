from django.db import migrations, models

import core.upload_utils


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0002_alter_expense_pdf_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=core.upload_utils.UniqueUploadTo("expenses/%Y/"), verbose_name="PDF")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "expense",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="attachments", to="expenses.expense", verbose_name="Έξοδο"),
                ),
            ],
            options={
                "verbose_name": "Συνημμένο Εξόδου",
                "verbose_name_plural": "Συνημμένα Εξόδων",
                "ordering": ["id"],
            },
        ),
    ]
