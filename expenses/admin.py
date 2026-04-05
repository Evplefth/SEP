from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_code", "expense_date", "category", "subcategory", "amount", "active")
    list_filter = ("category", "subcategory", "detail_type", "active", "expense_date")
    search_fields = ("expense_code", "description", "notes")

