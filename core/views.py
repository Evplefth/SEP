from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# Create your views here.


@login_required
def home(request):
    return render(request, 'core/home.html')


@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'core/user_list.html', {'users': users})

@login_required
def user_detail(request, user_id):
    user = User.objects.get(id=user_id)
    return render(request, 'core/user_detail.html', {'user': user})
    

