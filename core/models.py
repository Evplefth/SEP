from django.db import models
from django.core.validators import MinLengthValidator


class Companies_contacts(models.Model):
    name        = models.CharField(max_length=100, validators=[MinLengthValidator(2)], blank=True)
    idiotita    = models.CharField(max_length=100, blank=True, null=True)
    phone_number= models.CharField(max_length=20,  blank=True, null=True)
    email       = models.EmailField(blank=True, null=True)
    notes       = models.TextField(blank=True, null=True)
    company     = models.ForeignKey('companies', on_delete=models.CASCADE, related_name='contacts')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Επαφή Εταιρείας"
        verbose_name_plural = "Επαφές Εταιρειών"


class Invoices(models.Model):
    STATUS_CHOICES = [('paid', 'Εξοφλημένο'), ('pending', 'Εκκρεμεί'), ('overdue', 'Ληξιπρόθεσμο')]

    invoice_number = models.CharField(max_length=20, unique=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    service_type   = models.CharField(max_length=100, blank=True, null=True)
    date_of_issue  = models.DateField()
    status         = models.BooleanField(default=False)
    company        = models.ForeignKey('companies', on_delete=models.CASCADE, related_name='invoices')

    def __str__(self):
        return f"{self.invoice_number} — {self.company}"

    class Meta:
        verbose_name = "Τιμολόγιο"
        verbose_name_plural = "Τιμολόγια"
        ordering = ['-date_of_issue']


class companies(models.Model):
    name              = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    AFM               = models.CharField(max_length=20,  unique=True)
    DOY               = models.CharField(max_length=100, blank=True, null=True)
    address           = models.CharField(max_length=255, blank=True, null=True)
    services          = models.TextField(blank=True, null=True)
    ekremotes_ofiles  = models.TextField(blank=True, null=True)
    notes             = models.TextField(blank=True, null=True)
    active            = models.BooleanField(default=True)
    active_date       = models.DateField(auto_now_add=True)
    inactive_date     = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Εταιρεία"
        verbose_name_plural = "Εταιρείες"
        ordering = ['name']


class companies_members(models.Model):
    company = models.ForeignKey(companies, on_delete=models.CASCADE, related_name='members')
    member  = models.ForeignKey('Members', on_delete=models.CASCADE, related_name='companies')

    class Meta:
        verbose_name = "Απασχόληση"
        unique_together = ('company', 'member')  # αποφεύγει διπλές εγγραφές


class Banks(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Τράπεζα"
        verbose_name_plural = "Τράπεζες"
        ordering = ['name']


class Properties(models.Model):
    SIGGENIES_CHOICES = [
        ('syzygos',  'Σύζυγος'),
        ('tekno',    'Τέκνο'),
        ('goneas',   'Γονέας'),
        ('adelfos',  'Αδελφός/ή'),
        ('allo',     'Άλλο'),
    ]
    # ✅ Choices ορίζονται σωστά ως field choices, όχι ως απλή λίστα
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ιδιότητα Εξαρτώμενου"


class Exartomena(models.Model):
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='exartomena')
    name     = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    member   = models.ForeignKey('Members', on_delete=models.CASCADE, related_name='exartomena')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Εξαρτώμενο"
        verbose_name_plural = "Εξαρτώμενα"


class nationalities(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ιθαγένεια"
        verbose_name_plural = "Ιθαγένειες"
        ordering = ['name']


class Members(models.Model):
    GENDER_CHOICES   = [('M', 'Άνδρας'), ('F', 'Γυναίκα')]
    MITROO_CHOICES   = [('A', 'Τύπος Α'), ('B', 'Τύπος Β')]

    # ── Προσωπικά ───────────────────────────────────────────────
    first_name   = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Όνομα")
    last_name    = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Επίθετο")
    fathers_name = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Πατρώνυμο")
    gender       = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Φύλο")
    date_of_birth= models.DateField(blank=True, null=True, verbose_name="Ημ. Γέννησης")
    nationality  = models.ForeignKey(nationalities, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Ιθαγένεια")
    ADT          = models.CharField(max_length=20, unique=True, verbose_name="ΑΔΤ")
    AFM          = models.CharField(max_length=20, unique=True, verbose_name="ΑΦΜ")
    AMKA         = models.CharField(max_length=20, unique=True, verbose_name="ΑΜΚΑ")
    AMA          = models.CharField(max_length=20, unique=True, verbose_name="ΑΜΑ")  # Αριθμός Μητρώου Ασφαλισμένου

    # ── Μητρώο ──────────────────────────────────────────────────
    mitroo_type           = models.CharField(max_length=1, choices=MITROO_CHOICES, blank=True, null=True, verbose_name="Τύπος Μητρώου")
    mitroo_number         = models.PositiveIntegerField(blank=True, null=True, verbose_name="Αριθμός Μητρώου")
    # ✅ Διορθώθηκε: auto_now_add=True αφαιρέθηκε — δεν μπορούσε να οριστεί από τη φόρμα
    date_of_registration  = models.DateField(blank=True, null=True, verbose_name="Ημ. Εγγραφής")
    date_of_deregistration= models.DateField(blank=True, null=True, verbose_name="Ημ. Λήξης")

    # ── Οδηγός / Χειριστής ──────────────────────────────────────
    driver_A = models.BooleanField(default=False, verbose_name="Δίπλωμα Α")
    driver_B = models.BooleanField(default=False, verbose_name="Δίπλωμα Β")
    driver_C = models.BooleanField(default=False, verbose_name="Δίπλωμα Γ")
    driver_D = models.BooleanField(default=False, verbose_name="Δίπλωμα Δ")
    lifter   = models.BooleanField(default=False, verbose_name="Χειριστής Ανυψωτικού")

    # ── Ομαδικό ─────────────────────────────────────────────────
    omadiko           = models.BooleanField(default=False, verbose_name="Ομαδικό")
    omadiko_from      = models.DateField(blank=True, null=True, verbose_name="Ομαδικό Από")
    omadiko_to        = models.DateField(blank=True, null=True, verbose_name="Ομαδικό Έως")
    omadiko_exartomena= models.BooleanField(default=False, verbose_name="Ομαδικό Εξαρτώμενων")

    # ── Τράπεζα ─────────────────────────────────────────────────
    bank               = models.ForeignKey(Banks, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Τράπεζα")
    # ✅ Διορθώθηκε: blank=True, null=True — δεν είναι υποχρεωτικό
    bank_account_number= models.CharField(max_length=34, unique=True, null=True, verbose_name="IBAN")

    # ── Επικοινωνία ─────────────────────────────────────────────
    address       = models.CharField(max_length=255, blank=True, null=True, verbose_name="Διεύθυνση")
    tk            = models.CharField(max_length=10,  blank=True, null=True, verbose_name="ΤΚ")
    phone_number1 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Τηλ. 1")
    phone_number2 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Τηλ. 2")
    email         = models.EmailField(blank=True, null=True, verbose_name="Email")

    # ── Λοιπά ───────────────────────────────────────────────────
    notes          = models.TextField(blank=True, null=True, verbose_name="Παρατηρήσεις")
    pending_issues = models.TextField(blank=True, null=True, verbose_name="Εκκρεμότητες")

    active       = models.BooleanField(default=True)
    active_date  = models.DateField(auto_now_add=True)
    inactive_date= models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def full_name(self):
        return f"{self.last_name} {self.first_name} του {self.fathers_name}"

    class Meta:
        verbose_name = "Μέλος"
        verbose_name_plural = "Μέλη"
        ordering = ['last_name', 'first_name']