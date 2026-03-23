class Protocol(models.Model):
    """
    Αριθμός πρωτοκόλλου — μοναδικός ανά έτος.
    Π.χ.: Πρωτ. 1/2026, 2/2026 … reset στο 1 κάθε 1 Ιανουαρίου.
    """

    # ── Αριθμός / Έτος ──────────────────────────────────────────
    protocol_number = models.PositiveIntegerField(verbose_name="Αριθμός Πρωτοκόλλου")
    year            = models.PositiveIntegerField(verbose_name="Έτος")

    # ── Βασικά Στοιχεία ─────────────────────────────────────────
    date    = models.DateField(verbose_name="Ημερομηνία")
    subject = models.CharField(max_length=500, verbose_name="Θέμα")
    file    = models.FileField(
        upload_to='protocols/%Y/',
        blank=True, null=True,
        verbose_name="Αρχείο"
    )

    # ── Στοιχεία Παραλήπτη ──────────────────────────────────────
    receiver_last_name    = models.CharField(max_length=100, blank=True, verbose_name="Επώνυμο Παραλήπτη")
    receiver_first_name   = models.CharField(max_length=100, blank=True, verbose_name="Όνομα Παραλήπτη")
    receiver_organization = models.CharField(max_length=200, blank=True, verbose_name="Οργανισμός / Υπηρεσία")
    receiver_department   = models.CharField(max_length=200, blank=True, verbose_name="Τμήμα")
    receiver_address      = models.CharField(max_length=255, blank=True, verbose_name="Διεύθυνση")
    receiver_tk           = models.CharField(max_length=10,  blank=True, verbose_name="Τ.Κ.")
    receiver_phone        = models.CharField(max_length=20,  blank=True, verbose_name="Τηλέφωνο")
    receiver_email        = models.EmailField(blank=True,              verbose_name="Email")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Πρωτόκολλο"
        verbose_name_plural = "Πρωτόκολλα"
        ordering            = ['-year', '-protocol_number']
        # ✅ Ο συνδυασμός αριθμός+έτος πρέπει να είναι μοναδικός
        unique_together = ('protocol_number', 'year')

    def __str__(self):
        return f"Πρωτ. {self.protocol_number}/{self.year} — {self.subject[:60]}"

    @property
    def full_number(self):
        return f"{self.protocol_number}/{self.year}"

    @staticmethod
    def next_number(year):
        """Επιστρέφει τον επόμενο διαθέσιμο αριθμό για το δοθέν έτος."""
        from django.db.models import Max
        result = Protocol.objects.filter(year=year).aggregate(Max('protocol_number'))
        last   = result['protocol_number__max']
        return (last or 0) + 1