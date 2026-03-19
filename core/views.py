from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django_countries import countries

from core.models import Banks, Exartomena, Members, Properties, nationalities


def home(request):
    return render(request, "core/index.html")


def _member_form_context(form_data=None, member=None, error=None, existing_exartomena=None):
    return {
        "banks": Banks.objects.all().order_by("name"),
        "properties": Properties.objects.all().order_by("name"),
        "form_data": form_data or {},
        "member": member,
        "error": error,
        "existing_exartomena": existing_exartomena or [],
    }


def _country_code_from_member_nationality(member):
    if not member.nationality:
        return ""

    country_name = member.nationality.name.strip().lower()
    for code, name in countries:
        if name.strip().lower() == country_name:
            return code
    return ""


def _save_exartomena(request, member):
    Exartomena.objects.filter(member=member).delete()

    index = 0
    while True:
        name_key = f"exartomeno_name_{index}"
        property_key = f"exartomeno_property_{index}"

        if name_key not in request.POST and property_key not in request.POST:
            break

        name = (request.POST.get(name_key) or "").strip()
        property_id = request.POST.get(property_key) or None

        if name and property_id:
            Exartomena.objects.create(
                member=member,
                name=name,
                property_id=property_id,
            )

        index += 1


def _posted_exartomena(request):
    rows = []
    index = 0

    while True:
        name_key = f"exartomeno_name_{index}"
        property_key = f"exartomeno_property_{index}"

        if name_key not in request.POST and property_key not in request.POST:
            break

        rows.append(
            {
                "index": index,
                "name": request.POST.get(name_key, ""),
                "property_id": request.POST.get(property_key, ""),
            }
        )
        index += 1

    return rows


def _member_from_post(request, member=None):
    member = member or Members()

    member.first_name = (request.POST.get("first_name") or "").strip()
    member.last_name = (request.POST.get("last_name") or "").strip()
    member.fathers_name = (request.POST.get("fathers_name") or "").strip()
    member.gender = request.POST.get("gender") or None
    member.date_of_birth = request.POST.get("date_of_birth") or None
    nationality_code = request.POST.get("nationality") or None
    if nationality_code:
        country_name = countries.name(nationality_code)
        nationality_obj, _ = nationalities.objects.get_or_create(name=country_name)
        member.nationality = nationality_obj
    else:
        member.nationality = None
    member.ADT = (request.POST.get("ADT") or "").strip()
    member.AFM = (request.POST.get("AFM") or "").strip()
    member.AMKA = (request.POST.get("AMKA") or "").strip()
    member.AMA = (request.POST.get("AMA") or "").strip()

    member.mitroo_type = request.POST.get("mitroo_type") or None
    member.mitroo_number = request.POST.get("mitroo_number") or None
    member.date_of_registration = request.POST.get("date_of_registration") or None
    member.date_of_deregistration = request.POST.get("date_of_deregistration") or None

    member.driver_A = request.POST.get("driver_A") == "on"
    member.driver_B = request.POST.get("driver_B") == "on"
    member.driver_C = request.POST.get("driver_C") == "on"
    member.driver_D = request.POST.get("driver_D") == "on"
    member.lifter = request.POST.get("lifter") == "on"

    member.omadiko = request.POST.get("omadiko") == "on"
    member.omadiko_from = request.POST.get("omadiko_from") or None
    member.omadiko_to = request.POST.get("omadiko_to") or None
    member.omadiko_exartomena = request.POST.get("omadiko_exartomena") == "on"

    member.bank_id = request.POST.get("bank") or None
    member.bank_account_number = (request.POST.get("bank_account_number") or "").strip() or None

    member.address = (request.POST.get("address") or "").strip() or None
    member.tk = (request.POST.get("tk") or "").strip() or None
    member.phone_number1 = (request.POST.get("phone_number1") or "").strip() or None
    member.phone_number2 = (request.POST.get("phone_number2") or "").strip() or None
    member.email = (request.POST.get("email") or "").strip() or None

    member.notes = (request.POST.get("notes") or "").strip() or None
    member.pending_issues = (request.POST.get("pending_issues") or "").strip() or None

    return member


def _validate_member_post(request):
    required_fields = {
        "first_name": "Όνομα",
        "last_name": "Επώνυμο",
        "fathers_name": "Πατρώνυμο",
        "ADT": "ΑΔΤ",
        "AFM": "ΑΦΜ",
        "AMKA": "ΑΜΚΑ",
        "AMA": "ΑΜΑ",
    }

    missing = [
        label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()
    ]

    if missing:
        return f"Συμπλήρωσε τα υποχρεωτικά πεδία: {', '.join(missing)}."

    return None


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")


@login_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "core/user_list.html", {"users": users})


@login_required
def member_list(request):
    members = Members.objects.select_related("nationality", "bank").all()
    query = (request.GET.get("q") or "").strip()
    mitroo = (request.GET.get("mitroo") or "").strip()

    if query:
        members = members.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(fathers_name__icontains=query)
            | Q(ADT__icontains=query)
            | Q(AFM__icontains=query)
            | Q(AMKA__icontains=query)
            | Q(AMA__icontains=query)
            | Q(phone_number1__icontains=query)
            | Q(phone_number2__icontains=query)
            | Q(email__icontains=query)
        )

    if mitroo in {"A", "B"}:
        members = members.filter(mitroo_type=mitroo)

    return render(
        request,
        "core/member_list.html",
        {
            "members": members,
        },
    )


@login_required
def member_create(request):
    if request.method == "POST":
        error = _validate_member_post(request)
        if error:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(request.POST, error=error, existing_exartomena=_posted_exartomena(request)),
            )

        member = _member_from_post(request)

        try:
            member.save()
            _save_exartomena(request, member)
        except IntegrityError:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                request.POST,
                    existing_exartomena=_posted_exartomena(request),
                    error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ ή IBAN.",
                ),
            )

        messages.success(request, f"Το μέλος {member.last_name} {member.first_name} προστέθηκε επιτυχώς.")
        return redirect("core:members_list")

    return render(request, "core/member_add.html", _member_form_context())


@login_required
def member_update(request, member_id):
    member = get_object_or_404(Members, pk=member_id)

    if request.method == "POST":
        error = _validate_member_post(request)
        if error:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    member=member,
                    error=error,
                    existing_exartomena=_posted_exartomena(request),
                ),
            )

        member = _member_from_post(request, member=member)

        try:
            member.save()
            _save_exartomena(request, member)
        except IntegrityError:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    member=member,
                    existing_exartomena=_posted_exartomena(request),
                    error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ ή IBAN.",
                ),
            )

        messages.success(request, f"Το μέλος {member.last_name} {member.first_name} ενημερώθηκε επιτυχώς.")
        return redirect("core:members_list")

    form_data = {
        "first_name": member.first_name,
        "last_name": member.last_name,
        "fathers_name": member.fathers_name,
        "gender": member.gender or "",
        "date_of_birth": member.date_of_birth.isoformat() if member.date_of_birth else "",
        "nationality": _country_code_from_member_nationality(member),
        "ADT": member.ADT,
        "AFM": member.AFM,
        "AMKA": member.AMKA,
        "AMA": member.AMA,
        "mitroo_type": member.mitroo_type or "",
        "mitroo_number": str(member.mitroo_number or ""),
        "date_of_registration": member.date_of_registration.isoformat() if member.date_of_registration else "",
        "date_of_deregistration": member.date_of_deregistration.isoformat() if member.date_of_deregistration else "",
        "driver_A": member.driver_A,
        "driver_B": member.driver_B,
        "driver_C": member.driver_C,
        "driver_D": member.driver_D,
        "lifter": member.lifter,
        "omadiko": member.omadiko,
        "omadiko_from": member.omadiko_from.isoformat() if member.omadiko_from else "",
        "omadiko_to": member.omadiko_to.isoformat() if member.omadiko_to else "",
        "omadiko_exartomena": member.omadiko_exartomena,
        "bank": str(member.bank_id or ""),
        "bank_account_number": member.bank_account_number or "",
        "address": member.address or "",
        "tk": member.tk or "",
        "phone_number1": member.phone_number1 or "",
        "phone_number2": member.phone_number2 or "",
        "email": member.email or "",
        "notes": member.notes or "",
        "pending_issues": member.pending_issues or "",
    }

    existing_exartomena = []
    for index, exartomeno in enumerate(member.exartomena.select_related("property").all()):
        existing_exartomena.append(
            {
                "index": index,
                "name": exartomeno.name,
                "property_id": exartomeno.property_id,
            }
        )

    return render(
        request,
        "core/member_add.html",
        _member_form_context(form_data, member=member, existing_exartomena=existing_exartomena),
    )
