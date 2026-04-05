from django.urls import path

from . import views


app_name = "expenses"


urlpatterns = [
    path("", views.expense_list, name="list"),
    path("stats/", views.expense_stats, name="stats"),
    path("create/", views.expense_create, name="create"),
    path("<int:expense_id>/", views.expense_detail, name="detail"),
    path("<int:expense_id>/edit/", views.expense_update, name="update"),
]
