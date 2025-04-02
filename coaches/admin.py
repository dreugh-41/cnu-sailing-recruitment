# coaches/admin.py
from django.contrib import admin
from .models import Coach

@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'district', 'full_name', 'email', 'phone')
    list_filter = ('district', 'league')
    search_fields = ('school_name', 'first_name', 'last_name', 'email')