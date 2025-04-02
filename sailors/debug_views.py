from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.conf import settings
import os

def debug_auth(request):
    """Debug view to test authentication and create admin user"""
    response_parts = []
    
    # Try to create superuser if it doesn't exist
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'AdminPass123!')
            response_parts.append("Created admin user: username='admin', password='AdminPass123!'")
        else:
            response_parts.append("Admin user already exists")
    except IntegrityError as e:
        response_parts.append(f"Error creating user: {str(e)}")
    except Exception as e:
        response_parts.append(f"Unexpected error: {str(e)}")
    
    # Count existing users
    try:
        user_count = User.objects.count()
        response_parts.append(f"Total users in database: {user_count}")
        users = User.objects.all()
        response_parts.append("Users: " + ", ".join([u.username for u in users]))
    except Exception as e:
        response_parts.append(f"Error counting users: {str(e)}")
    
    # Check settings
    response_parts.append(f"LOGIN_URL: {settings.LOGIN_URL}")
    response_parts.append(f"LOGIN_REDIRECT_URL: {getattr(settings, 'LOGIN_REDIRECT_URL', 'Not set')}")
    
    # Check database connection
    response_parts.append(f"DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
    
    return HttpResponse("<br>".join(response_parts))
