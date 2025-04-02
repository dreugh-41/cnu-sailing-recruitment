# sailors/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sailors/', views.sailor_list, name='sailor_list'),
    path('scrape/', views.scrape_form, name='scrape_form'),
    path('scrape/execute/', views.execute_scrape, name='execute_scrape'),
    path('reset-database/', views.reset_database, name='reset_database'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('interested/', views.interested_sailors, name='interested_sailors'),
    path('toggle-interest/<int:sailor_id>/', views.toggle_interest, name='toggle_interest'),
    path('update-notes/<int:interest_id>/', views.update_notes, name='update_notes'),
    path('remove-year/', views.remove_graduation_year, name='remove_graduation_year'),
    path('confirm-remove-year/<str:grad_year>/', views.confirm_remove_year, name='confirm_remove_year'),
    path('update-heard-from/<int:interest_id>/', views.update_heard_from, name='update_heard_from'),
    path('update-reached-out/<int:interest_id>/', views.update_reached_out, name='update_reached_out'),
    path('sailor/<int:sailor_id>/', views.sailor_profile, name='sailor_profile'),
    path('update-sailor-info/<int:interest_id>/', views.update_sailor_info, name='update_sailor_info'),
]