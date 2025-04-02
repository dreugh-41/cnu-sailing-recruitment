from django.contrib import admin
from .models import School, RegattaType, Regatta, Sailor, Result

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(RegattaType)
class RegattaTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'weight')

@admin.register(Regatta)
class RegattaAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'date', 'regatta_type', 'is_jv')
    list_filter = ('season', 'regatta_type', 'is_jv')
    search_fields = ('name',)

@admin.register(Sailor)
class SailorAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'elo_rating')
    list_filter = ('school',)
    search_fields = ('name', 'school__name')

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('sailor', 'regatta', 'division', 'position', 'place')
    list_filter = ('division', 'position', 'regatta__season')
    search_fields = ('sailor__name', 'regatta__name')