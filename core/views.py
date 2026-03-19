from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from core.models import Banks, Members, nationalities


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
    return render(request, 'core/member_list.html', {'members': members})


@login_required
def member_create(request):
    banks    = Banks.objects.all()
    nat_list = nationalities.objects.all()

    if request.method == 'POST':

        # ── Προσωπικά ───────────────────────────────────────────
        first_name     = request.POST.get('first_name')
        last_name      = request.POST.get('last_name')
        fathers_name   = request.POST.get('fathers_name')
        gender         = request.POST.get('gender')              or None
        date_of_birth  = request.POST.get('date_of_birth')       or None
        nationality_id = request.POST.get('nationality')         or None
        ADT            = request.POST.get('ADT')                 or None
        AFM            = request.POST.get('AFM')                 or None
        AMKA           = request.POST.get('AMKA')                or None
        AMA            = request.POST.get('AMA')                 or None

        # ── Μητρώο ──────────────────────────────────────────────
        mitroo_type            = request.POST.get('mitroo_type')            or None
        mitroo_number          = request.POST.get('mitroo_number')          or None
        date_of_registration   = request.POST.get('date_of_registration')   or None
        date_of_deregistration = request.POST.get('date_of_deregistration') or None

        # ── Οδηγός / Χειριστής ──────────────────────────────────
        driver_A = request.POST.get('driver_A') == 'on'
        driver_B = request.POST.get('driver_B') == 'on'
        driver_C = request.POST.get('driver_C') == 'on'
        driver_D = request.POST.get('driver_D') == 'on'
        lifter   = request.POST.get('lifter')   == 'on'

        # ── Ομαδικό ─────────────────────────────────────────────
        omadiko            = request.POST.get('omadiko')            == 'on'
        omadiko_from       = request.POST.get('omadiko_from')       or None
        omadiko_to         = request.POST.get('omadiko_to')         or None
        omadiko_exartomena = request.POST.get('omadiko_exartomena') == 'on'

        # ── Τράπεζα ─────────────────────────────────────────────
        bank_id             = request.POST.get('bank')                or None
        bank_account_number = request.POST.get('bank_account_number') or None

        # ── Επικοινωνία ─────────────────────────────────────────
        address       = request.POST.get('address')       or None
        tk            = request.POST.get('tk')            or None
        phone_number1 = request.POST.get('phone_number1') or None
        phone_number2 = request.POST.get('phone_number2') or None
        email         = request.POST.get('email')         or None

        # ── Λοιπά ───────────────────────────────────────────────
        notes          = request.POST.get('notes')          or None
        pending_issues = request.POST.get('pending_issues') or None

        # ── Validation ──────────────────────────────────────────
        if not first_name or not last_name or not fathers_name:
            return render(request, 'core/member_add.html', {
                'banks':    banks,
                'nat_list': nat_list,
                'error':    'Παρακαλώ συμπληρώστε όλα τα υποχρεωτικά πεδία.',
            })

        # ── Save ────────────────────────────────────────────────
        member = Members(
            first_name=first_name,
            last_name=last_name,
            fathers_name=fathers_name,
            gender=gender,
            date_of_birth=date_of_birth,
            nationality_id=nationality_id,
            ADT=ADT,
            AFM=AFM,
            AMKA=AMKA,
            AMA=AMA,
            mitroo_type=mitroo_type,
            mitroo_number=mitroo_number,
            date_of_registration=date_of_registration,
            date_of_deregistration=date_of_deregistration,
            driver_A=driver_A,
            driver_B=driver_B,
            driver_C=driver_C,
            driver_D=driver_D,
            lifter=lifter,
            omadiko=omadiko,
            omadiko_from=omadiko_from,
            omadiko_to=omadiko_to,
            omadiko_exartomena=omadiko_exartomena,
            bank_id=bank_id,
            bank_account_number=bank_account_number,
            address=address,
            tk=tk,
            phone_number1=phone_number1,
            phone_number2=phone_number2,
            email=email,
            notes=notes,
            pending_issues=pending_issues,
        )
        member.save()

        messages.success(request, f'Το μέλος {last_name} {first_name} προστέθηκε επιτυχώς.')
        return redirect('core:members_list')

    # GET request
    return render(request, 'core/member_add.html', {
        'banks':    banks,
        'nat_list': nat_list,
    })