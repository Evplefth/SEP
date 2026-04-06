from django.contrib import admin

from .models import Expense, ExpenseAttachment


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_code", "expense_date", "category", "subcategory", "amount", "is_paid")
    list_filter = ("category", "subcategory", "detail_type", "is_paid", "expense_date")
    search_fields = ("expense_code", "description", "notes")
    inlines = [ExpenseAttachmentInline]


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ("expense", "filename", "created_at")
    search_fields = ("expense__expense_code", "file")
