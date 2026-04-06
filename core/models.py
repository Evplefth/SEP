from django.db import models
from django.core.validators import MinLengthValidator

from core.upload_utils import UniqueUploadTo


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
        verbose_name        = "Επαφή Εταιρείας"
        verbose_name_plural = "Επαφές Εταιρειών"


class Invoices(models.Model):
    STATUS_CHOICES = [('paid', 'Εξοφλημένο'), ('pending', 'Εκκρεμεί'), ('overdue', 'Ληξιπρόθεσμο')]

    invoice_number = models.CharField(max_length=20, unique=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    service_type   = models.CharField(max_length=100, blank=True, null=True)
    date_of_issue  = models.DateField()
    status         = models.BooleanField(default=False)
    scan_file      = models.FileField(upload_to=UniqueUploadTo('invoices/%Y/'), blank=True, null=True)
    company        = models.ForeignKey('companies', on_delete=models.CASCADE, related_name='invoices')

    def __str__(self):
        return f"{self.invoice_number} — {self.company}"

    class Meta:
        verbose_name        = "Τιμολόγιο"
        verbose_name_plural = "Τιμολόγια"
        ordering            = ['-date_of_issue']


class companies(models.Model):
    name             = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    AFM              = models.CharField(max_length=20, unique=True)
    DOY              = models.CharField(max_length=100, blank=True, null=True)
    address          = models.CharField(max_length=255, blank=True, null=True)
    services         = models.TextField(blank=True, null=True)
    ekremotes_ofiles = models.TextField(blank=True, null=True)
    notes            = models.TextField(blank=True, null=True)
    opening_invoice_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_payment_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active           = models.BooleanField(default=True)
    active_date      = models.DateField(auto_now_add=True)
    inactive_date    = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Εταιρεία"
        verbose_name_plural = "Εταιρείες"
        ordering            = ['name']


class CompanyPayment(models.Model):
    company      = models.ForeignKey('companies', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    reference    = models.CharField(max_length=100, blank=True, null=True)
    notes        = models.TextField(blank=True, null=True)
    active       = models.BooleanField(default=True)
    inactive_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.company} - {self.amount}"

    class Meta:
        verbose_name        = "Πληρωμή εταιρίας"
        verbose_name_plural = "Πληρωμές εταιριών"
        ordering            = ['-payment_date', '-id']


class PaymentAllocation(models.Model):
    payment = models.ForeignKey('CompanyPayment', on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey('Invoices', on_delete=models.CASCADE, related_name='allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('payment', 'invoice')
        ordering = ['invoice__date_of_issue', 'invoice_id', 'payment__payment_date', 'payment_id']


class companies_members(models.Model):
    company       = models.ForeignKey(companies, on_delete=models.CASCADE, related_name='members')
    member        = models.ForeignKey('Members', on_delete=models.CASCADE, related_name='companies')
    active        = models.BooleanField(default=True)
    active_date   = models.DateField(blank=True, null=True)
    inactive_date = models.DateField(blank=True, null=True)
    notes         = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name    = "Απασχόληση"
        unique_together = ('company', 'member')


class Banks(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Τράπεζα"
        verbose_name_plural = "Τράπεζες"
        ordering            = ['name']


class Properties(models.Model):
    SIGGENIES_CHOICES = [
        ('syzygos', 'Σύζυγος'),
        ('tekno',   'Τέκνο'),
        ('goneas',  'Γονέας'),
        ('adelfos', 'Αδελφός/ή'),
        ('allo',    'Άλλο'),
    ]
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
        verbose_name        = "Εξαρτώμενο"
        verbose_name_plural = "Εξαρτώμενα"


class nationalities(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ιθαγένεια"
        verbose_name_plural = "Ιθαγένειες"
        ordering            = ['name']


class Members(models.Model):
    GENDER_CHOICES = [('M', 'Άνδρας'), ('F', 'Γυναίκα')]
    MITROO_CHOICES = [('A', 'Τύπος Α'), ('B', 'Τύπος Β')]
    MEMBER_ROLE_CHOICES = [
        ("president", "ΠΡΟΕΔΡΟΣ"),
        ("vice_president", "ΑΝΤΙΠΡΟΕΔΡΟΣ"),
        ("general_secretary", "ΓΕΝΙΚΟΣ ΓΡΑΜΜΑΤΕΑΣ"),
        ("deputy_general_secretary", "ΑΝ. ΓΕΝ. ΓΡΑΜΜΑΤΕΑΣ"),
        ("treasurer", "ΤΑΜΙΑΣ"),
        ("deputy_treasurer", "ΑΝ. ΤΑΜΙΑΣ"),
        ("board_member", "ΜΕΛΟΣ Δ.Σ."),
        ("advisor", "ΣΥΜΒΟΥΛΟΣ"),
        ("supervisor", "ΕΦΟΡΟΣ"),
        ("member", "ΜΕΛΟΣ"),
    ]

    # ── Προσωπικά ───────────────────────────────────────────────
    first_name    = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Όνομα")
    last_name     = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Επίθετο")
    fathers_name  = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Πατρώνυμο")
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Φύλο")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Ημ. Γέννησης")
    nationality   = models.ForeignKey(nationalities, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Ιθαγένεια")
    member_role   = models.CharField(max_length=40, choices=MEMBER_ROLE_CHOICES, blank=True, null=True, verbose_name="Ιδιότητα")
    ADT           = models.CharField(max_length=20, unique=True, verbose_name="ΑΔΤ")
    AFM           = models.CharField(max_length=20, blank=True, null=True, verbose_name="ΑΦΜ")
    AMKA          = models.CharField(max_length=20, blank=True, null=True, verbose_name="ΑΜΚΑ")
    AMA           = models.CharField(max_length=20, blank=True, null=True, verbose_name="ΑΜΑ")

    # ── Μητρώο ──────────────────────────────────────────────────
    mitroo_type            = models.CharField(max_length=1, choices=MITROO_CHOICES, blank=True, null=True, verbose_name="Τύπος Μητρώου")
    mitroo_number          = models.PositiveIntegerField(blank=True, null=True, verbose_name="Αριθμός Μητρώου")
    date_of_registration   = models.DateField(blank=True, null=True, verbose_name="Ημ. Εγγραφής")
    date_of_deregistration = models.DateField(blank=True, null=True, verbose_name="Ημ. Λήξης")

    # ── Οδηγός / Χειριστής ──────────────────────────────────────
    driver_A = models.BooleanField(default=False, verbose_name="Δίπλωμα Α")
    driver_B = models.BooleanField(default=False, verbose_name="Δίπλωμα Β")
    driver_C = models.BooleanField(default=False, verbose_name="Δίπλωμα Γ")
    driver_D = models.BooleanField(default=False, verbose_name="Δίπλωμα Δ")
    lifter   = models.BooleanField(default=False, verbose_name="Χειριστής Ανυψωτικού")

    # ── Ομαδικό ─────────────────────────────────────────────────
    omadiko            = models.BooleanField(default=False, verbose_name="Ομαδικό")
    omadiko_from       = models.DateField(blank=True, null=True, verbose_name="Ομαδικό Από")
    omadiko_to         = models.DateField(blank=True, null=True, verbose_name="Ομαδικό Έως")
    omadiko_exartomena = models.BooleanField(default=False, verbose_name="Ομαδικό Εξαρτώμενων")

    # ── Τράπεζα ─────────────────────────────────────────────────
    bank                = models.ForeignKey(Banks, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Τράπεζα")
    bank_account_number = models.CharField(max_length=34, unique=True, null=True, verbose_name="IBAN")

    # ── Επικοινωνία ─────────────────────────────────────────────
    address       = models.CharField(max_length=255, blank=True, null=True, verbose_name="Διεύθυνση")
    tk            = models.CharField(max_length=10,  blank=True, null=True, verbose_name="ΤΚ")
    phone_number1 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Τηλ. 1")
    phone_number2 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Τηλ. 2")
    email         = models.EmailField(blank=True, null=True, verbose_name="Email")

    # ── Λοιπά ───────────────────────────────────────────────────
    notes          = models.TextField(blank=True, null=True, verbose_name="Παρατηρήσεις")
    pending_issues = models.TextField(blank=True, null=True, verbose_name="Εκκρεμότητες")
    member_registry_number = models.PositiveIntegerField(blank=True, null=True, verbose_name="Αριθμός Βιβλίου Μητρώου Μελών")

    active        = models.BooleanField(default=True)
    active_date   = models.DateField(auto_now_add=True)
    inactive_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def full_name(self):
        return f"{self.last_name} {self.first_name} του {self.fathers_name}"

    class Meta:
        verbose_name        = "Μέλος"
        verbose_name_plural = "Μέλη"
        ordering            = ['last_name', 'first_name']


class MemberFile(models.Model):
    member      = models.ForeignKey(Members, on_delete=models.CASCADE, related_name='files')
    file        = models.FileField(upload_to='members/%Y/', verbose_name="Αρχείο")
    description = models.CharField(max_length=200, blank=True, verbose_name="Περιγραφή")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} — {self.file.name}"

    class Meta:
        verbose_name        = "Αρχείο Μέλους"
        verbose_name_plural = "Αρχεία Μέλους"
        ordering            = ['-uploaded_at']


# ════════════════════════════════════════════════════════════════
#  ΑΣΦΑΛΙΣΤΙΚΕΣ ΕΤΑΙΡΕΙΕΣ & ΣΥΜΒΟΛΑΙΑ
# ════════════════════════════════════════════════════════════════

class InsuranceCompany(models.Model):
    """Ασφαλιστική εταιρεία που εκδίδει ομαδικά συμβόλαια"""
    name           = models.CharField(max_length=200, verbose_name="Επωνυμία")
    address        = models.CharField(max_length=255, blank=True, verbose_name="Διεύθυνση")
    phone          = models.CharField(max_length=20,  blank=True, verbose_name="Τηλέφωνο")
    email          = models.EmailField(blank=True,              verbose_name="Email")
    contact_person = models.CharField(max_length=150, blank=True, verbose_name="Υπεύθυνος Επικοινωνίας")
    notes          = models.TextField(blank=True,              verbose_name="Παρατηρήσεις")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ασφαλιστική Εταιρεία"
        verbose_name_plural = "Ασφαλιστικές Εταιρείες"
        ordering            = ['name']


class InsuranceContract(models.Model):
    """Ομαδικό συμβόλαιο — μία ασφαλιστική, πολλά μέλη"""
    company         = models.ForeignKey(
        InsuranceCompany, on_delete=models.CASCADE,
        related_name='contracts', verbose_name="Ασφαλιστική Εταιρεία"
    )
    contract_number = models.CharField(max_length=100, verbose_name="Αριθμός Συμβολαίου")
    coverage_type   = models.CharField(max_length=200, blank=True, verbose_name="Τύπος Κάλυψης")
    amount          = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Ποσό Ασφαλίστρου")
    start_date      = models.DateField(blank=True, null=True, verbose_name="Ημ. Έναρξης")
    end_date        = models.DateField(blank=True, null=True, verbose_name="Ημ. Λήξης")
    active          = models.BooleanField(default=True, verbose_name="Ενεργό")
    notes           = models.TextField(blank=True, verbose_name="Παρατηρήσεις")

    def __str__(self):
        return f"{self.contract_number} — {self.company}"

    class Meta:
        verbose_name        = "Ασφαλιστικό Συμβόλαιο"
        verbose_name_plural = "Ασφαλιστικά Συμβόλαια"
        ordering            = ['-start_date']
        unique_together     = ('company', 'contract_number')


class MemberInsurance(models.Model):
    """Σύνδεση μέλους με ασφαλιστικό συμβόλαιο"""
    member              = models.ForeignKey(
        Members, on_delete=models.CASCADE,
        related_name='insurance_contracts', verbose_name="Μέλος"
    )
    contract            = models.ForeignKey(
        InsuranceContract, on_delete=models.CASCADE,
        related_name='members', verbose_name="Συμβόλαιο"
    )
    includes_dependents = models.BooleanField(default=False, verbose_name="Περιλαμβάνει Εξαρτώμενα")

    def __str__(self):
        return f"{self.member} → {self.contract}"

    class Meta:
        verbose_name    = "Ασφάλιση Μέλους"
        verbose_name_plural = "Ασφαλίσεις Μελών"
        unique_together = ('member', 'contract')


# ════════════════════════════════════════════════════════════════
#  ΠΡΩΤΟΚΟΛΛΟ
# ════════════════════════════════════════════════════════════════

class Protocol(models.Model):
    TYPE_INCOMING = "incoming"
    TYPE_OUTGOING = "outgoing"
    TYPE_CHOICES = [
        (TYPE_INCOMING, "Εισερχόμενο"),
        (TYPE_OUTGOING, "Εξερχόμενο"),
    ]

    protocol_number = models.PositiveIntegerField(verbose_name="Αριθμός Πρωτοκόλλου")
    year            = models.PositiveIntegerField(verbose_name="Έτος")

    protocol_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_INCOMING,
        verbose_name="Τύπος Πρωτοκόλλου",
    )
    date    = models.DateField(verbose_name="Ημερομηνία")
    subject = models.CharField(max_length=500, verbose_name="Θέμα")
    file    = models.FileField(upload_to='protocols/%Y/', blank=True, null=True, verbose_name="Αρχείο")

    sender_last_name    = models.CharField(max_length=100, blank=True, verbose_name="Επώνυμο Αποστολέα")
    sender_first_name   = models.CharField(max_length=100, blank=True, verbose_name="Όνομα Αποστολέα")
    sender_organization = models.CharField(max_length=200, blank=True, verbose_name="Οργανισμός Αποστολέα")
    sender_department   = models.CharField(max_length=200, blank=True, verbose_name="Τμήμα Αποστολέα")
    sender_address      = models.CharField(max_length=255, blank=True, verbose_name="Διεύθυνση Αποστολέα")
    sender_tk           = models.CharField(max_length=10,  blank=True, verbose_name="Τ.Κ. Αποστολέα")
    sender_phone        = models.CharField(max_length=20,  blank=True, verbose_name="Τηλέφωνο Αποστολέα")
    sender_email        = models.EmailField(blank=True,              verbose_name="Email Αποστολέα")

    receiver_last_name    = models.CharField(max_length=100, blank=True, verbose_name="Επώνυμο Παραλήπτη")
    receiver_first_name   = models.CharField(max_length=100, blank=True, verbose_name="Όνομα Παραλήπτη")
    receiver_organization = models.CharField(max_length=200, blank=True, verbose_name="Οργανισμός Παραλήπτη")
    receiver_department   = models.CharField(max_length=200, blank=True, verbose_name="Τμήμα Παραλήπτη")
    receiver_address      = models.CharField(max_length=255, blank=True, verbose_name="Διεύθυνση Παραλήπτη")
    receiver_tk           = models.CharField(max_length=10,  blank=True, verbose_name="Τ.Κ. Παραλήπτη")
    receiver_phone        = models.CharField(max_length=20,  blank=True, verbose_name="Τηλέφωνο Παραλήπτη")
    receiver_email        = models.EmailField(blank=True,              verbose_name="Email Παραλήπτη")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Πρωτόκολλο"
        verbose_name_plural = "Πρωτόκολλα"
        ordering            = ['-year', '-protocol_number']
        unique_together     = ('protocol_number', 'year')

    def __str__(self):
        return f"Πρωτ. {self.protocol_number}/{self.year} — {self.subject[:60]}"

    @property
    def full_number(self):
        return f"{self.protocol_number}/{self.year}"

    @staticmethod
    def next_number(year):
        from django.db.models import Max
        result = Protocol.objects.filter(year=year).aggregate(Max('protocol_number'))
        last   = result['protocol_number__max']
        return (last or 0) + 1


class DocumentArchive(models.Model):
    FILE_TYPE_PDF = "pdf"
    FILE_TYPE_EXCEL = "excel"
    FILE_TYPE_WORD = "word"
    FILE_TYPE_CHOICES = [
        (FILE_TYPE_PDF, "PDF"),
        (FILE_TYPE_EXCEL, "Excel"),
        (FILE_TYPE_WORD, "Word"),
    ]

    name = models.CharField(max_length=200, unique=True, verbose_name="Όνομα")
    file_code = models.CharField(max_length=100, blank=True, verbose_name="Κωδικός Αρχείου")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name="Τύπος Αρχείου")
    file = models.FileField(upload_to=UniqueUploadTo('documents/%Y/'), verbose_name="Αρχείο")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Έγγραφο"
        verbose_name_plural = "Έγγραφα"
        ordering = ['name']

