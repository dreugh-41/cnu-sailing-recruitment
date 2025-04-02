# scraper/scraper.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from sailors.models import School, Sailor, Regatta, Result, RegattaType

def determine_regatta_type(name, description=""):
    """
    Determine regatta type based on name and description
    Returns the name of the regatta type
    """
    name_lower = name.lower()
    desc_lower = description.lower() if description else ""
    
    # Check for regatta types in order of precedence
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

def scrape_season(season):
    """
    Scrape an entire season (e.g., 'f23' or 's24')
    Returns a dictionary with statistics about the scraping operation
    """
    # Validate season format
    if not re.match(r'^[fs]\d{2}$', season):
        raise ValueError("Invalid season format. Use 'f' or 's' followed by two-digit year (e.g., 'f23', 's24')")
    
    base_url = f"https://scores.hssailing.org/{season}/"
    
    # Get the season page with all regattas
    try:
        response = requests.get(base_url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error accessing season page: {e}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all regatta links
    regatta_links = soup.select("table.regatta-list a")
    
    if not regatta_links:
        raise Exception(f"No regattas found for season {season}")
    
    # Initialize regatta types if they don't exist
    for regatta_type_name in [
        "National Championship", 
        "National Invitational", 
        "District Championship", 
        "District Championship Qualifier", 
        "In-District", 
        "State Championship", 
        "League Championship", 
        "In League", 
        "JV", 
        "Promotional"
    ]:
        RegattaType.objects.get_or_create(
            name=regatta_type_name,
            defaults={'weight': 1.0}  # Default weight, can be adjusted later
        )
    
    results = {
        'regattas_scraped': 0,
        'regattas_attempted': len(regatta_links),
        'sailors_added': 0,
        'results_added': 0,
        'errors': []
    }
    
    # Process each regatta
    for link in regatta_links:
        regatta_url = base_url + link['href']
        regatta_name = link.text.strip()
        
        try:
            # Get regatta details and results
            regatta_data = scrape_regatta(regatta_url, regatta_name, season)
            
            results['regattas_scraped'] += 1
            results['sailors_added'] += regatta_data['sailors_added']
            results['results_added'] += regatta_data['results_added']
        except Exception as e:
            results['errors'].append(f"{regatta_name}: {str(e)}")
    
    return results

def scrape_regatta(regatta_url, regatta_name, season):
    """
    Scrape a single regatta page
    Returns statistics about sailors and results added
    """
    try:
        response = requests.get(regatta_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error accessing regatta page: {e}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract regatta date
    date_text = soup.select_one("div.regatta-details time")
    regatta_date = datetime.now().date()  # Default to today if date not found
    if date_text:
        try:
            date_str = date_text.text.strip()
            # Try different date formats
            date_formats = [
                "%B %d-%d, %Y",  # "October 12-13, 2023"
                "%B %d, %Y",     # "October 12, 2023"
                "%b %d-%d, %Y",  # "Oct 12-13, 2023"
                "%b %d, %Y",     # "Oct 12, 2023"
            ]
            
            for date_format in date_formats:
                try:
                    regatta_date = datetime.strptime(date_str, date_format).date()
                    break
                except ValueError:
                    continue
        except Exception as e:
            print(f"Error parsing date for {regatta_name}: {e}")
    
    # Extract regatta description
    description = ""
    desc_elem = soup.select_one("div.regatta-details p")
    if desc_elem:
        description = desc_elem.text.strip()
    
    # Determine regatta type
    regatta_type_name = determine_regatta_type(regatta_name, description)
    is_jv = "jv" in regatta_name.lower()
    
    # Get the regatta type
    regatta_type = RegattaType.objects.get(name=regatta_type_name)
    
    # Create regatta record
    regatta, created = Regatta.objects.get_or_create(
        url=regatta_url,
        defaults={
            'name': regatta_name,
            'date': regatta_date,
            'season': season,
            'regatta_type': regatta_type,
            'is_jv': is_jv
        }
    )
    
    # Update the regatta if it wasn't newly created
    if not created:
        regatta.name = regatta_name
        regatta.date = regatta_date
        regatta.season = season
        regatta.regatta_type = regatta_type
        regatta.is_jv = is_jv
        regatta.save()
    
    results = {
        'sailors_added': 0,
        'results_added': 0
    }
    
    # Process divisions (A, B, etc.)
    divisions = soup.select("div.sailors-division")
    
    if not divisions:
        print(f"No division data found for {regatta_name}")
    
    for div in divisions:
        # Get division name (A, B, etc.)
        div_header = div.select_one("h3")
        if not div_header:
            continue
            
        division_name = div_header.text.strip()[:1]  # Get first character (A, B, etc.)
        
        # Find all sailor rows
        sailor_rows = div.select("div.sailors-sailorline")
        
        for row in sailor_rows:
            # Extract school
            school_elem = row.select_one("span.team-name")
            if not school_elem:
                continue
                
            school_name = school_elem.text.strip()
            school, _ = School.objects.get_or_create(name=school_name)
            
            # Extract sailor name and position
            sailor_elem = row.select_one("span.sailor-name")
            if not sailor_elem:
                continue
                
            sailor_text = sailor_elem.text.strip()
            
            # Determine position (skipper or crew)
            position = "Crew"  # Default to crew
            if "skipper" in sailor_text.lower():
                position = "Skipper"
                sailor_name = re.sub(r'\(skipper\)', '', sailor_text, flags=re.IGNORECASE).strip()
            else:
                sailor_name = sailor_text
            
            # Get or create sailor
            sailor, is_new = Sailor.objects.get_or_create(
                name=sailor_name,
                school=school
            )
            
            if is_new:
                results['sailors_added'] += 1
            
            # Extract place
            place_elem = row.select_one("span.sailorline-place")
            place = 99  # Default place if not found
            if place_elem:
                try:
                    place_text = place_elem.text.strip()
                    place = int(place_text)
                except (ValueError, TypeError):
                    pass
            
            # Create or update result
            result, created = Result.objects.get_or_create(
                sailor=sailor,
                regatta=regatta,
                division=division_name,
                position=position,
                defaults={'place': place}
            )
            
            # Update existing result if it wasn't newly created
            if not created:
                result.place = place
                result.save()
            else:
                results['results_added'] += 1
    
    return results