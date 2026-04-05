from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from two_factor.urls import urlpatterns as tf_urls
from core.views import RedirectAuthenticatedLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # 2FA login/setup/logout
    path('account/login/', RedirectAuthenticatedLoginView.as_view(), name='login'),
    path('', include(tf_urls, namespace='two_factor')),
    path('account/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # your app
    path('', include('core.urls')),
    path('expenses/', include('expenses.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
