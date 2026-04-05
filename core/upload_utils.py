import os
from pathlib import Path

from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


@deconstructible
class UniqueUploadTo:
    def __init__(self, directory_template):
        self.directory_template = directory_template

    def __call__(self, instance, filename):
        directory = timezone.now().strftime(self.directory_template)

        source_name = Path(filename).name
        stem = Path(source_name).stem
        ext = Path(source_name).suffix.lower()

        safe_stem = slugify(stem, allow_unicode=True) or "file"
        candidate_name = f"{safe_stem}{ext}"
        candidate_path = os.path.join(directory, candidate_name)

        counter = 1
        while default_storage.exists(candidate_path):
            candidate_name = f"{safe_stem}-{counter}{ext}"
            candidate_path = os.path.join(directory, candidate_name)
            counter += 1

        return candidate_path
