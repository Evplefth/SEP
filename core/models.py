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
        verbose_name        = "Ξ•Ο€Ξ±Ο†Ξ® Ξ•Ο„Ξ±ΞΉΟΞµΞ―Ξ±Ο‚"
        verbose_name_plural = "Ξ•Ο€Ξ±Ο†Ξ­Ο‚ Ξ•Ο„Ξ±ΞΉΟΞµΞΉΟΞ½"


class Invoices(models.Model):
    STATUS_CHOICES = [('paid', 'Ξ•ΞΎΞΏΟ†Ξ»Ξ·ΞΌΞ­Ξ½ΞΏ'), ('pending', 'Ξ•ΞΊΞΊΟΞµΞΌΞµΞ―'), ('overdue', 'Ξ›Ξ·ΞΎΞΉΟ€ΟΟΞΈΞµΟƒΞΌΞΏ')]

    invoice_number = models.CharField(max_length=20, unique=True)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    service_type   = models.CharField(max_length=100, blank=True, null=True)
    date_of_issue  = models.DateField()
    status         = models.BooleanField(default=False)
    scan_file      = models.FileField(upload_to='invoices/', blank=True, null=True)
    company        = models.ForeignKey('companies', on_delete=models.CASCADE, related_name='invoices')

    def __str__(self):
        return f"{self.invoice_number} β€” {self.company}"

    class Meta:
        verbose_name        = "Ξ¤ΞΉΞΌΞΏΞ»ΟΞ³ΞΉΞΏ"
        verbose_name_plural = "Ξ¤ΞΉΞΌΞΏΞ»ΟΞ³ΞΉΞ±"
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
        verbose_name        = "Ξ•Ο„Ξ±ΞΉΟΞµΞ―Ξ±"
        verbose_name_plural = "Ξ•Ο„Ξ±ΞΉΟΞµΞ―ΞµΟ‚"
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
        verbose_name        = "Ξ Ξ»Ξ·ΟΟ‰ΞΌΞ® ΞµΟ„Ξ±ΞΉΟΞ―Ξ±Ο‚"
        verbose_name_plural = "Ξ Ξ»Ξ·ΟΟ‰ΞΌΞ­Ο‚ ΞµΟ„Ξ±ΞΉΟΞΉΟΞ½"
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
        verbose_name    = "Ξ‘Ο€Ξ±ΟƒΟ‡ΟΞ»Ξ·ΟƒΞ·"
        unique_together = ('company', 'member')


class Banks(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ξ¤ΟΞ¬Ο€ΞµΞ¶Ξ±"
        verbose_name_plural = "Ξ¤ΟΞ¬Ο€ΞµΞ¶ΞµΟ‚"
        ordering            = ['name']


class Properties(models.Model):
    SIGGENIES_CHOICES = [
        ('syzygos', 'Ξ£ΟΞ¶Ο…Ξ³ΞΏΟ‚'),
        ('tekno',   'Ξ¤Ξ­ΞΊΞ½ΞΏ'),
        ('goneas',  'Ξ“ΞΏΞ½Ξ­Ξ±Ο‚'),
        ('adelfos', 'Ξ‘Ξ΄ΞµΞ»Ο†ΟΟ‚/Ξ®'),
        ('allo',    'Ξ†Ξ»Ξ»ΞΏ'),
    ]
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ξ™Ξ΄ΞΉΟΟ„Ξ·Ο„Ξ± Ξ•ΞΎΞ±ΟΟ„ΟΞΌΞµΞ½ΞΏΟ…"


class Exartomena(models.Model):
    property = models.ForeignKey(Properties, on_delete=models.CASCADE, related_name='exartomena')
    name     = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    member   = models.ForeignKey('Members', on_delete=models.CASCADE, related_name='exartomena')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ξ•ΞΎΞ±ΟΟ„ΟΞΌΞµΞ½ΞΏ"
        verbose_name_plural = "Ξ•ΞΎΞ±ΟΟ„ΟΞΌΞµΞ½Ξ±"


class nationalities(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ξ™ΞΈΞ±Ξ³Ξ­Ξ½ΞµΞΉΞ±"
        verbose_name_plural = "Ξ™ΞΈΞ±Ξ³Ξ­Ξ½ΞµΞΉΞµΟ‚"
        ordering            = ['name']


class Members(models.Model):
    GENDER_CHOICES = [('M', 'Άνδρας'), ('F', 'Γυναίκα')]
    MITROO_CHOICES = [('A', 'Τύπος Α'), ('B', 'Τύπος Β')]

    # β”€β”€ Ξ ΟΞΏΟƒΟ‰Ο€ΞΉΞΊΞ¬ β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    first_name    = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="ΞΞ½ΞΏΞΌΞ±")
    last_name     = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Ξ•Ο€Ξ―ΞΈΞµΟ„ΞΏ")
    fathers_name  = models.CharField(max_length=30, validators=[MinLengthValidator(2)], verbose_name="Ξ Ξ±Ο„ΟΟΞ½Ο…ΞΌΞΏ")
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Φύλο")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Ξ—ΞΌ. Ξ“Ξ­Ξ½Ξ½Ξ·ΟƒΞ·Ο‚")
    nationality   = models.ForeignKey(nationalities, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Ξ™ΞΈΞ±Ξ³Ξ­Ξ½ΞµΞΉΞ±")
    ADT           = models.CharField(max_length=20, unique=True, verbose_name="Ξ‘Ξ”Ξ¤")
    AFM           = models.CharField(max_length=20, unique=True, verbose_name="Ξ‘Ξ¦Ξ")
    AMKA          = models.CharField(max_length=20, unique=True, verbose_name="Ξ‘ΞΞΞ‘")
    AMA           = models.CharField(max_length=20, unique=True, verbose_name="Ξ‘ΞΞ‘")

    # β”€β”€ ΞΞ·Ο„ΟΟΞΏ β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    mitroo_type            = models.CharField(max_length=1, choices=MITROO_CHOICES, blank=True, null=True, verbose_name="Τύπος Μητρώου")
    mitroo_number          = models.PositiveIntegerField(blank=True, null=True, verbose_name="Ξ‘ΟΞΉΞΈΞΌΟΟ‚ ΞΞ·Ο„ΟΟΞΏΟ…")
    date_of_registration   = models.DateField(blank=True, null=True, verbose_name="Ξ—ΞΌ. Ξ•Ξ³Ξ³ΟΞ±Ο†Ξ®Ο‚")
    date_of_deregistration = models.DateField(blank=True, null=True, verbose_name="Ξ—ΞΌ. Ξ›Ξ®ΞΎΞ·Ο‚")

    # β”€β”€ ΞΞ΄Ξ·Ξ³ΟΟ‚ / Ξ§ΞµΞΉΟΞΉΟƒΟ„Ξ®Ο‚ β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    driver_A = models.BooleanField(default=False, verbose_name="Ξ”Ξ―Ο€Ξ»Ο‰ΞΌΞ± Ξ‘")
    driver_B = models.BooleanField(default=False, verbose_name="Ξ”Ξ―Ο€Ξ»Ο‰ΞΌΞ± Ξ’")
    driver_C = models.BooleanField(default=False, verbose_name="Ξ”Ξ―Ο€Ξ»Ο‰ΞΌΞ± Ξ“")
    driver_D = models.BooleanField(default=False, verbose_name="Ξ”Ξ―Ο€Ξ»Ο‰ΞΌΞ± Ξ”")
    lifter   = models.BooleanField(default=False, verbose_name="Ξ§ΞµΞΉΟΞΉΟƒΟ„Ξ®Ο‚ Ξ‘Ξ½Ο…ΟΟ‰Ο„ΞΉΞΊΞΏΟ")

    # β”€β”€ ΞΞΌΞ±Ξ΄ΞΉΞΊΟ β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    omadiko            = models.BooleanField(default=False, verbose_name="ΞΞΌΞ±Ξ΄ΞΉΞΊΟ")
    omadiko_from       = models.DateField(blank=True, null=True, verbose_name="ΞΞΌΞ±Ξ΄ΞΉΞΊΟ Ξ‘Ο€Ο")
    omadiko_to         = models.DateField(blank=True, null=True, verbose_name="ΞΞΌΞ±Ξ΄ΞΉΞΊΟ ΞΟ‰Ο‚")
    omadiko_exartomena = models.BooleanField(default=False, verbose_name="ΞΞΌΞ±Ξ΄ΞΉΞΊΟ Ξ•ΞΎΞ±ΟΟ„ΟΞΌΞµΞ½Ο‰Ξ½")

    # β”€β”€ Ξ¤ΟΞ¬Ο€ΞµΞ¶Ξ± β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    bank                = models.ForeignKey(Banks, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Ξ¤ΟΞ¬Ο€ΞµΞ¶Ξ±")
    bank_account_number = models.CharField(max_length=34, unique=True, null=True, verbose_name="IBAN")

    # β”€β”€ Ξ•Ο€ΞΉΞΊΞΏΞΉΞ½Ο‰Ξ½Ξ―Ξ± β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    address       = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ξ”ΞΉΞµΟΞΈΟ…Ξ½ΟƒΞ·")
    tk            = models.CharField(max_length=10,  blank=True, null=True, verbose_name="Ξ¤Ξ")
    phone_number1 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Ξ¤Ξ·Ξ». 1")
    phone_number2 = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Ξ¤Ξ·Ξ». 2")
    email         = models.EmailField(blank=True, null=True, verbose_name="Email")

    # β”€β”€ Ξ›ΞΏΞΉΟ€Ξ¬ β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€β”€
    notes          = models.TextField(blank=True, null=True, verbose_name="Ξ Ξ±ΟΞ±Ο„Ξ·ΟΞ®ΟƒΞµΞΉΟ‚")
    pending_issues = models.TextField(blank=True, null=True, verbose_name="Ξ•ΞΊΞΊΟΞµΞΌΟΟ„Ξ·Ο„ΞµΟ‚")
    member_registry_number = models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name="Αριθμός Βιβλίου Μητρώου Μελών")

    active        = models.BooleanField(default=True)
    active_date   = models.DateField(auto_now_add=True)
    inactive_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def full_name(self):
        return f"{self.last_name} {self.first_name} Ο„ΞΏΟ… {self.fathers_name}"

    class Meta:
        verbose_name        = "ΞΞ­Ξ»ΞΏΟ‚"
        verbose_name_plural = "ΞΞ­Ξ»Ξ·"
        ordering            = ['last_name', 'first_name']


class MemberFile(models.Model):
    member      = models.ForeignKey(Members, on_delete=models.CASCADE, related_name='files')
    file        = models.FileField(upload_to='members/%Y/', verbose_name="Ξ‘ΟΟ‡ΞµΞ―ΞΏ")
    description = models.CharField(max_length=200, blank=True, verbose_name="Ξ ΞµΟΞΉΞ³ΟΞ±Ο†Ξ®")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} β€” {self.file.name}"

    class Meta:
        verbose_name        = "Ξ‘ΟΟ‡ΞµΞ―ΞΏ ΞΞ­Ξ»ΞΏΟ…Ο‚"
        verbose_name_plural = "Ξ‘ΟΟ‡ΞµΞ―Ξ± ΞΞ­Ξ»ΞΏΟ…Ο‚"
        ordering            = ['-uploaded_at']


# β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•
#  Ξ‘Ξ£Ξ¦Ξ‘Ξ›Ξ™Ξ£Ξ¤Ξ™ΞΞ•Ξ£ Ξ•Ξ¤Ξ‘Ξ™Ξ΅Ξ•Ξ™Ξ•Ξ£ & Ξ£Ξ¥ΞΞ’ΞΞ›Ξ‘Ξ™Ξ‘
# β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•

class InsuranceCompany(models.Model):
    """Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ® ΞµΟ„Ξ±ΞΉΟΞµΞ―Ξ± Ο€ΞΏΟ… ΞµΞΊΞ΄Ξ―Ξ΄ΞµΞΉ ΞΏΞΌΞ±Ξ΄ΞΉΞΊΞ¬ ΟƒΟ…ΞΌΞ²ΟΞ»Ξ±ΞΉΞ±"""
    name           = models.CharField(max_length=200, verbose_name="Ξ•Ο€Ο‰Ξ½Ο…ΞΌΞ―Ξ±")
    address        = models.CharField(max_length=255, blank=True, verbose_name="Ξ”ΞΉΞµΟΞΈΟ…Ξ½ΟƒΞ·")
    phone          = models.CharField(max_length=20,  blank=True, verbose_name="Ξ¤Ξ·Ξ»Ξ­Ο†Ο‰Ξ½ΞΏ")
    email          = models.EmailField(blank=True,              verbose_name="Email")
    contact_person = models.CharField(max_length=150, blank=True, verbose_name="Ξ¥Ο€ΞµΟΞΈΟ…Ξ½ΞΏΟ‚ Ξ•Ο€ΞΉΞΊΞΏΞΉΞ½Ο‰Ξ½Ξ―Ξ±Ο‚")
    notes          = models.TextField(blank=True,              verbose_name="Ξ Ξ±ΟΞ±Ο„Ξ·ΟΞ®ΟƒΞµΞΉΟ‚")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ® Ξ•Ο„Ξ±ΞΉΟΞµΞ―Ξ±"
        verbose_name_plural = "Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ­Ο‚ Ξ•Ο„Ξ±ΞΉΟΞµΞ―ΞµΟ‚"
        ordering            = ['name']


class InsuranceContract(models.Model):
    """ΞΞΌΞ±Ξ΄ΞΉΞΊΟ ΟƒΟ…ΞΌΞ²ΟΞ»Ξ±ΞΉΞΏ β€” ΞΌΞ―Ξ± Ξ±ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ®, Ο€ΞΏΞ»Ξ»Ξ¬ ΞΌΞ­Ξ»Ξ·"""
    company         = models.ForeignKey(
        InsuranceCompany, on_delete=models.CASCADE,
        related_name='contracts', verbose_name="Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ® Ξ•Ο„Ξ±ΞΉΟΞµΞ―Ξ±"
    )
    contract_number = models.CharField(max_length=100, verbose_name="Ξ‘ΟΞΉΞΈΞΌΟΟ‚ Ξ£Ο…ΞΌΞ²ΞΏΞ»Ξ±Ξ―ΞΏΟ…")
    coverage_type   = models.CharField(max_length=200, blank=True, verbose_name="Ξ¤ΟΟ€ΞΏΟ‚ ΞΞ¬Ξ»Ο…ΟΞ·Ο‚")
    amount          = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Ξ ΞΏΟƒΟ Ξ‘ΟƒΟ†Ξ±Ξ»Ξ―ΟƒΟ„ΟΞΏΟ…")
    start_date      = models.DateField(blank=True, null=True, verbose_name="Ξ—ΞΌ. ΞΞ½Ξ±ΟΞΎΞ·Ο‚")
    end_date        = models.DateField(blank=True, null=True, verbose_name="Ξ—ΞΌ. Ξ›Ξ®ΞΎΞ·Ο‚")
    active          = models.BooleanField(default=True, verbose_name="Ξ•Ξ½ΞµΟΞ³Ο")
    notes           = models.TextField(blank=True, verbose_name="Ξ Ξ±ΟΞ±Ο„Ξ·ΟΞ®ΟƒΞµΞΉΟ‚")

    def __str__(self):
        return f"{self.contract_number} β€” {self.company}"

    class Meta:
        verbose_name        = "Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΟ Ξ£Ο…ΞΌΞ²ΟΞ»Ξ±ΞΉΞΏ"
        verbose_name_plural = "Ξ‘ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΞ¬ Ξ£Ο…ΞΌΞ²ΟΞ»Ξ±ΞΉΞ±"
        ordering            = ['-start_date']
        unique_together     = ('company', 'contract_number')


class MemberInsurance(models.Model):
    """Ξ£ΟΞ½Ξ΄ΞµΟƒΞ· ΞΌΞ­Ξ»ΞΏΟ…Ο‚ ΞΌΞµ Ξ±ΟƒΟ†Ξ±Ξ»ΞΉΟƒΟ„ΞΉΞΊΟ ΟƒΟ…ΞΌΞ²ΟΞ»Ξ±ΞΉΞΏ"""
    member              = models.ForeignKey(
        Members, on_delete=models.CASCADE,
        related_name='insurance_contracts', verbose_name="ΞΞ­Ξ»ΞΏΟ‚"
    )
    contract            = models.ForeignKey(
        InsuranceContract, on_delete=models.CASCADE,
        related_name='members', verbose_name="Ξ£Ο…ΞΌΞ²ΟΞ»Ξ±ΞΉΞΏ"
    )
    includes_dependents = models.BooleanField(default=False, verbose_name="Ξ ΞµΟΞΉΞ»Ξ±ΞΌΞ²Ξ¬Ξ½ΞµΞΉ Ξ•ΞΎΞ±ΟΟ„ΟΞΌΞµΞ½Ξ±")

    def __str__(self):
        return f"{self.member} β†’ {self.contract}"

    class Meta:
        verbose_name    = "Ξ‘ΟƒΟ†Ξ¬Ξ»ΞΉΟƒΞ· ΞΞ­Ξ»ΞΏΟ…Ο‚"
        verbose_name_plural = "Ξ‘ΟƒΟ†Ξ±Ξ»Ξ―ΟƒΞµΞΉΟ‚ ΞΞµΞ»ΟΞ½"
        unique_together = ('member', 'contract')


# β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•
#  Ξ Ξ΅Ξ©Ξ¤ΞΞΞΞ›Ξ›Ξ
# β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•β•

class Protocol(models.Model):
    protocol_number = models.PositiveIntegerField(verbose_name="Ξ‘ΟΞΉΞΈΞΌΟΟ‚ Ξ ΟΟ‰Ο„ΞΏΞΊΟΞ»Ξ»ΞΏΟ…")
    year            = models.PositiveIntegerField(verbose_name="ΞΟ„ΞΏΟ‚")

    date    = models.DateField(verbose_name="Ξ—ΞΌΞµΟΞΏΞΌΞ·Ξ½Ξ―Ξ±")
    subject = models.CharField(max_length=500, verbose_name="ΞΞ­ΞΌΞ±")
    file    = models.FileField(upload_to='protocols/%Y/', blank=True, null=True, verbose_name="Ξ‘ΟΟ‡ΞµΞ―ΞΏ")

    sender_last_name    = models.CharField(max_length=100, blank=True, verbose_name="Ξ•Ο€ΟΞ½Ο…ΞΌΞΏ Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_first_name   = models.CharField(max_length=100, blank=True, verbose_name="ΞΞ½ΞΏΞΌΞ± Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_organization = models.CharField(max_length=200, blank=True, verbose_name="ΞΟΞ³Ξ±Ξ½ΞΉΟƒΞΌΟΟ‚ Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_department   = models.CharField(max_length=200, blank=True, verbose_name="Ξ¤ΞΌΞ®ΞΌΞ± Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_address      = models.CharField(max_length=255, blank=True, verbose_name="Ξ”ΞΉΞµΟΞΈΟ…Ξ½ΟƒΞ· Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_tk           = models.CharField(max_length=10,  blank=True, verbose_name="Ξ¤.Ξ. Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_phone        = models.CharField(max_length=20,  blank=True, verbose_name="Ξ¤Ξ·Ξ»Ξ­Ο†Ο‰Ξ½ΞΏ Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")
    sender_email        = models.EmailField(blank=True,              verbose_name="Email Ξ‘Ο€ΞΏΟƒΟ„ΞΏΞ»Ξ­Ξ±")

    receiver_last_name    = models.CharField(max_length=100, blank=True, verbose_name="Ξ•Ο€ΟΞ½Ο…ΞΌΞΏ Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_first_name   = models.CharField(max_length=100, blank=True, verbose_name="ΞΞ½ΞΏΞΌΞ± Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_organization = models.CharField(max_length=200, blank=True, verbose_name="ΞΟΞ³Ξ±Ξ½ΞΉΟƒΞΌΟΟ‚ Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_department   = models.CharField(max_length=200, blank=True, verbose_name="Ξ¤ΞΌΞ®ΞΌΞ± Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_address      = models.CharField(max_length=255, blank=True, verbose_name="Ξ”ΞΉΞµΟΞΈΟ…Ξ½ΟƒΞ· Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_tk           = models.CharField(max_length=10,  blank=True, verbose_name="Ξ¤.Ξ. Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_phone        = models.CharField(max_length=20,  blank=True, verbose_name="Ξ¤Ξ·Ξ»Ξ­Ο†Ο‰Ξ½ΞΏ Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")
    receiver_email        = models.EmailField(blank=True,              verbose_name="Email Ξ Ξ±ΟΞ±Ξ»Ξ®Ο€Ο„Ξ·")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Ξ ΟΟ‰Ο„ΟΞΊΞΏΞ»Ξ»ΞΏ"
        verbose_name_plural = "Ξ ΟΟ‰Ο„ΟΞΊΞΏΞ»Ξ»Ξ±"
        ordering            = ['-year', '-protocol_number']
        unique_together     = ('protocol_number', 'year')

    def __str__(self):
        return f"Ξ ΟΟ‰Ο„. {self.protocol_number}/{self.year} β€” {self.subject[:60]}"

    @property
    def full_number(self):
        return f"{self.protocol_number}/{self.year}"

    @staticmethod
    def next_number(year):
        from django.db.models import Max
        result = Protocol.objects.filter(year=year).aggregate(Max('protocol_number'))
        last   = result['protocol_number__max']
        return (last or 0) + 1

