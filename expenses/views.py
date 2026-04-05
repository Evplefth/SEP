from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Expense


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
    expense.active = request.POST.get("active", "on") == "on"
    expense.inactive_date = request.POST.get("inactive_date") or None

    if request.FILES.get("pdf_file"):
        expense.pdf_file = request.FILES["pdf_file"]
    elif request.POST.get("remove_pdf") == "on":
        expense.pdf_file = None

    if expense.active:
        expense.inactive_date = None
    elif not expense.inactive_date:
        expense.inactive_date = date.today()

    return expense


def _expense_form_context(form_data=None, expense=None, error=None):
    form_data = form_data.copy() if form_data else {}
    if "active" in form_data:
        form_data["active"] = form_data.get("active") == "on"
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


@login_required
def expense_list(request):
    expenses = Expense.objects.all()
    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    active = (request.GET.get("active") or "").strip()
    year = (request.GET.get("year") or "").strip()

    if q:
        expenses = expenses.filter(
            Q(expense_code__icontains=q)
            | Q(description__icontains=q)
            | Q(notes__icontains=q)
        )
    if category:
        expenses = expenses.filter(category=category)
    if active in {"active", "inactive"}:
        expenses = expenses.filter(active=(active == "active"))
    if year.isdigit():
        expenses = expenses.filter(period_year=int(year))

    totals = {
        "all": sum((expense.amount for expense in expenses), start=Decimal("0.00")),
        "active_count": expenses.filter(active=True).count(),
        "inactive_count": expenses.filter(active=False).count(),
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
def expense_create(request):
    if request.method == "POST":
        expense = _expense_from_post(request)
        try:
            expense.full_clean()
            expense.save()
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
        "active": True,
        "expense_code": _next_expense_code(),
    }
    return render(request, "expenses/expense_form.html", _expense_form_context(initial))


@login_required
def expense_detail(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    return render(request, "expenses/expense_detail.html", {"expense": expense})


@login_required
def expense_update(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)

    if request.method == "POST":
        expense = _expense_from_post(request, expense=expense)
        try:
            expense.full_clean()
            expense.save()
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
        "active": expense.active,
        "inactive_date": expense.inactive_date.isoformat() if expense.inactive_date else "",
    }
    return render(request, "expenses/expense_form.html", _expense_form_context(form_data, expense=expense))
