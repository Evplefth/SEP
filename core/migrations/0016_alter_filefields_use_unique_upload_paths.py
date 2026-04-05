from django.db import migrations, models

import core.upload_utils


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_backfill_payment_allocations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoices",
            name="scan_file",
            field=models.FileField(blank=True, null=True, upload_to=core.upload_utils.UniqueUploadTo("invoices/%Y/")),
        ),
        migrations.AlterField(
            model_name="memberfile",
            name="file",
            field=models.FileField(upload_to=core.upload_utils.UniqueUploadTo("members/%Y/"), verbose_name="Αρχείο"),
        ),
        migrations.AlterField(
            model_name="protocol",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to=core.upload_utils.UniqueUploadTo("protocols/%Y/"), verbose_name="Αρχείο"),
        ),
    ]
