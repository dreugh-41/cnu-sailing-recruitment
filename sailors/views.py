from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import School, RegattaType, Regatta, Sailor, Result, InterestedSailor
from django.contrib import messages
from django.http import JsonResponse
import requests
from bs4 import BeautifulSoup
import re
import time

@login_required
def home(request):
    """View function for the home page"""
    # Get counts for the dashboard
    sailor_count = Sailor.objects.count()
    regatta_count = Regatta.objects.count()
    school_count = School.objects.count()
    
    context = {
        'sailor_count': sailor_count,
        'regatta_count': regatta_count,
        'school_count': school_count,
    }
    
    return render(request, 'sailors/home.html', context)

@login_required
def sailor_list(request):
    """View function for the sailor list page with filtering"""
    # Get filter parameters
    grad_year_filter = request.GET.get('grad_year', '')
    
    # Start with all sailors ordered by ELO rating
    sailors = Sailor.objects.all().order_by('-elo_rating')
    
    # Apply graduation year filter if provided
    if grad_year_filter:
        # Filter sailors by name containing the graduation year
        sailors = sailors.filter(name__contains=grad_year_filter)
    
    # Prefetch related results to avoid N+1 query problem
    sailors = sailors.prefetch_related(
        'result_set',
        'result_set__regatta',
    )

     # Get IDs of interested sailors
    interested_sailor_ids = set(InterestedSailor.objects.values_list('sailor_id', flat=True))
    
    # Extract graduation years and determine primary position for each sailor
    sailor_data = []
    all_grad_years = set()
    
    for sailor in sailors:
        # Extract grad year from name like "Anton Schmid '26"
        grad_year = "-"
        match = re.search(r"'(\d{2})(\*?)", sailor.name)
        if match:
            grad_year = f"'{match.group(1)}{match.group(2)}"
            all_grad_years.add(grad_year)
        
        # Get clean name without the grad year for display
        clean_name = sailor.name
        if match:
            # Remove grad year from name
            clean_name = sailor.name.replace(f" {grad_year}", "")
        
        # Calculate primary position (skipper or crew)
        results = sailor.result_set.all()
        skipper_count = results.filter(position='Skipper').count()
        crew_count = results.filter(position='Crew').count()
        
        if skipper_count > crew_count:
            primary_position = 'Skipper'
        elif crew_count > skipper_count:
            primary_position = 'Crew'
        else:
            primary_position = 'Both' if skipper_count > 0 else '-'
        
        # Calculate position percentage
        total_results = skipper_count + crew_count
        if total_results > 0:
            if primary_position == 'Skipper':
                position_pct = (skipper_count / total_results) * 100
            elif primary_position == 'Crew':
                position_pct = (crew_count / total_results) * 100
            else:
                position_pct = 50
            position_display = f"{primary_position} ({position_pct:.0f}%)"
        else:
            position_display = "-"
        
        sailor_data.append({
            'sailor': sailor,
            'clean_name': clean_name,
            'grad_year': grad_year,
            'primary_position': position_display,
            'is_interested': sailor.id in interested_sailor_ids
        })
    
    # Sort graduation years
    grad_years = sorted(all_grad_years)
    
    context = {
        'sailor_data': sailor_data,
        'grad_years': grad_years,
        'current_grad_year': grad_year_filter,
    }
    
    return render(request, 'sailors/sailor_list.html', context)

@login_required
def scrape_form(request):
    """View function for the scrape form page"""
    return render(request, 'sailors/scrape_form.html')

@login_required
def execute_scrape(request):
    """Execute the scraper for a given season"""
    if request.method == 'POST':
        season = request.POST.get('season')
        print(f"Received scrape request for season: {season}")
        
        try:
            # Get regattas for the season
            regattas = get_regattas_in_season(season)
            
            if not regattas:
                return JsonResponse({'success': False, 'error': f"No regattas found for season {season}"})
            
            # Process each regatta
            results = {
                'regattas_scraped': 0,
                'sailors_added': 0,
                'results_added': 0
            }
            
            for regatta in regattas:
                try:
                    # Process regatta
                    regatta_results = scrape_regatta(regatta['url'], regatta['name'], season)
                    results['regattas_scraped'] += 1
                    results['sailors_added'] += regatta_results['sailors_added']
                    results['results_added'] += regatta_results['results_added']
                except Exception as e:
                    print(f"Error processing regatta {regatta['name']}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'sailors_added': results['sailors_added'],
                'regattas_scraped': results['regattas_scraped'],
                'results_added': results['results_added']
            })
            
        except Exception as e:
            import traceback
            print(f"Error during scraping: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def reset_database(request):
    """Reset the database by deleting all sailor data"""
    if request.method == 'POST':
        # Delete all data from relevant models
        Result.objects.all().delete()
        Sailor.objects.all().delete()
        Regatta.objects.all().delete()
        School.objects.all().delete()
        RegattaType.objects.all().delete()
        
        # Redirect to home
        return redirect('home')
    
    # Show confirmation page
    return render(request, 'sailors/reset_confirm.html')

def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            # Return to login page with error
            return render(request, 'registration/login.html', {'error': 'Invalid username or password'})
    
    return render(request, 'registration/login.html')

@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')

# Scraper helper functions
def get_regattas_in_season(season):
    """
    Get all regattas in a given season from scores.hssailing.org
    
    Args:
        season (str): Season code (e.g., 'f23', 's24')
    
    Returns:
        list: List of dictionaries with regatta name and URL
    """
    base_url = f"https://scores.hssailing.org/{season}/"
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        
        # Save HTML for debugging
        with open(f"{season}_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved HTML to {season}_debug.html")
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing season page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try multiple selector strategies
    regattas = []
    
    # Strategy 1: Try the table.regatta-list selector
    regatta_links = soup.select("table.regatta-list a")
    print(f"Found {len(regatta_links)} links with table.regatta-list a selector")
    
    if regatta_links:
        for link in regatta_links:
            regatta_name = link.text.strip()
            regatta_path = link['href']
            regatta_url = base_url + regatta_path
            regattas.append({
                'name': regatta_name,
                'url': regatta_url
            })
    else:
        # Strategy 2: Look for links in rows with class row0 or row1
        row_links = []
        rows = soup.select("tr.row0, tr.row1")
        print(f"Found {len(rows)} rows with class row0 or row1")
        
        for row in rows:
            link = row.find('a')
            if link and not link.get('href', '').startswith('/schools/'):
                row_links.append(link)
        
        print(f"Found {len(row_links)} links in those rows")
        
        for link in row_links:
            regatta_name = link.text.strip()
            regatta_path = link.get('href')
            if regatta_path:
                regatta_url = base_url + regatta_path
                regattas.append({
                    'name': regatta_name,
                    'url': regatta_url
                })
    
    print(f"Found {len(regattas)} total regattas")
    return regattas

def determine_regatta_type(name, description=""):
    """
    Determine regatta type based on name and description
    """
    name_lower = name.lower()
    desc_lower = description.lower() if description else ""
    
    if "national championship" in name_lower or "national championship" in desc_lower:
        return "National Championship"
    elif "national" in name_lower and "invitational" in name_lower:
        return "National Invitational"
    elif "district championship" in name_lower:
        return "District Championship"
    elif "district" in name_lower and "qualifier" in name_lower:
        return "District Championship Qualifier"
    elif "district" in name_lower:
        return "In-District"
    elif "state championship" in name_lower:
        return "State Championship"
    elif "league championship" in name_lower:
        return "League Championship"
    elif "league" in name_lower:
        return "In League"
    elif "jv" in name_lower:
        return "JV"
    else:
        return "Promotional"

def extract_sailor_info(td_element):
    """Extract sailor name and graduation year from a td element"""
    if not td_element:
        return None, None
        
    # Find the <a> tag in the td
    a_tag = td_element.find('a')
    if not a_tag:
        return None, None
        
    # Skip links to schools
    if '/schools/' in a_tag.get('href', ''):
        return None, None
        
    text = a_tag.text.strip()
    if not text:
        return None, None
    
    # Special case for "Reserves"
    if text == "Reserves":
        return "Reserves", "N/A"
    
    # Try to match the pattern "Name 'YY" or "Name 'YY*"
    name_match = re.search(r'(.+?)\s+\'(\d+)(\*?)', text)
    if name_match:
        sailor_name = name_match.group(1).strip()
        grad_year = "'" + name_match.group(2)
        if name_match.group(3):  # If there's an asterisk
            grad_year += "*"
        return sailor_name, grad_year
    
    # If no match found, return the text as the name
    return text, None

def scrape_regatta(regatta_url, regatta_name, season):
    """
    Scrape sailor information from a single regatta
    """
    sailors_url = regatta_url + "/sailors"
    print(f"Fetching: {sailors_url}")
    
    try:
        response = requests.get(sailors_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing sailors page: {e}")
        return {'sailors_added': 0, 'results_added': 0}
    
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to extract the date from the regatta page
    regatta_date = None
    try:
        # Look for a time element in the sailors page
        time_element = soup.select_one("time[datetime]")
        
        if time_element and time_element.get('datetime'):
            from datetime import datetime
            # Extract the datetime attribute which has the format YYYY-MM-DDThh:mm
            datetime_str = time_element.get('datetime')
            # Parse just the date part (YYYY-MM-DD)
            date_part = datetime_str.split('T')[0]
            regatta_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            print(f"Extracted date for {regatta_name}: {regatta_date}")
        else:
            # If no time element is found, try to get the main regatta page
            print(f"No date found in sailors page, trying main page for {regatta_name}")
            main_response = requests.get(regatta_url)
            main_response.raise_for_status()
            main_soup = BeautifulSoup(main_response.text, 'html.parser')
            
            # Look for the time element in the main page
            main_time_element = main_soup.select_one("time[datetime]")
            if main_time_element and main_time_element.get('datetime'):
                datetime_str = main_time_element.get('datetime')
                date_part = datetime_str.split('T')[0]
                regatta_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                print(f"Extracted date from main page for {regatta_name}: {regatta_date}")
    except Exception as e:
        print(f"Error extracting date for {regatta_name}: {e}")
    
    # If we couldn't get a date, use current date as fallback
    if not regatta_date:
        from datetime import date
        regatta_date = date.today()
        print(f"Using current date for {regatta_name}: {regatta_date}")
    
    # Determine regatta type
    regatta_type_name = determine_regatta_type(regatta_name)
    is_jv = "jv" in regatta_name.lower()
    
    # Get or create regatta type
    regatta_type, _ = RegattaType.objects.get_or_create(
        name=regatta_type_name,
        defaults={'weight': 1.0}
    )
    
    # Check if this regatta already exists
    existing_regatta = Regatta.objects.filter(url=regatta_url).first()
    
    if existing_regatta:
        # Regatta already exists, just update fields if needed
        if (existing_regatta.name != regatta_name or 
            existing_regatta.date != regatta_date or
            existing_regatta.season != season or
            existing_regatta.regatta_type != regatta_type or
            existing_regatta.is_jv != is_jv):
            
            existing_regatta.name = regatta_name
            existing_regatta.date = regatta_date
            existing_regatta.season = season
            existing_regatta.regatta_type = regatta_type
            existing_regatta.is_jv = is_jv
            existing_regatta.save()
            print(f"Updated regatta: {regatta_name}")
        else:
            print(f"Regatta already exists and is up to date: {regatta_name}")
        
        regatta = existing_regatta
    else:
        # Create new regatta
        regatta = Regatta.objects.create(
            name=regatta_name,
            url=regatta_url,
            date=regatta_date,
            season=season,
            regatta_type=regatta_type,
            is_jv=is_jv
        )
        print(f"Created new regatta: {regatta_name}")
    
    # Stats to return
    stats = {
        'sailors_added': 0,
        'results_added': 0
    }
    
    # Find the sailor table
    table = soup.find('table')
    if not table:
        return stats
    
    # Get tbody which contains all rows
    tbody = table.find('tbody')
    if not tbody:
        return stats
    
    # Get all rows
    rows = tbody.find_all('tr')
    
    current_school = None
    current_division = None
    current_place = None
    
    # Process rows
    for row in rows:
        # Skip rows without class
        if not row.get('class'):
            continue
        
        # Skip rows with 'reserves-row' class
        row_classes = ' '.join(row.get('class', []))
        if 'reserves-row' in row_classes:
            continue
            
        # Get all cells in the row
        cells = row.find_all('td')
        if not cells:
            continue
            
        # Check if this is a topborder row (first type)
        is_topborder = 'topborder' in row_classes
        
        # If this is a topborder row, update the school
        if is_topborder:
            for cell in cells:
                if cell.get('class') and 'schoolname' in cell.get('class'):
                    current_school = cell.text.strip()
        
        # Skip if we don't have a current school
        if not current_school:
            continue
        
        # Check for division and place cells
        has_division_cell = False
        has_rank_cell = False
        row_division = None
        row_place = None
        
        for cell in cells:
            cell_classes = cell.get('class', [])
            if cell_classes:
                if 'division-cell' in cell_classes:
                    has_division_cell = True
                    row_division = cell.text.strip()
                elif 'rank-cell' in cell_classes:
                    has_rank_cell = True
                    row_place = cell.text.strip()
        
        # Update division and place if found
        if row_division and row_place:
            current_division = row_division
            current_place = row_place
        
        # Skip row if we don't have division or place info yet
        if not current_division or not current_place:
            continue
        
        # Determine row type
        is_type1 = is_topborder
        is_type2 = not is_topborder and has_division_cell and has_rank_cell
        is_type3 = not is_topborder and not has_division_cell and not has_rank_cell
        
        # Extract sailor information based on row type
        skipper_cell = None
        crew_cell = None
        
        # Type 1: topborder row with skipper in position 5, crew in position 7
        if is_type1 and len(cells) >= 7:
            skipper_cell = cells[4]  # position 5 (0-indexed)
            crew_cell = cells[6] if len(cells) > 6 else None  # position 7 (0-indexed)
            
        # Type 2: Regular row with skipper in position 3, crew in position 5
        elif is_type2 and len(cells) >= 5:
            skipper_cell = cells[2]  # position 3 (0-indexed)
            crew_cell = cells[4] if len(cells) > 4 else None  # position 5 (0-indexed)
            
        # Type 3: Row without division-cell or rank-cell
        elif is_type3:
            # Check if first or third cell has a sailor link
            if len(cells) >= 1:
                # Always check position 1 (index 0) for skipper
                if cells[0].find('a') and '/sailors/' in cells[0].find('a').get('href', ''):
                    skipper_cell = cells[0]
                
                # Check position 3 (index 2) for crew if it exists
                if len(cells) >= 3 and cells[2].find('a') and '/sailors/' in cells[2].find('a').get('href', ''):
                    crew_cell = cells[2]
        
        # Get or create school
        school, _ = School.objects.get_or_create(name=current_school)
        
        # Process skipper
        if skipper_cell:
            skipper_name, skipper_year = extract_sailor_info(skipper_cell)
            if skipper_name:
                # Store the name with the graduation year
                if skipper_year:
                    # Format the name as "Name 'YY" format
                    full_name = f"{skipper_name} {skipper_year}"
                else:
                    full_name = skipper_name
                
                # Get or create sailor
                sailor, is_new = Sailor.objects.get_or_create(
                    name=full_name,
                    school=school,
                    defaults={'elo_rating': 1000}
                )
                
                if is_new:
                    stats['sailors_added'] += 1
                    
                # Check if result already exists
                existing_result = Result.objects.filter(
                    sailor=sailor,
                    regatta=regatta,
                    division=current_division,
                    position='Skipper'
                ).first()
                
                if existing_result:
                    # Update place if different
                    if existing_result.place != current_place:
                        existing_result.place = current_place
                        existing_result.save()
                        print(f"Updated result for {full_name}")
                else:
                    # Create new result
                    Result.objects.create(
                        sailor=sailor,
                        regatta=regatta,
                        division=current_division,
                        position='Skipper',
                        place=current_place
                    )
                    stats['results_added'] += 1
                    
        # Process crew
        if crew_cell:
            crew_name, crew_year = extract_sailor_info(crew_cell)
            if crew_name:
                # Store the name with the graduation year
                if crew_year:
                    # Format the name as "Name 'YY" format
                    full_name = f"{crew_name} {crew_year}"
                else:
                    full_name = crew_name
                
                # Get or create sailor
                sailor, is_new = Sailor.objects.get_or_create(
                    name=full_name,
                    school=school,
                    defaults={'elo_rating': 1000}
                )
                
                if is_new:
                    stats['sailors_added'] += 1
                    
                # Check if result already exists
                existing_result = Result.objects.filter(
                    sailor=sailor,
                    regatta=regatta,
                    division=current_division,
                    position='Crew'
                ).first()
                
                if existing_result:
                    # Update place if different
                    if existing_result.place != current_place:
                        existing_result.place = current_place
                        existing_result.save()
                        print(f"Updated result for {full_name}")
                else:
                    # Create new result
                    Result.objects.create(
                        sailor=sailor,
                        regatta=regatta,
                        division=current_division,
                        position='Crew',
                        place=current_place
                    )
                    stats['results_added'] += 1
    
    # Update ELO ratings for this regatta
    try:
        from .elo import update_sailor_ratings
        update_sailor_ratings(regatta)
        print(f"Updated ELO ratings for {regatta_name}")
    except Exception as e:
        print(f"Error updating ELO ratings for {regatta_name}: {str(e)}")
    
    return stats

@login_required
def interested_sailors(request):
    """View function for the interested sailors page with tabs by graduation year"""
    # Get all interested sailors
    interested = InterestedSailor.objects.all().select_related('sailor', 'sailor__school')
    
    # Get current date for comparison
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    # Organize sailors by graduation year
    sailors_by_year = {}
    
    for interest in interested:
        sailor = interest.sailor
        
        # Extract grad year
        grad_year = "-"
        match = re.search(r"'(\d{2})(\*?)", sailor.name)
        if match:
            grad_year = f"'{match.group(1)}{match.group(2)}"
        
        # Get clean name
        clean_name = sailor.name
        if match:
            clean_name = sailor.name.replace(f" {grad_year}", "")
        
        # Calculate primary position
        results = sailor.result_set.all()
        skipper_count = results.filter(position='Skipper').count()
        crew_count = results.filter(position='Crew').count()
        
        if skipper_count > crew_count:
            primary_position = 'Skipper'
        elif crew_count > skipper_count:
            primary_position = 'Crew'
        else:
            primary_position = 'Both' if skipper_count > 0 else '-'
        
        # Calculate position percentage
        total_results = skipper_count + crew_count
        if total_results > 0:
            if primary_position == 'Skipper':
                position_pct = (skipper_count / total_results) * 100
            elif primary_position == 'Crew':
                position_pct = (crew_count / total_results) * 100
            else:
                position_pct = 50
            position_display = f"{primary_position} ({position_pct:.0f}%)"
        else:
            position_display = "-"
        
        # Determine row color based on last reached out date
        row_class = ''
        if interest.last_reached_out:
            if interest.last_reached_out >= one_week_ago:
                row_class = 'table-success'  # Less than 1 week - green
            elif interest.last_reached_out >= two_weeks_ago:
                row_class = 'table-warning'  # 1-2 weeks - yellow
            else:
                row_class = 'table-danger'   # More than 2 weeks - red
        
        # Add to sailors_by_year dictionary
        if grad_year not in sailors_by_year:
            sailors_by_year[grad_year] = []
        
        sailors_by_year[grad_year].append({
            'interest': interest,
            'sailor': sailor,
            'clean_name': clean_name,
            'grad_year': grad_year,
            'primary_position': position_display,
            'row_class': row_class
        })
    
    # Prepare data for template - creating a list of years and sailors
    years_and_sailors = []
    
    # Sort the years
    sorted_years = sorted(sailors_by_year.keys())
    
    for year in sorted_years:
        years_and_sailors.append({
            'year': year,
            'sailors': sailors_by_year[year]
        })
    
    context = {
        'years_and_sailors': years_and_sailors,
        'active_year': sorted_years[0] if sorted_years else None,
    }
    
    return render(request, 'sailors/interested_sailors.html', context)

@login_required
def toggle_interest(request, sailor_id):
    """Toggle whether a sailor is marked as interesting"""
    sailor = get_object_or_404(Sailor, id=sailor_id)
    
    # Check if already interested
    interest = InterestedSailor.objects.filter(sailor=sailor).first()
    
    if interest:
        # Remove from interested
        interest.delete()
        action = "removed"
        message = f"Removed {sailor.name} from interested sailors"
    else:
        # Add to interested
        InterestedSailor.objects.create(sailor=sailor)
        action = "added"
        message = f"Added {sailor.name} to interested sailors"
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'action': action,
            'message': message
        })
    
    # For non-AJAX requests, redirect back
    messages.success(request, message)
    referer = request.META.get('HTTP_REFERER')
    if referer and 'interested' in referer:
        return redirect('interested_sailors')
    else:
        return redirect('sailor_list')

@login_required
def update_notes(request, interest_id):
    """Update notes for an interested sailor"""
    interest = get_object_or_404(InterestedSailor, id=interest_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        interest.notes = notes
        interest.save()
        messages.success(request, f"Updated notes for {interest.sailor.name}")
    
    return redirect('interested_sailors')

@login_required
def remove_graduation_year(request):
    """View to select a graduation year to remove"""
    # Get all graduation years from sailor names
    sailors = Sailor.objects.all()
    grad_years = set()
    
    for sailor in sailors:
        match = re.search(r"'(\d{2})(\*?)", sailor.name)
        if match:
            grad_year = f"'{match.group(1)}{match.group(2)}"
            grad_years.add(grad_year)
    
    # Sort graduation years
    grad_years = sorted(grad_years)
    
    if request.method == 'POST':
        grad_year = request.POST.get('grad_year')
        if grad_year:
            return redirect('confirm_remove_year', grad_year=grad_year)
    
    context = {
        'grad_years': grad_years
    }
    
    return render(request, 'sailors/remove_graduation_year.html', context)

@login_required
def confirm_remove_year(request, grad_year):
    """Confirm and execute removal of sailors by graduation year"""
    # Count sailors with this graduation year
    sailors = Sailor.objects.all()
    sailors_to_remove = []
    
    for sailor in sailors:
        match = re.search(r"'(\d{2})(\*?)", sailor.name)
        if match:
            sailor_grad_year = f"'{match.group(1)}{match.group(2)}"
            if sailor_grad_year == grad_year:
                sailors_to_remove.append(sailor)
    
    if request.method == 'POST':
        # Delete all sailors with this graduation year
        for sailor in sailors_to_remove:
            # Delete related InterestedSailor if it exists
            InterestedSailor.objects.filter(sailor=sailor).delete()
            # Delete the sailor (will cascade to results)
            sailor.delete()
        
        messages.success(request, f"Successfully removed {len(sailors_to_remove)} sailors with graduation year {grad_year}")
        return redirect('sailor_list')
    
    context = {
        'grad_year': grad_year,
        'sailor_count': len(sailors_to_remove),
        'sailors': sailors_to_remove
    }
    
    return render(request, 'sailors/confirm_remove_year.html', context)

@login_required
def update_heard_from(request, interest_id):
    """Update the last heard from date for a sailor"""
    interest = get_object_or_404(InterestedSailor, id=interest_id)
    
    # Update the last heard from date to now
    from django.utils import timezone
    interest.last_heard_from = timezone.now()
    interest.save()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'date': interest.last_heard_from.strftime("%Y-%m-%d %H:%M")
        })
    
    messages.success(request, f"Updated last heard from date for {interest.sailor.name}")
    return redirect('interested_sailors')

@login_required
def update_reached_out(request, interest_id):
    """Update the last reached out date for a sailor"""
    interest = get_object_or_404(InterestedSailor, id=interest_id)
    
    # Update the last reached out date to now
    from django.utils import timezone
    interest.last_reached_out = timezone.now()
    interest.save()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'date': interest.last_reached_out.strftime("%Y-%m-%d %H:%M")
        })
    
    messages.success(request, f"Updated last reached out date for {interest.sailor.name}")
    return redirect('interested_sailors')

@login_required
def sailor_profile(request, sailor_id):
    """View function for a specific sailor's profile page"""
    sailor = get_object_or_404(Sailor, id=sailor_id)
    
    # Extract graduation year
    grad_year = "-"
    match = re.search(r"'(\d{2})(\*?)", sailor.name)
    if match:
        grad_year = f"'{match.group(1)}{match.group(2)}"
    
    # Get clean name
    clean_name = sailor.name
    if match:
        clean_name = sailor.name.replace(f" {grad_year}", "")
    
    # Calculate primary position
    results = sailor.result_set.all().select_related('regatta')
    skipper_count = results.filter(position='Skipper').count()
    crew_count = results.filter(position='Crew').count()
    
    if skipper_count > crew_count:
        primary_position = 'Skipper'
    elif crew_count > skipper_count:
        primary_position = 'Crew'
    else:
        primary_position = 'Both' if skipper_count > 0 else '-'
    
    # Calculate position percentage
    total_results = skipper_count + crew_count
    if total_results > 0:
        if primary_position == 'Skipper':
            position_pct = (skipper_count / total_results) * 100
        elif primary_position == 'Crew':
            position_pct = (crew_count / total_results) * 100
        else:
            position_pct = 50
        position_display = f"{primary_position} ({position_pct:.0f}%)"
    else:
        position_display = "-"
    
     # Check if sailor is in interested list
    is_interested = InterestedSailor.objects.filter(sailor=sailor).exists()
    interest = None
    if is_interested:
        interest = InterestedSailor.objects.get(sailor=sailor)
    
    context = {
        'sailor': sailor,
        'clean_name': clean_name,
        'grad_year': grad_year,
        'position_display': position_display,
        'results': results,
        'is_interested': is_interested,
        'interest': interest,
    }
    
    return render(request, 'sailors/sailor_profile.html', context)

@login_required
def update_sailor_info(request, interest_id):
    """Update additional information for an interested sailor"""
    interest = get_object_or_404(InterestedSailor, id=interest_id)
    
    if request.method == 'POST':
        # Update all fields from the form
        interest.phone = request.POST.get('phone', '')
        interest.email = request.POST.get('email', '')
        interest.position = request.POST.get('position', '')
        interest.gpa = request.POST.get('gpa', '')
        interest.major = request.POST.get('major', '')
        interest.size = request.POST.get('size', '')
        interest.hometown = request.POST.get('hometown', '')
        interest.coach_name = request.POST.get('coach_name', '')
        interest.coach_contact = request.POST.get('coach_contact', '')
        interest.references = request.POST.get('references', '')
        
        # Handle file uploads
        if 'transcript' in request.FILES:
            interest.transcript = request.FILES['transcript']
        
        if 'sailing_resume' in request.FILES:
            interest.sailing_resume = request.FILES['sailing_resume']
        
        interest.save()
        
        messages.success(request, f"Updated information for {interest.sailor.name}")
    
    return redirect('sailor_profile', sailor_id=interest.sailor.id)