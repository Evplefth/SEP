from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from core.models import Members

# Create your views here.



def home(request):
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')




@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'core/user_list.html', {'users': users})

@login_required
def member_list(request):
    members = Members.objects.all()
    return render(request,'core/member_list.html', {'members': members})

@login_required
def member_create(request):
    return render(request, 'core/member_add.html')







