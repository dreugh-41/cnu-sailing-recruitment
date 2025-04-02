# config/urls.py
from django.contrib import admin
from django.urls import path, include
from sailors import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
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