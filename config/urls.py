# config/urls.py
from django.contrib import admin
from django.urls import path, include
from sailors import views
from django.conf import settings
from django.conf.urls.static import static
from sailors.login_fix import fix_login, test_login, direct_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login-fix/', fix_login, name='login_fix'),
    path('login-test/', test_login, name='test_login'),
    path('', include('sailors.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('coaches/', include('coaches.urls')),
    path('admin/', admin.site.urls),
    path('', include('sailors.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('coaches/', include('coaches.urls')),
    path('emergency-login/', direct_login, name='emergency_login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
