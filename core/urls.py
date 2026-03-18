from django.urls import path
from . import views


app_name ='core'


urlpatterns = [
    path('', views.home, name='home'),
    path('users/', views.user_list, name='users'),
    path('members/',views.member_list, name='members_list'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('members/create/', views.member_create, name='member_create'),

]