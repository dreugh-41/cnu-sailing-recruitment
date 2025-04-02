# coaches/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Coach
import string
from django.http import JsonResponse
from django.utils import timezone

# coaches/views.py - update the coach_list view

@login_required
def coach_list(request):
    """View function for displaying all coaches, alphabetically by school"""
    # Get filter parameters
    district_filter = request.GET.get('district', '')
    letter_filter = request.GET.get('letter', '')
    search_filter = request.GET.get('search', '')
    
    # Start with all coaches
    coaches = Coach.objects.all()
    
    # Apply search filter if provided
    if search_filter:
        coaches = coaches.filter(
            models.Q(school_name__icontains=search_filter) | 
            models.Q(first_name__icontains=search_filter) | 
            models.Q(last_name__icontains=search_filter)
        )
    
    # Apply district filter if provided
    if district_filter:
        coaches = coaches.filter(district=district_filter)
    
    # Apply letter filter if provided
    if letter_filter:
        coaches = coaches.filter(school_name__istartswith=letter_filter)
    
    # Get all distinct districts for the filter dropdown
    districts = Coach.objects.values_list('district', flat=True).distinct().order_by('district')
    
    # Create a list of letters for the alphabet filter
    alphabet = list(string.ascii_uppercase)
    
    context = {
        'coaches': coaches,
        'districts': districts,
        'alphabet': alphabet,
        'current_district': district_filter,
        'current_letter': letter_filter,
        'search_query': search_filter,
    }
    
    return render(request, 'coaches/coach_list.html', context)

@login_required
def update_coach_reached_out(request, coach_id):
    """Update the last reached out date for a coach"""
    coach = get_object_or_404(Coach, id=coach_id)
    
    # Update the last reached out date to now
    coach.last_reached_out = timezone.now()
    coach.save()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'date': coach.last_reached_out.strftime("%Y-%m-%d %H:%M")
        })
    
    messages.success(request, f"Updated last reached out date for {coach.school_name}'s coach")
    return redirect('coach_list')

@login_required
def update_coach_heard_from(request, coach_id):
    """Update the last heard from date for a coach"""
    coach = get_object_or_404(Coach, id=coach_id)
    
    # Update the last heard from date to now
    coach.last_heard_from = timezone.now()
    coach.save()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'date': coach.last_heard_from.strftime("%Y-%m-%d %H:%M")
        })
    
    messages.success(request, f"Updated last heard from date for {coach.school_name}'s coach")
    return redirect('coach_list')