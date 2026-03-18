from django.db import models
from django.core.validators import MinLengthValidator

# Create your models here.


class Banks(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(2)], unique=True)
    
    def __str__(self):
        return self.name


class Members(models.Model):
    # personal info
    first_name = models.CharField(max_length=30, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=30, validators=[MinLengthValidator(2)])
    fathers_name = models.CharField(max_length=30, validators=[MinLengthValidator(2)])
    ADT = models.CharField(max_length=20, validators=[MinLengthValidator(5)], unique=True)
    AFM = models.CharField(max_length=20, validators=[MinLengthValidator(9)], unique=True)
    AMKA = models.CharField(max_length=20, validators=[MinLengthValidator(11)], unique=True)

    #  Mitroo
    mitroo_type = models.CharField(max_length=1, choices=[('A', 'Type A'), ('B', 'Type B')])
    mitroo_number = models.CharField(max_length=20, validators=[MinLengthValidator(5)], unique=True)
    date_of_registration = models.DateField(auto_now_add=True)
    date_of_deregistration = models.DateField(auto_now_add=True)

    #odigos h xeirisths anipsotikou
    driver_A = models.BooleanField(default=False)
    driver_B = models.BooleanField(default=False)
    driver_C = models.BooleanField(default=False)
    driver_D = models.BooleanField(default=False)

    lifter = models.BooleanField(default=False)

    #omadiko
    omadiko_from = models.DateField(blank=True, null=True)
    omadiko_to = models.DateField(blank=True, null=True)

    #bank
    bank = models.ForeignKey(Banks, on_delete=models.SET_NULL, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=False, null=False)

    #stoixei epikoinwnias
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number1 = models.CharField(max_length=20, blank=True, null=True)
    phone_number2 = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    #Παρατηρήσεις & Εκκρεμότητες
    notes = models.TextField(blank=True, null=True)
    pending_issues = models.TextField(blank=True, null=True)



    def __str__(self):
        return self.name