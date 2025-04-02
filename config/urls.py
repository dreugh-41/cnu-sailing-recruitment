# config/urls.py
from django.contrib import admin
from django.urls import path, include
from sailors import views
from sailors.debug_views import debug_auth
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('debug-auth/', debug_auth, name='debug_auth'),
    path('', include('sailors.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('coaches/', include('coaches.urls')),
    path('admin/', admin.site.urls),
    path('', include('sailors.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('coaches/', include('coaches.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
