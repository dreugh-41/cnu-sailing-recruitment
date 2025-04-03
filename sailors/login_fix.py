from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db import IntegrityError, connections
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.middleware.csrf import get_token

def fix_login(request):
    """View to diagnose and fix login issues"""
    csrf_token = get_token(request)
    response = []
    
    # Display environment info
    response.append("<h2>Environment Information</h2>")
    response.append(f"<p>DATABASE ENGINE: {settings.DATABASES['default'].get('ENGINE', 'Not set')}</p>")
    
    # Check database connection
    response.append("<h2>Database Connection Test</h2>")
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            response.append(f"<p>Database connection successful: {row}</p>")
    except Exception as e:
        response.append(f"<p style='color:red'>Database connection error: {str(e)}</p>")
    
    # Check users table and create admin if needed
    response.append("<h2>Users Check</h2>")
    try:
        user_count = User.objects.count()
        response.append(f"<p>Total users in database: {user_count}</p>")
        
        # Create admin user if none exists
        if user_count == 0:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='AdminPassword123!'
            )
            response.append("<p style='color:green'>Created admin user: username='admin', password='AdminPassword123!'</p>")
        else:
            # List existing users
            users = User.objects.all()
            response.append("<p>Existing users:</p><ul>")
            for user in users:
                response.append(f"<li>{user.username} (is_staff: {user.is_staff}, is_superuser: {user.is_superuser})</li>")
            response.append("</ul>")
            
            # Create test user if not exists
            if not User.objects.filter(username='testuser').exists():
                User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='TestPass123!'
                )
                response.append("<p style='color:green'>Created test user: username='testuser', password='TestPass123!'</p>")
    except Exception as e:
        response.append(f"<p style='color:red'>Error checking/creating users: {str(e)}</p>")
    
    # Login form for quick testing
    response.append("<h2>Test Login Form</h2>")
    response.append(f"""
    <form method="post" action="/login-test/">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        <div>
            <label>Username: <input type="text" name="username" value="admin"></label>
        </div>
        <div>
            <label>Password: <input type="password" name="password" value="AdminPassword123!"></label>
        </div>
        <button type="submit">Test Login</button>
    </form>
    """)
    
    return HttpResponse("<br>".join(response))

def test_login(request):
    """Test login functionality directly"""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login successful
            login(request, user)
            return HttpResponse(f"<p style='color:green'>Login successful for {username}! User is authenticated.</p><a href='/'>Go to home page</a>")
        else:
            # Login failed
            return HttpResponse(f"<p style='color:red'>Login failed for {username}. Wrong credentials or authentication backend issue.</p>")
    
    return HttpResponse("Method not allowed", status=405)

def direct_login(request):
    """Direct login view that bypasses potential issues"""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return HttpResponse("Login failed. Wrong credentials.")
    
    return HttpResponse("""
    <h1>Emergency Login</h1>
    <form method="post">
        <div>Username: <input type="text" name="username" value="admin"></div>
        <div>Password: <input type="password" name="password"></div>
        <button type="submit">Login Now</button>
    </form>
    """)