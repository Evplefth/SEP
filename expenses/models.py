from django.core.exceptions import ValidationError
from django.db import models

from core.upload_utils import UniqueUploadTo


class Expense(models.Model):
    CATEGORY_EFKA = "efka"
    CATEGORY_OFE = "ofe"
    CATEGORY_GROUP = "group"

    SUBCATEGORY_TEKA = "teka"
    SUBCATEGORY_EFKA = "efka_main"
    SUBCATEGORY_FMY = "fmy"

    DETAIL_INSURANCE = "insurance"
    DETAIL_CAMP = "camp"

    CATEGORY_CHOICES = [
        (CATEGORY_EFKA, "Εισφορές ΕΦΚΑ"),
        (CATEGORY_OFE, "Εισφορές ΟΦΕ"),
        (CATEGORY_GROUP, "Εισφορές Ομαδικών"),
    ]

    SUBCATEGORY_CHOICES = [
        (SUBCATEGORY_TEKA, "ΤΕΚΑ"),
        (SUBCATEGORY_EFKA, "ΕΦΚΑ"),
        (SUBCATEGORY_FMY, "Φόρος Μισθωτών Υπηρεσιών"),
    ]

    DETAIL_TYPE_CHOICES = [
        (DETAIL_INSURANCE, "Ασφάλιση"),
        (DETAIL_CAMP, "Παιδικές Κατασκηνώσεις"),
    ]

    expense_code = models.CharField(max_length=30, unique=True, verbose_name="Κωδικός Εξόδου")
    expense_date = models.DateField(verbose_name="Ημερομηνία")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Ποσό")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Κατηγορία")
    subcategory = models.CharField(max_length=20, choices=SUBCATEGORY_CHOICES, blank=True, verbose_name="Υποκατηγορία")
    detail_type = models.CharField(max_length=20, choices=DETAIL_TYPE_CHOICES, blank=True, verbose_name="Είδος")
    period_month = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Μήνας Περιόδου")
    period_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Έτος Περιόδου")
    description = models.CharField(max_length=255, blank=True, verbose_name="Περιγραφή")
    notes = models.TextField(blank=True, verbose_name="Σημειώσεις")
    is_paid = models.BooleanField(default=False, verbose_name="Πληρωμένο")
    pdf_file = models.FileField(upload_to=UniqueUploadTo("expenses/%Y/"), blank=True, null=True, verbose_name="PDF")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-id"]
        verbose_name = "Έξοδο"
        verbose_name_plural = "Έξοδα"

    def __str__(self):
        return f"{self.expense_code} - {self.get_category_display()}"

    def clean(self):
        errors = {}

        if self.period_month and not 1 <= self.period_month <= 12:
            errors["period_month"] = "Ο μήνας περιόδου πρέπει να είναι από 1 έως 12."

        if self.category == self.CATEGORY_EFKA:
            if not self.subcategory:
                errors["subcategory"] = "Η υποκατηγορία είναι υποχρεωτική για εισφορές ΕΦΚΑ."
            if self.subcategory == self.SUBCATEGORY_EFKA and not self.detail_type:
                errors["detail_type"] = "Το είδος είναι υποχρεωτικό όταν η υποκατηγορία είναι ΕΦΚΑ."
            if self.subcategory != self.SUBCATEGORY_EFKA:
                self.detail_type = ""
        else:
            self.subcategory = ""
            self.detail_type = ""

        if errors:
            raise ValidationError(errors)

    @property
    def all_pdf_files(self):
        files = []
        if self.pdf_file:
            files.append(
                {
                    "id": f"legacy-{self.pk or 'new'}",
                    "name": self.pdf_file.name.split("/")[-1],
                    "file": self.pdf_file,
                    "is_legacy": True,
                }
            )
        for attachment in self.attachments.all():
            files.append(
                {
                    "id": attachment.id,
                    "name": attachment.filename,
                    "file": attachment.file,
                    "is_legacy": False,
                    "attachment": attachment,
                }
            )
        return files

    @property
    def pdf_count(self):
        return len(self.all_pdf_files)

    @property
    def primary_pdf(self):
        files = self.all_pdf_files
        return files[0] if files else None


class ExpenseAttachment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="attachments", verbose_name="Έξοδο")
    file = models.FileField(upload_to=UniqueUploadTo("expenses/%Y/"), verbose_name="PDF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Συνημμένο Εξόδου"
        verbose_name_plural = "Συνημμένα Εξόδων"

    def __str__(self):
        return f"{self.expense.expense_code} - {self.filename}"

    @property
    def filename(self):
        return self.file.name.split("/")[-1]
