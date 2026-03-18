from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from core.models import Banks, Members

# Create your views here.



def home(request):
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')




@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'core/user_list.html', {'users': users})

@login_required
def member_list(request):
    members = Members.objects.all()
    return render(request,'core/member_list.html', {'members': members})


@login_required
def member_create(request):
    error = None
    banks = Banks.objects.all()

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        fathers_name = request.POST.get('fathers_name')
        ADT = request.POST.get('ADT')
        AFM = request.POST.get('AFM')
        AMKA = request.POST.get('AMKA')
        mitroo_type = request.POST.get('mitroo_type')
        mitroo_number = request.POST.get('mitroo_number')
        date_of_registration = request.POST.get('date_of_registration')
        date_of_deregistration = request.POST.get('date_of_deregistration')
        driver_A = request.POST.get('driver_A') == 'on'
        driver_B = request.POST.get('driver_B') == 'on'
        driver_C = request.POST.get('driver_C') == 'on'
        driver_D = request.POST.get('driver_D') == 'on'
        lifter = request.POST.get('lifter') == 'on'
        omadiko_from = request.POST.get('omadiko_from')
        omadiko_to = request.POST.get('omadiko_to')
        bank_id = request.POST.get('bank')
        bank_account_number = request.POST.get('bank_account_number')
        address = request.POST.get('address')
        phone_number1 = request.POST.get('phone_number1')
        phone_number2 = request.POST.get('phone_number2')
        email = request.POST.get('email')
        notes = request.POST.get('notes')
        pending_issues = request.POST.get('pending_issues')

        # Validate required fields
        if not first_name or not last_name or not fathers_name:
            error = "Παρακαλώ συμπληρώστε όλα τα υποχρεωτικά πεδία."
        else:
            member = Members(
                first_name=first_name,
                last_name=last_name,
                fathers_name=fathers_name,
                ADT=ADT,
                AFM=AFM,
                AMKA=AMKA,
                mitroo_type=mitroo_type,
                mitroo_number=mitroo_number,
                date_of_registration=date_of_registration,
                date_of_deregistration=date_of_deregistration,
                driver_A=driver_A,
                driver_B=driver_B,
                driver_C=driver_C,
                driver_D=driver_D,
                lifter=lifter,
                omadiko_from=omadiko_from,
                omadiko_to=omadiko_to,
                bank_id=bank_id,
                bank_account_number=bank_account_number,
                address=address,
                phone_number1=phone_number1,
                phone_number2=phone_number2,
                email=email,
                notes=notes,
                pending_issues=pending_issues
            )
            member.save()
            return render(request, 'core/member_list.html', {'members': Members.objects.all(), 'success': 'Το μέλος προστέθηκε επιτυχώς.'})

    if error:
        return render(request, 'core/member_add.html', {'error': error})

    return render(request, 'core/member_add.html', {'banks': banks})







