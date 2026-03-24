from django.urls import path
from . import views


app_name = "core"


urlpatterns = [
    path("", views.home, name="home"),
    path("media-preview/<path:path>/", views.media_preview, name="media_preview"),

    # ── Users ────────────────────────────────────────────────────
    path("users/",        views.user_list,   name="users"),
    path("users/create/", views.user_create, name="user_create"),

    # ── Members ──────────────────────────────────────────────────
    path("members/",                     views.member_list,   name="members_list"),
    path("members/create/",              views.member_create, name="member_create"),
    path("members/<int:member_id>/",     views.member_detail, name="member_detail"),
    path("members/<int:member_id>/edit/", views.member_update, name="member_update"),

    # ── Companies ────────────────────────────────────────────────
    path("companies/",                       views.company_list,   name="companies_list"),
    path("companies/create/",               views.company_create, name="company_create"),
    path("companies/<int:company_id>/",      views.company_detail, name="company_detail"),
    path("companies/<int:company_id>/edit/", views.company_update, name="company_update"),

    # ── Invoices ─────────────────────────────────────────────────
    path("invoices/",                        views.invoice_list,   name="invoices_list"),
    path("invoices/create/",                views.invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/edit/",  views.invoice_update, name="invoice_update"),

    # ── Dashboard ────────────────────────────────────────────────
    path("dashboard/", views.dashboard, name="dashboard"),

    # ── Protocols ────────────────────────────────────────────────
    path("protocols/",                        views.protocol_list,   name="protocol_list"),
    path("protocols/new/",                    views.protocol_create, name="protocol_create"),
    path("protocols/<int:protocol_id>/",      views.protocol_detail, name="protocol_detail"),
    path("protocols/<int:protocol_id>/edit/", views.protocol_update, name="protocol_update"),

    # ── Insurance Companies ──────────────────────────────────────
    path("insurance/",                                               views.insurance_company_list,   name="insurance_company_list"),
    path("insurance/new/",                                           views.insurance_company_create, name="insurance_company_create"),
    path("insurance/<int:company_id>/",                              views.insurance_company_detail, name="insurance_company_detail"),
    path("insurance/<int:company_id>/edit/",                         views.insurance_company_update, name="insurance_company_update"),
    path("insurance/<int:company_id>/contract/new/",                 views.insurance_contract_create, name="insurance_contract_create"),
    path("insurance/<int:company_id>/contracts.json/",               views.insurance_contracts_json,  name="insurance_contracts_json"),
]