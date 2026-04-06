from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Expense, ExpenseAttachment


def _next_expense_code():
    year = timezone.now().year
    prefix = f"EXP-{year}-"
    latest = (
        Expense.objects.filter(expense_code__startswith=prefix)
        .order_by("-expense_code")
        .values_list("expense_code", flat=True)
        .first()
    )
    next_number = 1
    if latest:
        try:
            next_number = int(latest.split("-")[-1]) + 1
        except (TypeError, ValueError):
            next_number = Expense.objects.filter(expense_code__startswith=prefix).count() + 1
    return f"{prefix}{next_number:04d}"


def _expense_from_post(request, expense=None):
    expense = expense or Expense()
    expense.expense_code = (request.POST.get("expense_code") or "").strip() or _next_expense_code()
    expense.expense_date = request.POST.get("expense_date") or None
    expense.amount = request.POST.get("amount") or None
    expense.category = (request.POST.get("category") or "").strip()
    expense.subcategory = (request.POST.get("subcategory") or "").strip()
    expense.detail_type = (request.POST.get("detail_type") or "").strip()
    expense.period_month = request.POST.get("period_month") or None
    expense.period_year = request.POST.get("period_year") or None
    expense.description = (request.POST.get("description") or "").strip()
    expense.notes = (request.POST.get("notes") or "").strip()
    expense.is_paid = request.POST.get("is_paid", "off") == "on"

    if request.POST.get("remove_pdf") == "on":
        if expense.pk and expense.pdf_file:
            expense.pdf_file.delete(save=False)
        expense.pdf_file = None

    return expense


def _sync_expense_attachments(request, expense):
    remove_ids = []
    for attachment_id in request.POST.getlist("remove_attachment_ids"):
        if attachment_id.isdigit():
            remove_ids.append(int(attachment_id))

    if remove_ids:
        for attachment in expense.attachments.filter(id__in=remove_ids):
            if attachment.file:
                attachment.file.delete(save=False)
            attachment.delete()

    for uploaded_file in request.FILES.getlist("pdf_files"):
        ExpenseAttachment.objects.create(expense=expense, file=uploaded_file)


def _expense_form_context(form_data=None, expense=None, error=None):
    form_data = form_data.copy() if form_data else {}
    if "is_paid" in form_data:
        form_data["is_paid"] = form_data.get("is_paid") == "on"
    return {
        "expense": expense,
        "form_data": form_data or {},
        "error": error,
        "category_choices": Expense.CATEGORY_CHOICES,
        "subcategory_choices": Expense.SUBCATEGORY_CHOICES,
        "detail_type_choices": Expense.DETAIL_TYPE_CHOICES,
        "default_expense_code": _next_expense_code() if not expense else expense.expense_code,
    }


def _validation_error_message(exc):
    if hasattr(exc, "message_dict"):
        parts = []
        for messages_list in exc.message_dict.values():
            parts.extend(messages_list)
        return " ".join(parts)
    return " ".join(exc.messages)


def _has_pdf_after_submit(request, expense):
    remaining_legacy_pdf = expense.pdf_file and request.POST.get("remove_pdf") != "on"
    remaining_attachments = expense.attachments.exclude(
        id__in=[int(value) for value in request.POST.getlist("remove_attachment_ids") if value.isdigit()]
    ).exists()
    new_uploads = bool(request.FILES.getlist("pdf_files"))
    return bool(remaining_legacy_pdf or remaining_attachments or new_uploads)


@login_required
def expense_list(request):
    expenses = Expense.objects.prefetch_related("attachments").order_by("is_paid", "-created_at", "-id")
    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    year = (request.GET.get("year") or "").strip()

    if q:
        expenses = expenses.filter(
            Q(expense_code__icontains=q)
            | Q(description__icontains=q)
            | Q(notes__icontains=q)
        )
    if category:
        expenses = expenses.filter(category=category)
    if year.isdigit():
        expenses = expenses.filter(period_year=int(year))

    totals = {
        "all": sum((expense.amount for expense in expenses), start=Decimal("0.00")),
        "paid_count": expenses.filter(is_paid=True).count(),
        "pending_amount": sum(
            (expense.amount for expense in expenses.filter(is_paid=False)),
            start=Decimal("0.00"),
        ),
    }

    return render(
        request,
        "expenses/expense_list.html",
        {
            "expenses": expenses,
            "totals": totals,
            "category_choices": Expense.CATEGORY_CHOICES,
        },
    )


@login_required
def expense_stats(request):
    expenses = Expense.objects.all()
    category = (request.GET.get("category") or "").strip()
    year = (request.GET.get("year") or "").strip()

    if category:
        expenses = expenses.filter(category=category)
    if year.isdigit():
        expenses = expenses.filter(period_year=int(year))

    total_amount = Decimal("0.00")
    paid_amount = Decimal("0.00")
    unpaid_amount = Decimal("0.00")
    category_rows = []
    subcategory_rows = []
    year_rows = []

    category_map = {}
    subcategory_map = {}
    year_map = {}

    for expense in expenses.order_by("-created_at", "-id"):
        amount = expense.amount or Decimal("0.00")
        total_amount += amount
        if expense.is_paid:
            paid_amount += amount
        else:
            unpaid_amount += amount

        category_key = expense.get_category_display()
        category_entry = category_map.setdefault(
            category_key,
            {"label": category_key, "count": 0, "total": Decimal("0.00"), "paid": Decimal("0.00"), "unpaid": Decimal("0.00")},
        )
        category_entry["count"] += 1
        category_entry["total"] += amount
        if expense.is_paid:
            category_entry["paid"] += amount
        else:
            category_entry["unpaid"] += amount

        if expense.subcategory:
            subcategory_key = f"{expense.get_category_display()} / {expense.get_subcategory_display()}"
            subcategory_entry = subcategory_map.setdefault(
                subcategory_key,
                {"label": subcategory_key, "count": 0, "total": Decimal("0.00"), "paid": Decimal("0.00"), "unpaid": Decimal("0.00")},
            )
            subcategory_entry["count"] += 1
            subcategory_entry["total"] += amount
            if expense.is_paid:
                subcategory_entry["paid"] += amount
            else:
                subcategory_entry["unpaid"] += amount

        year_label = expense.period_year or "Χωρίς έτος"
        year_entry = year_map.setdefault(
            year_label,
            {"label": year_label, "count": 0, "total": Decimal("0.00"), "paid": Decimal("0.00"), "unpaid": Decimal("0.00")},
        )
        year_entry["count"] += 1
        year_entry["total"] += amount
        if expense.is_paid:
            year_entry["paid"] += amount
        else:
            year_entry["unpaid"] += amount

    category_rows = sorted(category_map.values(), key=lambda row: (-row["total"], row["label"]))
    subcategory_rows = sorted(subcategory_map.values(), key=lambda row: (-row["total"], row["label"]))
    year_rows = sorted(
        year_map.values(),
        key=lambda row: (
            row["label"] == "Χωρίς έτος",
            -(row["label"] if isinstance(row["label"], int) else 0),
            str(row["label"]),
        ),
    )

    return render(
        request,
        "expenses/expense_stats.html",
        {
            "totals": {
                "all": total_amount,
                "paid_amount": paid_amount,
                "unpaid_amount": unpaid_amount,
                "count": expenses.count(),
            },
            "category_rows": category_rows,
            "subcategory_rows": subcategory_rows,
            "year_rows": year_rows,
            "category_choices": Expense.CATEGORY_CHOICES,
        },
    )


@login_required
def expense_create(request):
    if request.method == "POST":
        expense = _expense_from_post(request)
        try:
            expense.full_clean()
            if expense.is_paid and not _has_pdf_after_submit(request, expense):
                raise ValidationError("Για πληρωμένο έξοδο πρέπει να επισυνάψετε τουλάχιστον ένα PDF.")
            expense.save()
            _sync_expense_attachments(request, expense)
        except ValidationError as exc:
            return render(
                request,
                "expenses/expense_form.html",
                _expense_form_context(request.POST, error=_validation_error_message(exc)),
            )

        messages.success(request, f"Το έξοδο {expense.expense_code} καταχωρήθηκε επιτυχώς.")
        return redirect("expenses:detail", expense_id=expense.id)

    initial = {
        "expense_date": date.today().isoformat(),
        "is_paid": False,
        "expense_code": _next_expense_code(),
    }
    return render(request, "expenses/expense_form.html", _expense_form_context(initial))


@login_required
def expense_detail(request, expense_id):
    expense = get_object_or_404(Expense.objects.prefetch_related("attachments"), pk=expense_id)
    return render(request, "expenses/expense_detail.html", {"expense": expense})


@login_required
def expense_update(request, expense_id):
    expense = get_object_or_404(Expense.objects.prefetch_related("attachments"), pk=expense_id)

    if request.method == "POST":
        expense = _expense_from_post(request, expense=expense)
        try:
            expense.full_clean()
            if expense.is_paid and not _has_pdf_after_submit(request, expense):
                raise ValidationError("Για πληρωμένο έξοδο πρέπει να επισυνάψετε τουλάχιστον ένα PDF.")
            expense.save()
            _sync_expense_attachments(request, expense)
        except ValidationError as exc:
            return render(
                request,
                "expenses/expense_form.html",
                _expense_form_context(request.POST, expense=expense, error=_validation_error_message(exc)),
            )

        messages.success(request, f"Το έξοδο {expense.expense_code} ενημερώθηκε επιτυχώς.")
        return redirect("expenses:detail", expense_id=expense.id)

    form_data = {
        "expense_code": expense.expense_code,
        "expense_date": expense.expense_date.isoformat() if expense.expense_date else "",
        "amount": expense.amount,
        "category": expense.category,
        "subcategory": expense.subcategory,
        "detail_type": expense.detail_type,
        "period_month": expense.period_month or "",
        "period_year": expense.period_year or "",
        "description": expense.description,
        "notes": expense.notes,
        "is_paid": expense.is_paid,
    }
    return render(request, "expenses/expense_form.html", _expense_form_context(form_data, expense=expense))
