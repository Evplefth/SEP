from django.urls import path
from . import views


app_name = "core"


urlpatterns = [
    path("", views.home, name="home"),
    path("media-preview/<path:path>/", views.media_preview, name="media_preview"),
    path("users/", views.user_list, name="users"),
    path("users/create/", views.user_create, name="user_create"),
    path("members/", views.member_list, name="members_list"),
    path("members/<int:member_id>/", views.member_detail, name="member_detail"),
    path("members/create/", views.member_create, name="member_create"),
    path("members/<int:member_id>/edit/", views.member_update, name="member_update"),
    path("companies/", views.company_list, name="companies_list"),
    path("companies/<int:company_id>/", views.company_detail, name="company_detail"),
    path("companies/create/", views.company_create, name="company_create"),
    path("companies/<int:company_id>/edit/", views.company_update, name="company_update"),
    path("invoices/", views.invoice_list, name="invoices_list"),
    path("invoices/create/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/edit/", views.invoice_update, name="invoice_update"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
