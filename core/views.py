import re
from datetime import date
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.static import serve
from django_countries import countries
from django_otp import user_has_device
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import datetime
from two_factor.views import LoginView as TwoFactorLoginView

from core.models import (
    Banks,
    CompanyPayment,
    DocumentArchive,
    PaymentAllocation,
    Exartomena,
    InsuranceCompany,
    InsuranceContract,
    Invoices,
    MemberFile,
    MemberInsurance,
    Members,
    Properties,
    Protocol,
    companies,
    companies_members,
    nationalities,
)


class RedirectAuthenticatedLoginView(TwoFactorLoginView):
    redirect_authenticated_user = True


def home(request):
    if request.user.is_authenticated:
        return redirect("core:post_login_redirect")
    return redirect("two_factor:login")


@login_required
def post_login_redirect(request):
    if not user_has_device(request.user):
        return redirect("two_factor:setup")
    return redirect("core:dashboard")


def _require_staff_or_redirect(request, redirect_to="core:dashboard"):
    if request.user.is_staff:
        return None
    messages.error(request, "Μόνο διαχειριστές μπορούν να διαγράψουν εγγραφές.")
    return redirect(redirect_to)


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


def _mitroo_expiry_state(deregistration_date):
    if not deregistration_date:
        return {"warning": False, "expired": False, "days_left": None}
    today = timezone.now().date()
    days_left = (deregistration_date - today).days
    return {
        "warning": days_left <= 90,
        "expired": days_left < 0,
        "days_left": days_left,
    }


def _recalculate_company_payment_allocations(company):
    invoices = list(
        Invoices.objects.filter(company=company).order_by("date_of_issue", "id")
    )
    payments = list(
        CompanyPayment.objects.filter(company=company, active=True).order_by("payment_date", "id")
    )

    invoice_remaining = {
        invoice.id: Decimal(invoice.amount or Decimal("0.00"))
        for invoice in invoices
    }
    allocations = []

    for payment in payments:
        remaining_payment = Decimal(payment.amount or Decimal("0.00"))
        if remaining_payment <= 0:
            continue

        for invoice in invoices:
            remaining_invoice = invoice_remaining[invoice.id]
            if remaining_invoice <= 0:
                continue
            if remaining_payment <= 0:
                break

            allocated_amount = min(remaining_payment, remaining_invoice)
            if allocated_amount <= 0:
                continue

            allocations.append(
                PaymentAllocation(
                    payment=payment,
                    invoice=invoice,
                    amount=allocated_amount,
                )
            )
            invoice_remaining[invoice.id] = remaining_invoice - allocated_amount
            remaining_payment -= allocated_amount

    with transaction.atomic():
        PaymentAllocation.objects.filter(payment__company=company).delete()
        if allocations:
            PaymentAllocation.objects.bulk_create(allocations)

        for invoice in invoices:
            is_paid = invoice_remaining[invoice.id] <= 0
            if invoice.status != is_paid:
                invoice.status = is_paid
                invoice.save(update_fields=["status"])


def _attach_invoice_payment_state(invoices):
    invoice_list = list(invoices)
    invoice_ids = [invoice.id for invoice in invoice_list]
    if not invoice_ids:
        return invoice_list

    totals = {
        row["invoice_id"]: row["total"] or Decimal("0.00")
        for row in (
            PaymentAllocation.objects.filter(invoice_id__in=invoice_ids)
            .values("invoice_id")
            .annotate(total=Sum("amount"))
        )
    }

    for invoice in invoice_list:
        allocated_amount = totals.get(invoice.id, Decimal("0.00"))
        outstanding_amount = max(Decimal(invoice.amount or Decimal("0.00")) - allocated_amount, Decimal("0.00"))
        invoice.allocated_amount = allocated_amount
        invoice.outstanding_amount = outstanding_amount
        invoice.is_paid = outstanding_amount == 0 and allocated_amount > 0
        invoice.is_partially_paid = allocated_amount > 0 and outstanding_amount > 0
        if invoice.is_paid:
            invoice.payment_state_label = "Εξοφλημένο"
        elif invoice.is_partially_paid:
            invoice.payment_state_label = "Μερικώς εξοφλημένο"
        else:
            invoice.payment_state_label = "Ανεξόφλητο"

    return invoice_list


def _format_export_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Ναι" if value else "Όχι"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def _clean_export_text(value):
    text = _format_export_value(value)
    if any(marker in text for marker in ("Ξ", "Ο", "β‚¬")):
        try:
            repaired = text.encode("latin1").decode("utf-8")
            if repaired:
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


def _document_form_context(form_data=None, document=None, error=None):
    return {
        "document": document,
        "form_data": form_data or {},
        "error": error,
        "file_type_choices": DocumentArchive.FILE_TYPE_CHOICES,
    }


def _generate_document_code():
    while True:
        code = f"DOC-{get_random_string(8, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')}"
        if not DocumentArchive.objects.filter(file_code=code).exists():
            return code


def _document_from_post(request, document=None):
    document = document or DocumentArchive()
    document.name = (request.POST.get("name") or "").strip()
    document.file_code = (request.POST.get("file_code") or "").strip() or _generate_document_code()
    document.file_type = (request.POST.get("file_type") or "").strip()

    if request.FILES.get("file"):
        document.file = request.FILES["file"]

    return document


def _build_excel_response(sheet_name, filename, headers, rows):
    xml_rows = []
    header_cells = "".join(
        f'<Cell ss:StyleID="header"><Data ss:Type="String">{escape(_clean_export_text(header))}</Data></Cell>'
        for header in headers
    )
    xml_rows.append(f"<Row>{header_cells}</Row>")

    for row in rows:
        cells = "".join(
            f'<Cell><Data ss:Type="String">{escape(_clean_export_text(value))}</Data></Cell>'
            for value in row
        )
        xml_rows.append(f"<Row>{cells}</Row>")

    content = f"""<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
  <Styles>
    <Style ss:ID="header">
      <Font ss:Bold="1"/>
      <Interior ss:Color="#DCEBFF" ss:Pattern="Solid"/>
    </Style>
  </Styles>
  <Worksheet ss:Name="{escape(_clean_export_text(sheet_name[:31]))}">
    <Table>
      {''.join(xml_rows)}
    </Table>
  </Worksheet>
</Workbook>"""

    response = HttpResponse(content, content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
    return response


def _export_pdf_font_name():
    font_name = "ArialUnicodeSEP"
    registered_fonts = set(pdfmetrics.getRegisteredFontNames())
    if font_name not in registered_fonts:
        pdfmetrics.registerFont(TTFont(font_name, r"C:\Windows\Fonts\arial.ttf"))
    return font_name


def _build_pdf_response(title, filename, headers, rows):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=28,
        bottomMargin=24,
    )

    font_name = _export_pdf_font_name()
    styles = getSampleStyleSheet()
    title_style = styles["Heading2"].clone("export_title")
    title_style.fontName = font_name
    title_style.fontSize = 15
    title_style.leading = 18
    title_style.textColor = colors.HexColor("#0F172A")

    cell_style = styles["BodyText"].clone("export_cell")
    cell_style.fontName = font_name
    cell_style.fontSize = 8
    cell_style.leading = 10
    cell_style.wordWrap = "CJK"

    table_data = [[Paragraph(_clean_export_text(header), cell_style) for header in headers]]
    for row in rows:
        table_data.append([
            Paragraph(_clean_export_text(value).replace("\n", "<br/>"), cell_style)
            for value in row
        ])

    column_count = max(len(headers), 1)
    usable_width = landscape(A4)[0] - document.leftMargin - document.rightMargin
    col_width = usable_width / column_count

    table = Table(table_data, repeatRows=1, colWidths=[col_width] * column_count)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BFDBFE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FBFF")]),
    ]))

    story = [
        Paragraph(_clean_export_text(title), title_style),
        Spacer(1, 12),
        table,
    ]
    document.build(story)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


def _member_company_names(member):
    return ", ".join(
        link.company.name for link in member.companies.select_related("company").all()
    )


def _payment_allocated_invoice_numbers(payment):
    return ", ".join(
        f"{allocation.invoice.invoice_number} ({allocation.amount:.2f}€)"
        for allocation in payment.allocations.select_related("invoice").all()
    )


def _export_configs():
    return {
        "members": {
            "label": "Μέλη",
            "filename": "members_export",
            "sheet_name": "Members",
            "queryset": lambda: Members.objects.select_related("nationality", "bank").prefetch_related("companies__company").order_by("last_name", "first_name"),
            "fields": [
                ("last_name", "Επώνυμο", lambda obj: obj.last_name),
                ("first_name", "Όνομα", lambda obj: obj.first_name),
                ("fathers_name", "Πατρώνυμο", lambda obj: obj.fathers_name),
                ("gender", "Φύλο", lambda obj: obj.get_gender_display() if obj.gender else ""),
                ("member_registry_number", "Αριθμός Βιβλίου Μητρώου", lambda obj: obj.member_registry_number),
                ("mitroo_type", "Τύπος Μητρώου", lambda obj: obj.get_mitroo_type_display() if obj.mitroo_type else ""),
                ("mitroo_number", "Αριθμός Μητρώου", lambda obj: obj.mitroo_number),
                ("date_of_registration", "Ημ. Εγγραφής", lambda obj: obj.date_of_registration),
                ("date_of_deregistration", "Ημ. Λήξης", lambda obj: obj.date_of_deregistration),
                ("afm", "ΑΦΜ", lambda obj: obj.AFM),
                ("amka", "ΑΜΚΑ", lambda obj: obj.AMKA),
                ("ama", "ΑΜΑ", lambda obj: obj.AMA),
                ("adt", "ΑΔΤ", lambda obj: obj.ADT),
                ("phone_number1", "Τηλέφωνο 1", lambda obj: obj.phone_number1),
                ("phone_number2", "Τηλέφωνο 2", lambda obj: obj.phone_number2),
                ("email", "Email", lambda obj: obj.email),
                ("bank", "Τράπεζα", lambda obj: obj.bank.name if obj.bank else ""),
                ("iban", "IBAN", lambda obj: obj.bank_account_number),
                ("companies", "Εταιρίες", _member_company_names),
                ("active", "Ενεργό", lambda obj: obj.active),
            ],
        },
        "companies": {
            "label": "Εταιρίες",
            "filename": "companies_export",
            "sheet_name": "Companies",
            "queryset": lambda: companies.objects.order_by("name"),
            "fields": [
                ("name", "Επωνυμία", lambda obj: obj.name),
                ("afm", "ΑΦΜ", lambda obj: obj.AFM),
                ("doy", "ΔΟΥ", lambda obj: obj.DOY),
                ("address", "Διεύθυνση", lambda obj: obj.address),
                ("services", "Υπηρεσίες", lambda obj: obj.services),
                ("opening_invoice_total", "Αρχικές Τιμολογήσεις", lambda obj: obj.opening_invoice_total),
                ("opening_payment_total", "Αρχικές Πληρωμές", lambda obj: obj.opening_payment_total),
                ("active", "Ενεργή", lambda obj: obj.active),
                ("inactive_date", "Ημ. Ανενεργής", lambda obj: obj.inactive_date),
                ("notes", "Σημειώσεις", lambda obj: obj.notes),
            ],
        },
        "invoices": {
            "label": "Τιμολόγια",
            "filename": "invoices_export",
            "sheet_name": "Invoices",
            "queryset": lambda: _attach_invoice_payment_state(
                Invoices.objects.select_related("company").order_by("-date_of_issue", "-id")
            ),
            "fields": [
                ("invoice_number", "Αριθμός Τιμολογίου", lambda obj: obj.invoice_number),
                ("company", "Εταιρία", lambda obj: obj.company.name if obj.company else ""),
                ("date_of_issue", "Ημ. Έκδοσης", lambda obj: obj.date_of_issue),
                ("service_type", "Εργασία", lambda obj: obj.service_type),
                ("amount", "Ποσό", lambda obj: obj.amount),
                ("allocated_amount", "Εξοφλημένο", lambda obj: getattr(obj, "allocated_amount", Decimal("0.00"))),
                ("outstanding_amount", "Υπόλοιπο", lambda obj: getattr(obj, "outstanding_amount", obj.amount)),
                ("payment_state_label", "Κατάσταση Εξόφλησης", lambda obj: getattr(obj, "payment_state_label", "")),
                ("scan_file", "Scan", lambda obj: obj.scan_file.name if obj.scan_file else ""),
            ],
        },
        "payments": {
            "label": "Πληρωμές",
            "filename": "payments_export",
            "sheet_name": "Payments",
            "queryset": lambda: CompanyPayment.objects.select_related("company").prefetch_related("allocations__invoice").order_by("-payment_date", "-id"),
            "fields": [
                ("company", "Εταιρία", lambda obj: obj.company.name if obj.company else ""),
                ("payment_date", "Ημερομηνία", lambda obj: obj.payment_date),
                ("amount", "Ποσό", lambda obj: obj.amount),
                ("reference", "Αναφορά", lambda obj: obj.reference),
                ("active", "Ενεργή", lambda obj: obj.active),
                ("inactive_date", "Ημ. Ανενεργής", lambda obj: obj.inactive_date),
                ("allocated_invoices", "Τιμολόγια που κάλυψε", _payment_allocated_invoice_numbers),
                ("notes", "Σημειώσεις", lambda obj: obj.notes),
            ],
        },
    }


# ── FIX 1: προστέθηκε existing_insurance ────────────────────────
def _member_form_context(form_data=None, member=None, error=None,
                          existing_exartomena=None, existing_companies=None,
                          existing_insurance=None):
    return {
        "banks":               Banks.objects.all().order_by("name"),
        "properties":          Properties.objects.all().order_by("name"),
        "all_companies":       companies.objects.order_by("name"),
        "insurance_companies": InsuranceCompany.objects.order_by("name"),
        "form_data":           form_data or {},
        "member":              member,
        "error":               error,
        "existing_exartomena": existing_exartomena or [],
        "existing_companies":  existing_companies or [],
        "existing_insurance":  existing_insurance or [],  # ← πολλαπλά
    }


def _company_form_context(form_data=None, company=None, error=None, existing_invoices=None, existing_payments=None):
    return {
        "form_data":         form_data or {},
        "company":           company,
        "error":             error,
        "existing_invoices": existing_invoices or [],
        "existing_payments": existing_payments or [],
    }


def _invoice_form_context(form_data=None, invoice=None, error=None):
    return {
        "form_data": form_data or {},
        "invoice":   invoice,
        "companies": companies.objects.order_by("name"),
        "error":     error,
    }


def _payment_form_context(form_data=None, payment=None, company=None, error=None):
    return {
        "form_data": form_data or {},
        "payment": payment,
        "company": company,
        "error": error,
        "companies": companies.objects.order_by("name"),
    }


def _posted_exartomena(request):
    rows = []
    for index in _extract_row_indexes(request.POST, ["exartomeno_name_", "exartomeno_property_"]):
        rows.append({
            "index":       index,
            "name":        request.POST.get(f"exartomeno_name_{index}", ""),
            "property_id": request.POST.get(f"exartomeno_property_{index}", ""),
        })
    return rows


def _posted_member_companies(request):
    rows = []
    for index in _extract_row_indexes(
        request.POST,
        ["company_id_", "company_active_", "company_active_date_", "company_inactive_date_", "company_notes_"],
    ):
        rows.append({
            "index":         index,
            "company_id":    request.POST.get(f"company_id_{index}", ""),
            "active":        request.POST.get(f"company_active_{index}") == "on",
            "active_date":   request.POST.get(f"company_active_date_{index}", ""),
            "inactive_date": request.POST.get(f"company_inactive_date_{index}", ""),
            "notes":         request.POST.get(f"company_notes_{index}", ""),
        })
    return rows


def _posted_invoices(request):
    rows = []
    indexes = sorted(
        set(_extract_row_indexes(request.POST, ["invoice_"]) + _extract_row_indexes(request.FILES, ["invoice_scan_file_"]))
    )
    for index in indexes:
        rows.append({
            "index":          index,
            "invoice_id":     request.POST.get(f"invoice_id_{index}", ""),
            "invoice_number": request.POST.get(f"invoice_number_{index}", ""),
            "amount":         request.POST.get(f"invoice_amount_{index}", ""),
            "service_type":   request.POST.get(f"invoice_service_type_{index}", ""),
            "date_of_issue":  request.POST.get(f"invoice_date_of_issue_{index}", ""),
            "status":         request.POST.get(f"invoice_status_{index}") == "on",
            "scan_file":      request.FILES.get(f"invoice_scan_file_{index}"),
            "scan_name":      request.POST.get(f"invoice_existing_scan_{index}", ""),
        })
    return rows


def _posted_payments(request):
    rows = []
    for index in _extract_row_indexes(request.POST, ["payment_"]):
        rows.append({
            "index":        index,
            "payment_id":   request.POST.get(f"payment_id_{index}", ""),
            "amount":       request.POST.get(f"payment_amount_{index}", ""),
            "payment_date": request.POST.get(f"payment_date_{index}", ""),
            "reference":    request.POST.get(f"payment_reference_{index}", ""),
            "notes":        request.POST.get(f"payment_notes_{index}", ""),
        })
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
        active        = row["active"]
        active_date   = row["active_date"] or (date.today().isoformat() if active else None)
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
        amount         = row["amount"] or None
        date_of_issue  = row["date_of_issue"] or None
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
        invoice.amount         = amount
        invoice.service_type   = (row["service_type"] or "").strip() or None
        invoice.date_of_issue  = date_of_issue
        invoice.status         = row["status"]
        if row["scan_file"]:
            invoice.scan_file = row["scan_file"]
        invoice.save()
        keep_ids.append(invoice.id)
    Invoices.objects.filter(company=company).exclude(id__in=keep_ids).delete()


def _save_company_payments(request, company):
    keep_ids = []
    for row in _posted_payments(request):
        amount = row["amount"] or None
        payment_date = row["payment_date"] or None
        if not amount or not payment_date:
            continue
        payment_id = row["payment_id"] or None
        if payment_id:
            payment = CompanyPayment.objects.filter(pk=payment_id, company=company).first()
            if not payment:
                payment = CompanyPayment(company=company)
        else:
            payment = CompanyPayment(company=company)
        payment.amount = amount
        payment.payment_date = payment_date
        payment.reference = (row["reference"] or "").strip() or None
        payment.notes = (row["notes"] or "").strip() or None
        payment.save()
        keep_ids.append(payment.id)
    CompanyPayment.objects.filter(company=company).exclude(id__in=keep_ids).delete()


def _save_member_files(request, member):
    i = 0
    while True:
        f = request.FILES.get(f"member_file_{i}")
        if f is None:
            break
        desc = (request.POST.get(f"member_file_desc_{i}") or "").strip()
        MemberFile.objects.create(member=member, file=f, description=desc)
        i += 1


# ── FIX 2: πολλαπλά συμβόλαια με _extract_row_indexes ──────────
def _save_member_insurance(request, member):
    """Αποθηκεύει ΠΟΛΛΑΠΛΑ ομαδικά συμβόλαια ανά μέλος."""
    MemberInsurance.objects.filter(member=member).delete()
    for index in _extract_row_indexes(request.POST, ["insurance_contract_"]):
        contract_id         = request.POST.get(f"insurance_contract_{index}") or None
        includes_dependents = request.POST.get(f"insurance_includes_dependents_{index}") == "on"
        if contract_id:
            MemberInsurance.objects.create(
                member=member,
                contract_id=contract_id,
                includes_dependents=includes_dependents,
            )


def _member_from_post(request, member=None):
    member = member or Members()
    member.first_name    = (request.POST.get("first_name") or "").strip()
    member.last_name     = (request.POST.get("last_name") or "").strip()
    member.fathers_name  = (request.POST.get("fathers_name") or "").strip()
    member.gender        = request.POST.get("gender") or None
    member.date_of_birth = request.POST.get("date_of_birth") or None

    nationality_code = request.POST.get("nationality") or None
    if nationality_code:
        country_name = countries.name(nationality_code)
        nationality_obj, _ = nationalities.objects.get_or_create(name=country_name)
        member.nationality = nationality_obj
    else:
        member.nationality = None

    member.ADT  = (request.POST.get("ADT") or "").strip()
    member.AFM  = (request.POST.get("AFM") or "").strip()
    member.AMKA = (request.POST.get("AMKA") or "").strip()
    member.AMA  = (request.POST.get("AMA") or "").strip()
    member.member_registry_number = request.POST.get("member_registry_number") or None

    member.mitroo_type            = request.POST.get("mitroo_type") or None
    member.mitroo_number          = request.POST.get("mitroo_number") or None
    member.date_of_registration   = request.POST.get("date_of_registration") or None
    member.date_of_deregistration = request.POST.get("date_of_deregistration") or None

    member.driver_A = request.POST.get("driver_A") == "on"
    member.driver_B = request.POST.get("driver_B") == "on"
    member.driver_C = request.POST.get("driver_C") == "on"
    member.driver_D = request.POST.get("driver_D") == "on"
    member.lifter   = request.POST.get("lifter") == "on"

    member.omadiko            = request.POST.get("omadiko") == "on"
    member.omadiko_from       = request.POST.get("omadiko_from") or None
    member.omadiko_to         = request.POST.get("omadiko_to") or None
    member.omadiko_exartomena = request.POST.get("omadiko_exartomena") == "on"

    member.bank_id             = request.POST.get("bank") or None
    member.bank_account_number = (request.POST.get("bank_account_number") or "").strip() or None

    member.address       = (request.POST.get("address") or "").strip() or None
    member.tk            = (request.POST.get("tk") or "").strip() or None
    member.phone_number1 = (request.POST.get("phone_number1") or "").strip() or None
    member.phone_number2 = (request.POST.get("phone_number2") or "").strip() or None
    member.email         = (request.POST.get("email") or "").strip() or None

    member.notes          = (request.POST.get("notes") or "").strip() or None
    member.pending_issues = (request.POST.get("pending_issues") or "").strip() or None

    member.active        = request.POST.get("active") == "on"
    member.inactive_date = request.POST.get("inactive_date") or None
    if member.active:
        member.inactive_date = None

    return member


def _company_from_post(request, company=None):
    company = company or companies()
    company.name             = (request.POST.get("name") or "").strip()
    company.AFM              = (request.POST.get("AFM") or "").strip()
    company.DOY              = (request.POST.get("DOY") or "").strip() or None
    company.address          = (request.POST.get("address") or "").strip() or None
    company.services         = (request.POST.get("services") or "").strip() or None
    company.ekremotes_ofiles = (request.POST.get("ekremotes_ofiles") or "").strip() or None
    company.notes            = (request.POST.get("notes") or "").strip() or None
    company.opening_invoice_total = request.POST.get("opening_invoice_total") or 0
    company.opening_payment_total = request.POST.get("opening_payment_total") or 0
    company.active           = request.POST.get("active") == "on"
    company.inactive_date    = request.POST.get("inactive_date") or None
    if company.active:
        company.inactive_date = None
    return company


def _invoice_from_post(request, invoice=None):
    invoice = invoice or Invoices()
    invoice.company_id     = request.POST.get("company") or None
    invoice.invoice_number = (request.POST.get("invoice_number") or "").strip()
    invoice.amount         = request.POST.get("amount") or None
    invoice.service_type   = (request.POST.get("service_type") or "").strip() or None
    invoice.date_of_issue  = request.POST.get("date_of_issue") or None
    invoice.status         = request.POST.get("status") == "on"
    if request.FILES.get("scan_file"):
        invoice.scan_file = request.FILES["scan_file"]
    return invoice


def _payment_from_post(request, payment=None):
    payment = payment or CompanyPayment()
    payment.company_id = request.POST.get("company") or None
    payment.amount = request.POST.get("amount") or None
    payment.payment_date = request.POST.get("payment_date") or None
    payment.reference = (request.POST.get("reference") or "").strip() or None
    payment.notes = (request.POST.get("notes") or "").strip() or None
    payment.active = request.POST.get("active") == "on" or "active" not in request.POST
    payment.inactive_date = request.POST.get("inactive_date") or None
    if payment.active:
        payment.inactive_date = None
    elif not payment.inactive_date:
        payment.inactive_date = timezone.now().date()
    return payment


def _validate_member_post(request):
    required_fields = {
        "first_name":   "Όνομα",
        "last_name":    "Επώνυμο",
        "fathers_name": "Πατρώνυμο",
        "ADT":  "ΑΔΤ",
        "AFM":  "ΑΦΜ",
        "AMKA": "ΑΜΚΑ",
        "AMA":  "ΑΜΑ",
        "member_registry_number": "Αριθμός Βιβλίου Μητρώου",
    }
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπληρώστε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _find_member_duplicate(member):
    unique_fields = {
        "ADT":  "ΑΔΤ",
        "AFM":  "ΑΦΜ",
        "AMKA": "ΑΜΚΑ",
        "AMA":  "ΑΜΑ",
        "bank_account_number": "IBAN",
        "member_registry_number": "Αριθμός Βιβλίου Μητρώου",
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
    required_fields = {"name": "Επωνυμία", "AFM": "ΑΦΜ"}
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπληρώστε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _validate_invoice_post(request):
    required_fields = {
        "company":        "Εταιρία",
        "invoice_number": "Αριθμός τιμολογίου",
        "amount":         "Ποσό",
        "date_of_issue":  "Ημερομηνία έκδοσης",
    }
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπληρώστε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _find_invoice_duplicate(invoice):
    qs = Invoices.objects.filter(invoice_number=invoice.invoice_number)
    if invoice.pk:
        qs = qs.exclude(pk=invoice.pk)
    return qs.exists()


def _validate_payment_post(request):
    required_fields = {
        "company": "Εταιρία",
        "amount": "Ποσό",
        "payment_date": "Ημερομηνία πληρωμής",
    }
    missing = [label for field, label in required_fields.items() if not (request.POST.get(field) or "").strip()]
    if missing:
        return f"Συμπληρώστε τα υποχρεωτικά πεδία: {', '.join(missing)}."
    return None


def _protocol_from_post(request):
    return {
        "subject":               (request.POST.get("subject") or "").strip(),
        "sender_last_name":      (request.POST.get("sender_last_name") or "").strip(),
        "sender_first_name":     (request.POST.get("sender_first_name") or "").strip(),
        "sender_organization":   (request.POST.get("sender_organization") or "").strip(),
        "sender_department":     (request.POST.get("sender_department") or "").strip(),
        "sender_address":        (request.POST.get("sender_address") or "").strip(),
        "sender_tk":             (request.POST.get("sender_tk") or "").strip(),
        "sender_phone":          (request.POST.get("sender_phone") or "").strip(),
        "sender_email":          (request.POST.get("sender_email") or "").strip(),
        "receiver_last_name":    (request.POST.get("receiver_last_name") or "").strip(),
        "receiver_first_name":   (request.POST.get("receiver_first_name") or "").strip(),
        "receiver_organization": (request.POST.get("receiver_organization") or "").strip(),
        "receiver_department":   (request.POST.get("receiver_department") or "").strip(),
        "receiver_address":      (request.POST.get("receiver_address") or "").strip(),
        "receiver_tk":           (request.POST.get("receiver_tk") or "").strip(),
        "receiver_phone":        (request.POST.get("receiver_phone") or "").strip(),
        "receiver_email":        (request.POST.get("receiver_email") or "").strip(),
    }


# ════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {
        "members_count":   Members.objects.count(),
        "companies_count": companies.objects.count(),
        "invoices_count":  Invoices.objects.count(),
    })


@login_required
def export_data(request):
    configs = _export_configs()
    dataset_key = request.GET.get("dataset") or request.POST.get("dataset") or "members"
    export_format = (request.POST.get("export_format") or request.GET.get("export_format") or "pdf").lower()
    if dataset_key not in configs:
        dataset_key = "members"
    if export_format not in {"pdf", "excel"}:
        export_format = "pdf"

    selected_config = configs[dataset_key]
    selected_field_keys = request.POST.getlist("fields") if request.method == "POST" else [
        key for key, _, _ in selected_config["fields"]
    ]

    valid_field_keys = {key for key, _, _ in selected_config["fields"]}
    selected_field_keys = [key for key in selected_field_keys if key in valid_field_keys]

    if request.method == "POST":
        if not selected_field_keys:
            return render(request, "core/export_data.html", {
                "datasets": configs,
                "selected_dataset_key": dataset_key,
                "selected_config": selected_config,
                "selected_field_keys": selected_field_keys,
                "selected_export_format": export_format,
                "error": "Επιλέξτε τουλάχιστον ένα πεδίο για εξαγωγή.",
            })

        field_map = {key: (label, getter) for key, label, getter in selected_config["fields"]}
        headers = [field_map[key][0] for key in selected_field_keys]
        rows = []
        for obj in selected_config["queryset"]():
            rows.append([field_map[key][1](obj) for key in selected_field_keys])

        if export_format == "excel":
            return _build_excel_response(
                selected_config["sheet_name"],
                selected_config["filename"],
                headers,
                rows,
            )

        return _build_pdf_response(
            selected_config["label"],
            selected_config["filename"],
            headers,
            rows,
        )

    return render(request, "core/export_data.html", {
        "datasets": configs,
        "selected_dataset_key": dataset_key,
        "selected_config": selected_config,
        "selected_field_keys": selected_field_keys,
        "selected_export_format": export_format,
    })

# ════════════════════════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════════════════════════

@login_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "core/user_list.html", {"users": users})


@login_required
def user_create(request):
    if not request.user.is_staff:
        messages.error(request, "Μόνο διαχειριστές μπορούν να δημιουργούν νέους χρήστες.")
        return redirect("core:users")

    if request.method == "POST":
        username   = (request.POST.get("username") or "").strip()
        email      = (request.POST.get("email") or "").strip()
        first_name = (request.POST.get("first_name") or "").strip()
        last_name  = (request.POST.get("last_name") or "").strip()
        password1  = request.POST.get("password1") or ""
        password2  = request.POST.get("password2") or ""
        is_staff   = request.POST.get("is_staff") == "on"

        if not username or not password1:
            return render(request, "core/user_add.html", {"error": "Το username και ο κωδικός είναι υποχρεωτικά."})
        if password1 != password2:
            return render(request, "core/user_add.html", {"error": "Οι δύο κωδικοί δεν ταιριάζουν."})
        if User.objects.filter(username=username).exists():
            return render(request, "core/user_add.html", {"error": "Υπάρχει ήδη χρήστης με αυτό το username."})

        user = User.objects.create_user(
            username=username, email=email, password=password1,
            first_name=first_name, last_name=last_name, is_staff=is_staff,
        )
        messages.success(request, f"Ο χρήστης {user.username} δημιουργήθηκε επιτυχώς.")
        return redirect("core:users")

    return render(request, "core/user_add.html")


@login_required
def user_delete(request, user_id):
    staff_redirect = _require_staff_or_redirect(request, "core:users")
    if staff_redirect:
        return staff_redirect

    target_user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        if target_user.pk == request.user.pk:
            messages.error(request, "Δεν μπορείς να διαγράψεις τον δικό σου λογαριασμό.")
            return redirect("core:users")

        username = target_user.username
        target_user.delete()
        messages.success(request, f"Ο χρήστης {username} διαγράφηκε οριστικά.")
    return redirect("core:users")


# ════════════════════════════════════════════════════════════════
#  MEMBERS
# ════════════════════════════════════════════════════════════════

@login_required
def member_list(request):
    members = Members.objects.select_related("nationality", "bank").prefetch_related(
        "companies__company",
        "insurance_contracts__contract__company",
    ).all()
    query  = (request.GET.get("q") or "").strip()
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
            | Q(member_registry_number__icontains=query)
            | Q(phone_number1__icontains=query)
            | Q(phone_number2__icontains=query)
            | Q(email__icontains=query)
        )

    if mitroo in {"A", "B"}:
        members = members.filter(mitroo_type=mitroo)

    for member in members:
        state = _mitroo_expiry_state(member.date_of_deregistration)
        member.has_mitroo_warning = state["warning"]
        member.mitroo_expired = state["expired"]
        member.mitroo_days_left = state["days_left"]

    return render(request, "core/member_list.html", {"members": members})


@login_required
def member_detail(request, member_id):
    member = get_object_or_404(
        Members.objects.select_related("nationality", "bank").prefetch_related(
            "companies__company",
            "exartomena__property",
            "files",
            "insurance_contracts__contract__company",
        ),
        pk=member_id,
    )
    company_links = member.companies.select_related("company").all().order_by("-active", "company__name")
    insurance_links = member.insurance_contracts.select_related("contract__company").all().order_by("-contract__active", "contract__company__name")
    mitroo_state = _mitroo_expiry_state(member.date_of_deregistration)
    member_files = member.files.all()
    return render(request, "core/member_detail.html", {
        "member": member,
        "company_links": company_links,
        "insurance_links": insurance_links,
        "member_files": member_files,
        "mitroo_warning": mitroo_state["warning"],
        "mitroo_expired": mitroo_state["expired"],
        "mitroo_days_left": mitroo_state["days_left"],
    })


@login_required
def member_create(request):
    if request.method == "POST":
        error = _validate_member_post(request)
        if error:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, error=error,
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        member = _member_from_post(request)
        duplicate_label = _find_member_duplicate(member)
        if duplicate_label:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, error=f"Υπάρχει ήδη μέλος με ίδιο {duplicate_label}.",
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        try:
            member.save()
            _save_exartomena(request, member)
            _save_member_companies(request, member)
            _save_member_files(request, member)
            _save_member_insurance(request, member)
        except IntegrityError:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ, αριθμό βιβλίου μητρώου ή IBAN.",
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        messages.success(request, f"Το μέλος {member.last_name} {member.first_name} προστέθηκε επιτυχώς.")
        return redirect("core:members_list")

    return render(request, "core/member_add.html", _member_form_context())


# β”€β”€ FIX 3: member_update ΞΌΞµ Ο€ΞΏΞ»Ξ»Ξ±Ο€Ξ»Ξ¬ existing_insurance β”€β”€β”€β”€β”€β”€β”€β”€β”€
@login_required
def member_update(request, member_id):
    member = get_object_or_404(Members, pk=member_id)

    if request.method == "POST":
        error = _validate_member_post(request)
        if error:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, member=member, error=error,
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        member = _member_from_post(request, member=member)
        duplicate_label = _find_member_duplicate(member)
        if duplicate_label:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, member=member, error=f"Υπάρχει ήδη μέλος με ίδιο {duplicate_label}.",
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        try:
            member.save()
            _save_exartomena(request, member)
            _save_member_companies(request, member)
            _save_member_files(request, member)
            _save_member_insurance(request, member)
        except IntegrityError:
            return render(request, "core/member_add.html", _member_form_context(
                request.POST, member=member, error="Υπάρχει ήδη μέλος με ίδιο ΑΔΤ, ΑΦΜ, ΑΜΚΑ, ΑΜΑ, αριθμό βιβλίου μητρώου ή IBAN.",
                existing_exartomena=_posted_exartomena(request),
                existing_companies=_posted_member_companies(request),
            ))

        messages.success(request, f"Το μέλος {member.last_name} {member.first_name} ενημερώθηκε επιτυχώς.")
        return redirect("core:members_list")

    # ── Υπάρχουσες ασφαλίσεις — ΠΟΛΛΑΠΛΕΣ ──────────────────────
    existing_insurance = [
        {
            "index":               i,
            "company_id":          mi.contract.company_id,
            "contract_id":         mi.contract_id,
            "includes_dependents": mi.includes_dependents,
        }
        for i, mi in enumerate(
            member.insurance_contracts.select_related("contract__company").all()
        )
    ]

    form_data = {
        "first_name":             member.first_name,
        "last_name":              member.last_name,
        "fathers_name":           member.fathers_name,
        "gender":                 member.gender or "",
        "date_of_birth":          member.date_of_birth.isoformat() if member.date_of_birth else "",
        "nationality":            _country_code_from_member_nationality(member),
        "ADT":  member.ADT,
        "AFM":  member.AFM,
        "AMKA": member.AMKA,
        "AMA":  member.AMA,
        "member_registry_number": str(getattr(member, "member_registry_number", "") or ""),
        "mitroo_type":            member.mitroo_type or "",
        "mitroo_number":          str(member.mitroo_number or ""),
        "date_of_registration":   member.date_of_registration.isoformat() if member.date_of_registration else "",
        "date_of_deregistration": member.date_of_deregistration.isoformat() if member.date_of_deregistration else "",
        "driver_A": member.driver_A,
        "driver_B": member.driver_B,
        "driver_C": member.driver_C,
        "driver_D": member.driver_D,
        "lifter":   member.lifter,
        "omadiko":            member.omadiko,
        "omadiko_from":       member.omadiko_from.isoformat() if member.omadiko_from else "",
        "omadiko_to":         member.omadiko_to.isoformat() if member.omadiko_to else "",
        "omadiko_exartomena": member.omadiko_exartomena,
        "bank":                str(member.bank_id or ""),
        "bank_account_number": member.bank_account_number or "",
        "address":       member.address or "",
        "tk":            member.tk or "",
        "phone_number1": member.phone_number1 or "",
        "phone_number2": member.phone_number2 or "",
        "email":         member.email or "",
        "notes":          member.notes or "",
        "pending_issues": member.pending_issues or "",
        "active":        member.active,
        "inactive_date": member.inactive_date.isoformat() if member.inactive_date else "",
    }

    existing_exartomena = [
        {"index": i, "name": ex.name, "property_id": ex.property_id}
        for i, ex in enumerate(member.exartomena.select_related("property").all())
    ]

    existing_companies = [
        {
            "index":         i,
            "company_id":    link.company_id,
            "active":        link.active,
            "active_date":   link.active_date.isoformat() if link.active_date else "",
            "inactive_date": link.inactive_date.isoformat() if link.inactive_date else "",
            "notes":         link.notes or "",
        }
        for i, link in enumerate(member.companies.select_related("company").all())
    ]

    return render(request, "core/member_add.html", _member_form_context(
        form_data, member=member,
        existing_exartomena=existing_exartomena,
        existing_companies=existing_companies,
        existing_insurance=existing_insurance,
    ))


@login_required
def member_delete(request, member_id):
    staff_redirect = _require_staff_or_redirect(request, "core:members_list")
    if staff_redirect:
        return staff_redirect

    member = get_object_or_404(Members, pk=member_id)
    if request.method == "POST":
        member_name = f"{member.last_name} {member.first_name}".strip() or f"ID {member.pk}"
        member.delete()
        messages.success(request, f"Το μέλος {member_name} διαγράφηκε οριστικά.")
    return redirect("core:members_list")


# ════════════════════════════════════════════════════════════════
#  COMPANIES
# ════════════════════════════════════════════════════════════════

@login_required
def company_list(request):
    company_qs = companies.objects.prefetch_related("invoices", "payments").all()
    query = (request.GET.get("q") or "").strip()
    if query:
        company_qs = company_qs.filter(Q(name__icontains=query) | Q(AFM__icontains=query) | Q(DOY__icontains=query))
    return render(request, "core/company_list.html", {"companies": company_qs})


@login_required
def company_detail(request, company_id):
    company = get_object_or_404(companies, pk=company_id)
    invoices_qs = company.invoices.all().order_by("-date_of_issue", "-id")
    payments_qs = company.payments.all().order_by("-payment_date", "-id")

    status_filter = (request.GET.get("status") or "").strip()
    date_from     = (request.GET.get("date_from") or "").strip()
    date_to       = (request.GET.get("date_to") or "").strip()
    invoice_query = (request.GET.get("q") or "").strip()
    filters_applied = any([status_filter, date_from, date_to, invoice_query])

    if invoice_query:
        invoices_qs = invoices_qs.filter(Q(invoice_number__icontains=invoice_query) | Q(service_type__icontains=invoice_query))
    if status_filter in {"paid", "pending"}:
        invoices_qs = invoices_qs.filter(status=(status_filter == "paid"))
    if date_from:
        invoices_qs = invoices_qs.filter(date_of_issue__gte=date_from)
    if date_to:
        invoices_qs = invoices_qs.filter(date_of_issue__lte=date_to)
    if not filters_applied:
        invoices_qs = invoices_qs[:3]
    invoices_qs = _attach_invoice_payment_state(invoices_qs)

    company_members = company.members.select_related("member").all().order_by("-active", "member__last_name")
    invoices_total = company.invoices.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    payments_total = company.payments.filter(active=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    overall_invoiced = (company.opening_invoice_total or Decimal("0.00")) + invoices_total
    overall_paid = (company.opening_payment_total or Decimal("0.00")) + payments_total
    current_balance = overall_invoiced - overall_paid

    return render(request, "core/company_detail.html", {
        "company": company,
        "invoices": invoices_qs,
        "payments": payments_qs,
        "company_members": company_members,
        "filters_applied": filters_applied,
        "invoices_total": invoices_total,
        "payments_total": payments_total,
        "overall_invoiced": overall_invoiced,
        "overall_paid": overall_paid,
        "current_balance": current_balance,
    })


@login_required
def company_create(request):
    if request.method == "POST":
        error = _validate_company_post(request)
        if error:
            return render(request, "core/company_add.html",
                _company_form_context(
                    request.POST,
                    error=error,
                    existing_invoices=_posted_invoices(request),
                    existing_payments=_posted_payments(request),
                ))

        company = _company_from_post(request)
        try:
            company.save()
            _save_company_invoices(request, company)
            _recalculate_company_payment_allocations(company)
        except IntegrityError:
            return render(request, "core/company_add.html",
                _company_form_context(request.POST,
                error="Υπάρχει ήδη εταιρία με ίδιο ΑΦΜ ή τιμολόγιο με ίδιο αριθμό.",
                existing_invoices=_posted_invoices(request),
                existing_payments=_posted_payments(request)))

        messages.success(request, f"Η εταιρία {company.name} προστέθηκε επιτυχώς.")
        return redirect("core:companies_list")

    return render(request, "core/company_add.html", _company_form_context())


@login_required
def company_update(request, company_id):
    company = get_object_or_404(companies, pk=company_id)

    if request.method == "POST":
        error = _validate_company_post(request)
        if error:
            return render(request, "core/company_add.html",
                _company_form_context(request.POST, company=company, error=error,
                existing_invoices=_posted_invoices(request),
                existing_payments=_posted_payments(request)))

        company = _company_from_post(request, company=company)
        try:
            company.save()
            _save_company_invoices(request, company)
            _recalculate_company_payment_allocations(company)
        except IntegrityError:
            return render(request, "core/company_add.html",
                _company_form_context(request.POST, company=company,
                error="Υπάρχει ήδη εταιρία με ίδιο ΑΦΜ ή τιμολόγιο με ίδιο αριθμό.",
                existing_invoices=_posted_invoices(request),
                existing_payments=_posted_payments(request)))

        messages.success(request, f"Η εταιρία {company.name} ενημερώθηκε επιτυχώς.")
        return redirect("core:companies_list")

    form_data = {
        "name":             company.name,
        "AFM":              company.AFM,
        "DOY":              company.DOY or "",
        "address":          company.address or "",
        "services":         company.services or "",
        "ekremotes_ofiles": company.ekremotes_ofiles or "",
        "notes":            company.notes or "",
        "opening_invoice_total": company.opening_invoice_total,
        "opening_payment_total": company.opening_payment_total,
        "active":           company.active,
        "inactive_date":    company.inactive_date.isoformat() if company.inactive_date else "",
    }

    existing_invoices = [
        {
            "index":          i,
            "invoice_id":     invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount":         invoice.amount,
            "service_type":   invoice.service_type or "",
            "date_of_issue":  invoice.date_of_issue.isoformat() if invoice.date_of_issue else "",
            "status":         invoice.status,
            "scan_name":      invoice.scan_file.name if invoice.scan_file else "",
            "scan_url":       reverse("core:media_preview", args=[invoice.scan_file.name]) if invoice.scan_file else "",
        }
        for i, invoice in enumerate(company.invoices.all())
    ]

    existing_payments = [
        {
            "index": i,
            "payment_id": payment.id,
            "amount": payment.amount,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else "",
            "reference": payment.reference or "",
            "notes": payment.notes or "",
        }
        for i, payment in enumerate(company.payments.all())
    ]

    return render(request, "core/company_add.html",
        _company_form_context(
            form_data,
            company=company,
            existing_invoices=existing_invoices,
            existing_payments=existing_payments,
        ))


@login_required
def company_delete(request, company_id):
    staff_redirect = _require_staff_or_redirect(request, "core:companies_list")
    if staff_redirect:
        return staff_redirect

    company = get_object_or_404(companies, pk=company_id)
    if request.method == "POST":
        company_name = company.name or f"ID {company.pk}"
        company.delete()
        messages.success(request, f"Η εταιρία {company_name} διαγράφηκε οριστικά.")
    return redirect("core:companies_list")


@login_required
def payment_create(request):
    company_id = (request.GET.get("company") or request.POST.get("company") or "").strip()
    selected_company = companies.objects.filter(pk=company_id).first() if company_id else None

    if request.method == "POST":
        error = _validate_payment_post(request)
        if error:
            return render(
                request,
                "core/payment_add.html",
                _payment_form_context(request.POST, company=selected_company, error=error),
            )

        payment = _payment_from_post(request)
        payment.save()
        _recalculate_company_payment_allocations(payment.company)
        messages.success(request, "Η πληρωμή καταχωρήθηκε επιτυχώς.")
        return redirect(f"{reverse('core:company_detail', args=[payment.company_id])}?tab=payments")

    form_data = {
        "company": selected_company.id if selected_company else "",
        "active": True,
    }
    return render(request, "core/payment_add.html", _payment_form_context(form_data, company=selected_company))


@login_required
def payment_update(request, payment_id):
    payment = get_object_or_404(CompanyPayment.objects.select_related("company"), pk=payment_id)

    if request.method == "POST":
        error = _validate_payment_post(request)
        if error:
            return render(
                request,
                "core/payment_add.html",
                _payment_form_context(request.POST, payment=payment, company=payment.company, error=error),
            )

        previous_company = payment.company
        payment = _payment_from_post(request, payment=payment)
        payment.save()
        if previous_company and previous_company.pk != payment.company_id:
            _recalculate_company_payment_allocations(previous_company)
        _recalculate_company_payment_allocations(payment.company)
        messages.success(request, "Η πληρωμή ενημερώθηκε επιτυχώς.")
        return redirect(f"{reverse('core:company_detail', args=[payment.company_id])}?tab=payments")

    form_data = {
        "company": payment.company_id,
        "amount": payment.amount,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else "",
        "reference": payment.reference or "",
        "notes": payment.notes or "",
        "active": payment.active,
        "inactive_date": payment.inactive_date.isoformat() if payment.inactive_date else "",
    }
    return render(request, "core/payment_add.html", _payment_form_context(form_data, payment=payment, company=payment.company))


@login_required
def payment_deactivate(request, payment_id):
    payment = get_object_or_404(CompanyPayment, pk=payment_id)
    if request.method == "POST" and payment.active:
        payment.active = False
        payment.inactive_date = timezone.now().date()
        payment.save(update_fields=["active", "inactive_date"])
        _recalculate_company_payment_allocations(payment.company)
        messages.success(request, "Η πληρωμή απενεργοποιήθηκε επιτυχώς.")
    return redirect(f"{reverse('core:company_detail', args=[payment.company_id])}?tab=payments")


@login_required
def payment_delete(request, payment_id):
    payment = get_object_or_404(CompanyPayment.objects.select_related("company"), pk=payment_id)
    if not request.user.is_staff:
        messages.error(request, "Μόνο διαχειριστές μπορούν να διαγράψουν εγγραφές.")
        return redirect(f"{reverse('core:company_detail', args=[payment.company_id])}?tab=payments")

    company_id = payment.company_id
    payment_label = payment.reference or f"{payment.amount} €"
    if request.method == "POST":
        payment.delete()
        if companies.objects.filter(pk=company_id).exists():
            _recalculate_company_payment_allocations(companies.objects.get(pk=company_id))
        messages.success(request, f"Η πληρωμή {payment_label} διαγράφηκε οριστικά.")
    return redirect(f"{reverse('core:company_detail', args=[company_id])}?tab=payments")


@login_required
def invoice_list(request):
    invoices = Invoices.objects.select_related("company").all().order_by("-date_of_issue", "-id")
    company_id    = (request.GET.get("company") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    query         = (request.GET.get("q") or "").strip()

    if company_id:
        invoices = invoices.filter(company_id=company_id)
    if status_filter in {"paid", "pending"}:
        invoices = invoices.filter(status=(status_filter == "paid"))
    if query:
        invoices = invoices.filter(Q(invoice_number__icontains=query) | Q(service_type__icontains=query))
    invoices = _attach_invoice_payment_state(invoices)

    return render(request, "core/invoice_list.html", {
        "invoices":  invoices,
        "companies": companies.objects.order_by("name"),
    })


@login_required
def invoice_create(request):
    if request.method == "POST":
        error = _validate_invoice_post(request)
        if error:
            return render(request, "core/invoice_add.html", _invoice_form_context(request.POST, error=error))

        invoice = _invoice_from_post(request)
        if _find_invoice_duplicate(invoice):
            return render(request, "core/invoice_add.html",
                _invoice_form_context(request.POST, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."))
        try:
            invoice.save()
            _recalculate_company_payment_allocations(invoice.company)
        except IntegrityError:
            return render(request, "core/invoice_add.html",
                _invoice_form_context(request.POST, error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."))

        messages.success(request, f"Το τιμολόγιο {invoice.invoice_number} προστέθηκε επιτυχώς.")
        return redirect("core:invoices_list")

    return render(request, "core/invoice_add.html", _invoice_form_context())


@login_required
def invoice_update(request, invoice_id):
    invoice = get_object_or_404(Invoices.objects.select_related("company"), pk=invoice_id)

    if request.method == "POST":
        error = _validate_invoice_post(request)
        if error:
            return render(request, "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice, error=error))

        previous_company = invoice.company
        invoice = _invoice_from_post(request, invoice=invoice)
        if _find_invoice_duplicate(invoice):
            return render(request, "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice,
                error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."))
        try:
            invoice.save()
            if previous_company and previous_company.pk != invoice.company_id:
                _recalculate_company_payment_allocations(previous_company)
            _recalculate_company_payment_allocations(invoice.company)
        except IntegrityError:
            return render(request, "core/invoice_add.html",
                _invoice_form_context(request.POST, invoice=invoice,
                error="Υπάρχει ήδη τιμολόγιο με αυτόν τον αριθμό."))

        messages.success(request, f"Το τιμολόγιο {invoice.invoice_number} ενημερώθηκε επιτυχώς.")
        return redirect("core:invoices_list")

    form_data = {
        "company":        str(invoice.company_id),
        "invoice_number": invoice.invoice_number,
        "amount":         invoice.amount,
        "service_type":   invoice.service_type or "",
        "date_of_issue":  invoice.date_of_issue.isoformat() if invoice.date_of_issue else "",
        "status":         invoice.status,
    }
    return render(request, "core/invoice_add.html", _invoice_form_context(form_data, invoice=invoice))


@login_required
def invoice_delete(request, invoice_id):
    invoice = get_object_or_404(Invoices.objects.select_related("company"), pk=invoice_id)
    redirect_url = request.META.get("HTTP_REFERER") or reverse("core:invoices_list")
    if not request.user.is_staff:
        messages.error(request, "Μόνο διαχειριστές μπορούν να διαγράψουν εγγραφές.")
        return redirect(redirect_url)

    company_id = invoice.company_id
    invoice_number = invoice.invoice_number
    if request.method == "POST":
        invoice.delete()
        if companies.objects.filter(pk=company_id).exists():
            _recalculate_company_payment_allocations(companies.objects.get(pk=company_id))
        messages.success(request, f"Το τιμολόγιο {invoice_number} διαγράφηκε οριστικά.")
    return redirect(redirect_url)


# ════════════════════════════════════════════════════════════════
#  ΠΡΩΤΟΚΟΛΛΑ
# ════════════════════════════════════════════════════════════════

@login_required
def protocol_list(request):
    protocols = Protocol.objects.all()
    query  = (request.GET.get("q") or "").strip()
    year_f = (request.GET.get("year") or "").strip()

    if query:
        protocols = protocols.filter(
            Q(subject__icontains=query)
            | Q(sender_last_name__icontains=query)
            | Q(sender_organization__icontains=query)
            | Q(receiver_last_name__icontains=query)
            | Q(receiver_first_name__icontains=query)
            | Q(receiver_organization__icontains=query)
        )
    if year_f:
        protocols = protocols.filter(year=year_f)

    years = Protocol.objects.values_list("year", flat=True).distinct().order_by("-year")

    return render(request, "core/protocol_list.html", {
        "protocols": protocols,
        "years":     years,
    })


@login_required
def protocol_create(request):
    today    = timezone.now().date()
    year     = today.year
    next_num = Protocol.next_number(year)

    if request.method == "POST":
        date_str    = request.POST.get("date") or today.isoformat()
        chosen_date = datetime.date.fromisoformat(date_str)
        chosen_year = chosen_date.year
        chosen_num  = Protocol.next_number(chosen_year)
        fields      = _protocol_from_post(request)

        if not fields["subject"]:
            return render(request, "core/protocol_create.html", {
                "next_num": chosen_num, "year": chosen_year,
                "today": today.isoformat(), "error": "Το θέμα είναι υποχρεωτικό.",
            })

        protocol = Protocol(protocol_number=chosen_num, year=chosen_year, date=chosen_date, **fields)
        if request.FILES.get("file"):
            protocol.file = request.FILES["file"]

        try:
            protocol.save()
        except IntegrityError:
            protocol.protocol_number = Protocol.next_number(chosen_year)
            protocol.save()

        messages.success(request, f"Το πρωτόκολλο {protocol.full_number} καταχωρήθηκε επιτυχώς.")
        return redirect("core:protocol_list")

    return render(request, "core/protocol_create.html", {
        "next_num": next_num, "year": year, "today": today.isoformat(),
    })


@login_required
def protocol_detail(request, protocol_id):
    protocol = get_object_or_404(Protocol, pk=protocol_id)
    return render(request, "core/protocol_details.html", {"protocol": protocol})


@login_required
def protocol_update(request, protocol_id):
    protocol = get_object_or_404(Protocol, pk=protocol_id)

    if request.method == "POST":
        fields = _protocol_from_post(request)
        if not fields["subject"]:
            return render(request, "core/protocol_create.html", {
                "protocol": protocol, "error": "Το θέμα είναι υποχρεωτικό.",
            })
        for attr, value in fields.items():
            setattr(protocol, attr, value)
        if request.FILES.get("file"):
            protocol.file = request.FILES["file"]
        protocol.save()
        messages.success(request, f"Το πρωτόκολλο {protocol.full_number} ενημερώθηκε επιτυχώς.")
        return redirect("core:protocol_list")

    return render(request, "core/protocol_create.html", {"protocol": protocol})


# ════════════════════════════════════════════════════════════════
#  ΑΣΦΑΛΙΣΤΙΚΕΣ ΕΤΑΙΡΕΙΕΣ
# ════════════════════════════════════════════════════════════════

@login_required
def insurance_company_list(request):
    ins_companies = InsuranceCompany.objects.prefetch_related("contracts").all()
    query = (request.GET.get("q") or "").strip()
    if query:
        ins_companies = ins_companies.filter(
            Q(name__icontains=query) | Q(contact_person__icontains=query)
        )
    return render(request, "core/insurance_company_list.html", {"ins_companies": ins_companies})


@login_required
def insurance_company_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            return render(request, "core/insurance_company_add.html", {"error": "Η επωνυμία είναι υποχρεωτική."})

        ins = InsuranceCompany.objects.create(
            name           = name,
            address        = (request.POST.get("address") or "").strip(),
            phone          = (request.POST.get("phone") or "").strip(),
            email          = (request.POST.get("email") or "").strip(),
            contact_person = (request.POST.get("contact_person") or "").strip(),
            notes          = (request.POST.get("notes") or "").strip(),
        )
        messages.success(request, f"Η ασφαλιστική εταιρία {ins.name} προστέθηκε επιτυχώς.")
        return redirect("core:insurance_company_list")

    return render(request, "core/insurance_company_add.html")


@login_required
def insurance_company_detail(request, company_id):
    ins       = get_object_or_404(InsuranceCompany, pk=company_id)
    contracts = ins.contracts.prefetch_related("members__member").all()
    return render(request, "core/insurance_company_detail.html", {"ins": ins, "contracts": contracts})


@login_required
def insurance_company_update(request, company_id):
    ins = get_object_or_404(InsuranceCompany, pk=company_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            return render(request, "core/insurance_company_add.html", {
                "ins": ins, "error": "Η επωνυμία είναι υποχρεωτική."
            })
        ins.name           = name
        ins.address        = (request.POST.get("address") or "").strip()
        ins.phone          = (request.POST.get("phone") or "").strip()
        ins.email          = (request.POST.get("email") or "").strip()
        ins.contact_person = (request.POST.get("contact_person") or "").strip()
        ins.notes          = (request.POST.get("notes") or "").strip()
        ins.save()
        messages.success(request, f"Η ασφαλιστική {ins.name} ενημερώθηκε.")
        return redirect("core:insurance_company_list")

    return render(request, "core/insurance_company_add.html", {"ins": ins})


@login_required
def insurance_contract_create(request, company_id):
    ins = get_object_or_404(InsuranceCompany, pk=company_id)

    if request.method == "POST":
        contract_number = (request.POST.get("contract_number") or "").strip()
        if not contract_number:
            return render(request, "core/insurance_contract_add.html", {
                "ins": ins, "error": "Ο αριθμός συμβολαίου είναι υποχρεωτικός."
            })
        InsuranceContract.objects.create(
            company         = ins,
            contract_number = contract_number,
            coverage_type   = (request.POST.get("coverage_type") or "").strip(),
            amount          = request.POST.get("amount") or None,
            start_date      = request.POST.get("start_date") or None,
            end_date        = request.POST.get("end_date") or None,
            active          = request.POST.get("active") == "on",
            notes           = (request.POST.get("notes") or "").strip(),
        )
        messages.success(request, f"Το συμβόλαιο {contract_number} προστέθηκε.")
        return redirect("core:insurance_company_detail", company_id=ins.pk)

    return render(request, "core/insurance_contract_add.html", {"ins": ins})


@login_required
def insurance_contracts_json(request, company_id):
    contracts = InsuranceContract.objects.filter(
        company_id=company_id, active=True
    ).values("id", "contract_number", "coverage_type")
    return JsonResponse({"contracts": list(contracts)})


@login_required
def document_list(request):
    documents = DocumentArchive.objects.all()
    q = (request.GET.get("q") or "").strip()
    file_type = (request.GET.get("file_type") or "").strip()

    if q:
        documents = documents.filter(
            Q(name__icontains=q)
            | Q(file_code__icontains=q)
            | Q(file_type__icontains=q)
        )
    if file_type:
        documents = documents.filter(file_type__iexact=file_type)

    return render(request, "core/document_list.html", {
        "documents": documents,
        "file_type_choices": DocumentArchive.FILE_TYPE_CHOICES,
        "totals": {
            "all": documents.count(),
            "types": len(DocumentArchive.FILE_TYPE_CHOICES),
        },
    })


@login_required
def document_create(request):
    if request.method == "POST":
        document = _document_from_post(request)
        if not request.FILES.get("file"):
            return render(
                request,
                "core/document_form.html",
                _document_form_context(request.POST, error="Το αρχείο είναι υποχρεωτικό."),
            )

        try:
            document.full_clean()
            document.save()
        except ValidationError as exc:
            return render(
                request,
                "core/document_form.html",
                _document_form_context(request.POST, error=_validation_error_message(exc)),
            )
        except IntegrityError:
            return render(
                request,
                "core/document_form.html",
                _document_form_context(request.POST, error="Υπάρχει ήδη έγγραφο με αυτό το όνομα."),
            )

        messages.success(request, f"Το έγγραφο {document.name} καταχωρήθηκε επιτυχώς.")
        return redirect("core:document_list")

    return render(request, "core/document_form.html", _document_form_context())


@login_required
def document_update(request, document_id):
    document = get_object_or_404(DocumentArchive, pk=document_id)

    if request.method == "POST":
        document = _document_from_post(request, document=document)
        try:
            document.full_clean()
            document.save()
        except ValidationError as exc:
            return render(
                request,
                "core/document_form.html",
                _document_form_context(request.POST, document=document, error=_validation_error_message(exc)),
            )
        except IntegrityError:
            return render(
                request,
                "core/document_form.html",
                _document_form_context(request.POST, document=document, error="Υπάρχει ήδη έγγραφο με αυτό το όνομα."),
            )

        messages.success(request, f"Το έγγραφο {document.name} ενημερώθηκε επιτυχώς.")
        return redirect("core:document_list")

    form_data = {
        "name": document.name,
        "file_code": document.file_code,
        "file_type": document.file_type,
    }
    return render(request, "core/document_form.html", _document_form_context(form_data, document=document))
