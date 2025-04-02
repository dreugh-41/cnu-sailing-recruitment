# coaches/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.coach_list, name='coach_list'),
    path('update-reached-out/<int:coach_id>/', views.update_coach_reached_out, name='update_coach_reached_out'),
    path('update-heard-from/<int:coach_id>/', views.update_coach_heard_from, name='update_coach_heard_from'),
]