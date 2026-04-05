from django.db import migrations, models

import core.upload_utils


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="pdf_file",
            field=models.FileField(blank=True, null=True, upload_to=core.upload_utils.UniqueUploadTo("expenses/%Y/"), verbose_name="PDF"),
        ),
    ]
