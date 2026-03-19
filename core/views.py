import re
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.static import serve
from django_countries import countries

from core.models import (
    Banks,
    Exartomena,
    Invoices,
    Members,
    Properties,
    companies,
    companies_members,
    nationalities,
)


def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return redirect("login")


@login_required
@xframe_options_exempt
def media_preview(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT, show_indexes=False)


def _extract_row_indexes(data, prefixes):
    indexes = set()
    pattern = re.compile(r"_(\d+)$")

    for key in data.keys():
        if any(key.startswith(prefix) for prefix in prefixes):
            match = pattern.search(key)
            if match:
                indexes.add(int(match.group(1)))

    return sorted(indexes)


def _country_code_from_member_nationality(member):
    if not member.nationality:
        return ""

    country_name = member.nationality.name.strip().lower()
    for code, name in countries:
        if name.strip().lower() == country_name:
            return code
    return ""


def _member_form_context(form_data=None, member=None, error=None, existing_exartomena=None, existing_companies=None):
    return {
        "banks": Banks.objects.all().order_by("name"),
        "properties": Properties.objects.all().order_by("name"),
        "all_companies": companies.objects.order_by("name"),
        "form_data": form_data or {},
        "member": member,
        "error": error,
        "existing_exartomena": existing_exartomena or [],
        "existing_companies": existing_companies or [],
    }


def _company_form_context(form_data=None, company=None, error=None, existing_invoices=None):
    return {
        "form_data": form_data or {},
        "company": company,
        "error": error,
        "existing_invoices": existing_invoices or [],
    }


def _invoice_form_context(form_data=None, invoice=None, error=None):
    return {
        "form_data": form_data or {},
        "invoice": invoice,
        "companies": companies.objects.order_by("name"),
        "error": error,
    }


def _posted_exartomena(request):
    rows = []
    for index in _extract_row_indexes(request.POST, ["exartomeno_name_", "exartomeno_property_"]):
        rows.append(
            {
                "index": index,
                "name": request.POST.get(f"exartomeno_name_{index}", ""),
                "property_id": request.POST.get(f"exartomeno_property_{index}", ""),
            }
        )
    return rows


def _posted_member_companies(request):
    rows = []
    for index in _extract_row_indexes(
        request.POST,
        ["company_id_", "company_active_", "company_active_date_", "company_inactive_date_", "company_notes_"],
    ):
        rows.append(
            {
                "index": index,
                "company_id": request.POST.get(f"company_id_{index}", ""),
                "active": request.POST.get(f"company_active_{index}") == "on",
                "active_date": request.POST.get(f"company_active_date_{index}", ""),
                "inactive_date": request.POST.get(f"company_inactive_date_{index}", ""),
                "notes": request.POST.get(f"company_notes_{index}", ""),
            }
        )
    return rows


def _posted_invoices(request):
    rows = []
    indexes = sorted(
        set(_extract_row_indexes(request.POST, ["invoice_"]) + _extract_row_indexes(request.FILES, ["invoice_scan_file_"]))
    )
    for index in indexes:
        rows.append(
            {
                "index": index,
                "invoice_id": request.POST.get(f"invoice_id_{index}", ""),
                "invoice_number": request.POST.get(f"invoice_number_{index}", ""),
                "amount": request.POST.get(f"invoice_amount_{index}", ""),
                "service_type": request.POST.get(f"invoice_service_type_{index}", ""),
                "date_of_issue": request.POST.get(f"invoice_date_of_issue_{index}", ""),
                "status": request.POST.get(f"invoice_status_{index}") == "on",
                "scan_file": request.FILES.get(f"invoice_scan_file_{index}"),
                "scan_name": request.POST.get(f"invoice_existing_scan_{index}", ""),
            }
        )
    return rows


def _save_exartomena(request, member):
    Exartomena.objects.filter(member=member).delete()

    for row in _posted_exartomena(request):
        name = (row["name"] or "").strip()
        property_id = row["property_id"] or None
        if name and property_id:
            Exartomena.objects.create(member=member, name=name, property_id=property_id)


def _save_member_companies(request, member):
    companies_members.objects.filter(member=member).delete()

    for row in _posted_member_companies(request):
        company_id = row["company_id"] or None
        if not company_id:
            continue

        active = row["active"]
        active_date = row["active_date"] or (date.today().isoformat() if active else None)
        inactive_date = row["inactive_date"] or (None if active else date.today().isoformat())

        companies_members.objects.create(
            member=member,
            company_id=company_id,
            active=active,
            active_date=active_date,
            inactive_date=inactive_date,
            notes=(row["notes"] or "").strip() or None,
        )


def _save_company_invoices(request, company):
    keep_ids = []

    for row in _posted_invoices(request):
        invoice_number = (row["invoice_number"] or "").strip()
        amount = row["amount"] or None
        date_of_issue = row["date_of_issue"] or None

        if not invoice_number or not amount or not date_of_issue:
            continue

        invoice_id = row["invoice_id"] or None
        if invoice_id:
            invoice = Invoices.objects.filter(pk=invoice_id, company=company).first()
            if not invoice:
                invoice = Invoices(company=company)
        else:
            invoice = Invoices(company=company)

        invoice.invoice_number = invoice_number
        invoice.amount = amount
        invoice.service_type = (row["service_type"] or "").strip() or None
        invoice.date_of_issue = date_of_issue
        invoice.status = row["status"]
        if row["scan_file"]:
            invoice.scan_file = row["scan_file"]
        invoice.save()
        keep_ids.append(invoice.id)

    Invoices.objects.filter(company=company).exclude(id__in=keep_ids).delete()


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

    member.active = request.POST.get("active") == "on"
    member.inactive_date = request.POST.get("inactive_date") or None
    if member.active:
        member.inactive_date = None

    return member


def _company_from_post(request, company=None):
    company = company or companies()
    company.name = (request.POST.get("name") or "").strip()
    company.AFM = (request.POST.get("AFM") or "").strip()
    company.DOY = (request.POST.get("DOY") or "").strip() or None
    company.address = (request.POST.get("address") or "").strip() or None
    company.services = (request.POST.get("services") or "").strip() or None
    company.ekremotes_ofiles = (request.POST.get("ekremotes_ofiles") or "").strip() or None
    company.notes = (request.POST.get("notes") or "").strip() or None
    company.active = request.POST.get("active") == "on"
    company.inactive_date = request.POST.get("inactive_date") or None
    if company.active:
        company.inactive_date = None
    return company


def _invoice_from_post(request, invoice=None):
    invoice = invoice or Invoices()
    invoice.company_id = request.POST.get("company") or None
    invoice.invoice_number = (request.POST.get("invoice_number") or "").strip()
    invoice.amount = request.POST.get("amount") or None
    invoice.service_type = (request.POST.get("service_type") or "").strip() or None
    invoice.date_of_issue = request.POST.get("date_of_issue") or None
    invoice.status = request.POST.get("status") == "on"
    if request.FILES.get("scan_file"):
        invoice.scan_file = request.FILES["scan_file"]
    return invoice


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
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπλήρωσε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _find_member_duplicate(member):
    unique_fields = {
        "ADT": "ΑΔΤ",
        "AFM": "ΑΦΜ",
        "AMKA": "ΑΜΚΑ",
        "AMA": "ΑΜΑ",
        "bank_account_number": "IBAN",
    }

    for field, label in unique_fields.items():
        value = getattr(member, field, None)
        if not value:
            continue

        qs = Members.objects.filter(**{field: value})
        if member.pk:
            qs = qs.exclude(pk=member.pk)
        if qs.exists():
            return label

    return None


def _validate_company_post(request):
    required_fields = {
        "name": "Επωνυμία",
        "AFM": "ΑΦΜ",
    }
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπλήρωσε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _validate_invoice_post(request):
    required_fields = {
        "company": "Εταιρία",
        "invoice_number": "Αριθμός τιμολογίου",
        "amount": "Ποσό",
        "date_of_issue": "Ημερομηνία έκδοσης",
    }
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπλήρωσε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _find_invoice_duplicate(invoice):
    qs = Invoices.objects.filter(invoice_number=invoice.invoice_number)
    if invoice.pk:
        qs = qs.exclude(pk=invoice.pk)
    return qs.exists()


@login_required
def dashboard(request):
    return render(
        request,
        "core/dashboard.html",
        {
            "members_count": Members.objects.count(),
            "companies_count": companies.objects.count(),
            "invoices_count": Invoices.objects.count(),
        },
    )


@login_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "core/user_list.html", {"users": users})


@login_required
def user_create(request):
    if not request.user.is_staff:
        messages.error(request, "Μόνο χρήστες με staff δικαιώματα μπορούν να δημιουργούν νέους χρήστες.")
        return redirect("core:users")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        is_staff = request.POST.get("is_staff") == "on"

        if not username or not password1:
            return render(request, "core/user_add.html", {"error": "Το username και ο κωδικός είναι υποχρεωτικά."})
        if password1 != password2:
            return render(request, "core/user_add.html", {"error": "Οι δύο κωδικοί δεν ταιριάζουν."})
        if User.objects.filter(username=username).exists():
            return render(request, "core/user_add.html", {"error": "Υπάρχει ήδη χρήστης με αυτό το username."})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
        )
        messages.success(request, f"Ο χρήστης {user.username} δημιουργήθηκε επιτυχώς.")
        return redirect("core:users")

    return render(request, "core/user_add.html")


@login_required
def member_list(request):
    members = Members.objects.select_related("nationality", "bank").prefetch_related("companies__company").all()
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

    return render(request, "core/member_list.html", {"members": members})


@login_required
def member_detail(request, member_id):
    member = get_object_or_404(
        Members.objects.select_related("nationality", "bank").prefetch_related("companies__company", "exartomena__property"),
        pk=member_id,
    )
    company_links = member.companies.select_related("company").all().order_by("-active", "company__name")
    return render(
        request,
        "core/member_detail.html",
        {
            "member": member,
            "company_links": company_links,
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
                _member_form_context(
                    request.POST,
                    error=error,
                    existing_exartomena=_posted_exartomena(request),
                    existing_companies=_posted_member_companies(request),
                ),
            )

        member = _member_from_post(request)
        duplicate_label = _find_member_duplicate(member)
        if duplicate_label:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    error=f"Υπάρχει ήδη μέλος με ίδιο {duplicate_label}.",
                    existing_exartomena=_posted_exartomena(request),
                    existing_companies=_posted_member_companies(request),
                ),
            )

        try:
            member.save()
            _save_exartomena(request, member)
            _save_member_companies(request, member)
        except IntegrityError:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ ή IBAN.",
                    existing_exartomena=_posted_exartomena(request),
                    existing_companies=_posted_member_companies(request),
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
                    existing_companies=_posted_member_companies(request),
                ),
            )

        member = _member_from_post(request, member=member)
        duplicate_label = _find_member_duplicate(member)
        if duplicate_label:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    member=member,
                    error=f"Υπάρχει ήδη μέλος με ίδιο {duplicate_label}.",
                    existing_exartomena=_posted_exartomena(request),
                    existing_companies=_posted_member_companies(request),
                ),
            )

        try:
            member.save()
            _save_exartomena(request, member)
            _save_member_companies(request, member)
        except IntegrityError:
            return render(
                request,
                "core/member_add.html",
                _member_form_context(
                    request.POST,
                    member=member,
                    error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ ή IBAN.",
                    existing_exartomena=_posted_exartomena(request),
                    existing_companies=_posted_member_companies(request),
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
        "active": member.active,
        "inactive_date": member.inactive_date.isoformat() if member.inactive_date else "",
    }

    existing_exartomena = [
        {"index": index, "name": ex.name, "property_id": ex.property_id}
        for index, ex in enumerate(member.exartomena.select_related("property").all())
    ]

    existing_companies = [
        {
            "index": index,
            "company_id": link.company_id,
            "active": link.active,
            "active_date": link.active_date.isoformat() if link.active_date else "",
            "inactive_date": link.inactive_date.isoformat() if link.inactive_date else "",
            "notes": link.notes or "",
        }
        for index, link in enumerate(member.companies.select_related("company").all())
    ]

    return render(
        request,
        "core/member_add.html",
        _member_form_context(
            form_data,
            member=member,
            existing_exartomena=existing_exartomena,
            existing_companies=existing_companies,
        ),
    )


@login_required
def company_list(request):
    company_qs = companies.objects.prefetch_related("invoices").all()
    query = (request.GET.get("q") or "").strip()
    if query:
        company_qs = company_qs.filter(Q(name__icontains=query) | Q(AFM__icontains=query) | Q(DOY__icontains=query))
    return render(request, "core/company_list.html", {"companies": company_qs})


@login_required
def company_detail(request, company_id):
    company = get_object_or_404(companies, pk=company_id)
    invoices_qs = company.invoices.all().order_by("-date_of_issue", "-id")

    status_filter = (request.GET.get("status") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    invoice_query = (request.GET.get("q") or "").strip()

    filters_applied = any([status_filter, date_from, date_to, invoice_query])

    if invoice_query:
        invoices_qs = invoices_qs.filter(
            Q(invoice_number__icontains=invoice_query) | Q(service_type__icontains=invoice_query)
        )
    if status_filter in {"paid", "pending"}:
        invoices_qs = invoices_qs.filter(status=(status_filter == "paid"))
    if date_from:
        invoices_qs = invoices_qs.filter(date_of_issue__gte=date_from)
    if date_to:
        invoices_qs = invoices_qs.filter(date_of_issue__lte=date_to)
    if not filters_applied:
        invoices_qs = invoices_qs[:3]

    company_members = company.members.select_related("member").all().order_by("-active", "member__last_name")

    return render(
        request,
        "core/company_detail.html",
        {
            "company": company,
            "invoices": invoices_qs,
            "company_members": company_members,
            "filters_applied": filters_applied,
        },
    )


@login_required
def company_create(request):
    if request.method == "POST":
        error = _validate_company_post(request)
        if error:
            return render(
                request,
                "core/company_add.html",
                _company_form_context(request.POST, error=error, existing_invoices=_posted_invoices(request)),
            )

        company = _company_from_post(request)
        try:
            company.save()
            _save_company_invoices(request, company)
        except IntegrityError:
            return render(
                request,
                "core/company_add.html",
                _company_form_context(
                    request.POST,
                    error="Υπάρχει ήδη εταιρία με ίδιο ΑΦΜ ή τιμολόγιο με ίδιο αριθμό.",
                    existing_invoices=_posted_invoices(request),
                ),
            )

        messages.success(request, f"Η εταιρία {company.name} προστέθηκε επιτυχώς.")
        return redirect("core:companies_list")

    return render(request, "core/company_add.html", _company_form_context())


@login_required
def company_update(request, company_id):
    company = get_object_or_404(companies, pk=company_id)

    if request.method == "POST":
        error = _validate_company_post(request)
        if error:
            return render(
                request,
                "core/company_add.html",
                _company_form_context(
                    request.POST,
                    company=company,
                    error=error,
                    existing_invoices=_posted_invoices(request),
                ),
            )

        company = _company_from_post(request, company=company)
        try:
            company.save()
            _save_company_invoices(request, company)
        except IntegrityError:
            return render(
                request,
                "core/company_add.html",
                _company_form_context(
                    request.POST,
                    company=company,
                    error="Υπάρχει ήδη εταιρία με ίδιο ΑΦΜ ή τιμολόγιο με ίδιο αριθμό.",
                    existing_invoices=_posted_invoices(request),
                ),
            )

        messages.success(request, f"Η εταιρία {company.name} ενημερώθηκε επιτυχώς.")
        return redirect("core:companies_list")

    form_data = {
        "name": company.name,
        "AFM": company.AFM,
        "DOY": company.DOY or "",
        "address": company.address or "",
        "services": company.services or "",
        "ekremotes_ofiles": company.ekremotes_ofiles or "",
        "notes": company.notes or "",
        "active": company.active,
        "inactive_date": company.inactive_date.isoformat() if company.inactive_date else "",
    }

    existing_invoices = [
        {
            "index": index,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": invoice.amount,
            "service_type": invoice.service_type or "",
            "date_of_issue": invoice.date_of_issue.isoformat() if invoice.date_of_issue else "",
            "status": invoice.status,
            "scan_name": invoice.scan_file.name if invoice.scan_file else "",
            "scan_url": reverse("core:media_preview", args=[invoice.scan_file.name]) if invoice.scan_file else "",
        }
        for index, invoice in enumerate(company.invoices.all())
    ]

    return render(
        request,
        "core/company_add.html",
        _company_form_context(form_data, company=company, existing_invoices=existing_invoices),
    )


@login_required
def invoice_list(request):
    invoices = Invoices.objects.select_related("company").all().order_by("-date_of_issue", "-id")
    company_id = (request.GET.get("company") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    query = (request.GET.get("q") or "").strip()

    if company_id:
        invoices = invoices.filter(company_id=company_id)
    if status_filter in {"paid", "pending"}:
        invoices = invoices.filter(status=(status_filter == "paid"))
    if query:
        invoices = invoices.filter(Q(invoice_number__icontains=query) | Q(service_type__icontains=query))

    return render(
        request,
        "core/invoice_list.html",
        {
            "invoices": invoices,
            "companies": companies.objects.order_by("name"),
        },
    )


@login_required
def invoice_create(request):
    if request.method == "POST":
        error = _validate_invoice_post(request)
        if error:
            return render(request, "core/invoice_add.html", _invoice_form_context(request.POST, error=error))

        invoice = _invoice_from_post(request)
        if _find_invoice_duplicate(invoice):
            return render(
                request,
                "core/invoice_add.html",
                _invoice_form_context(request.POST, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."),
            )
        try:
            invoice.save()
        except IntegrityError:
            return render(
                request,
                "core/invoice_add.html",
                _invoice_form_context(request.POST, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."),
            )

        messages.success(request, f"Το τιμολόγιο {invoice.invoice_number} προστέθηκε επιτυχώς.")
        return redirect("core:invoices_list")

    return render(request, "core/invoice_add.html", _invoice_form_context())


@login_required
def invoice_update(request, invoice_id):
    invoice = get_object_or_404(Invoices.objects.select_related("company"), pk=invoice_id)

    if request.method == "POST":
        error = _validate_invoice_post(request)
        if error:
            return render(
                request,
                "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice, error=error),
            )

        invoice = _invoice_from_post(request, invoice=invoice)
        if _find_invoice_duplicate(invoice):
            return render(
                request,
                "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."),
            )
        try:
            invoice.save()
        except IntegrityError:
            return render(
                request,
                "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."),
            )

        messages.success(request, f"Το τιμολόγιο {invoice.invoice_number} ενημερώθηκε επιτυχώς.")
        return redirect("core:invoices_list")

    form_data = {
        "company": str(invoice.company_id),
        "invoice_number": invoice.invoice_number,
        "amount": invoice.amount,
        "service_type": invoice.service_type or "",
        "date_of_issue": invoice.date_of_issue.isoformat() if invoice.date_of_issue else "",
        "status": invoice.status,
    }
    return render(request, "core/invoice_add.html", _invoice_form_context(form_data, invoice=invoice))
