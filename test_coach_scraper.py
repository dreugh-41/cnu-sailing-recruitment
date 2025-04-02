# improved_coach_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import re

def scrape_schools_from_district(district_url):
    """
    Scrape school information from a district URL
    Returns a list of dictionaries with school names and detail URLs
    """
    print(f"Scraping district: {district_url}")
    
    try:
        response = requests.get(district_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing district page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main table
    tables = soup.find_all('table')
    if not tables:
        print("No tables found on the page")
        return []
    
    main_table = tables[0]  # First table contains the schools
    rows = main_table.find_all('tr')
    
    # Skip the header row and any subheading rows
    # The first actual school data starts at the third row (index 2)
    data_rows = rows[2:]
    
    schools = []
    for row in data_rows:
        cells = row.find_all('td')
        if not cells:
            continue  # Skip rows without cells
            
        # The school name and link should be in the first cell
        first_cell = cells[0]
        link = first_cell.find('a')
        
        if link:
            school_name = link.text.strip()
            school_url = link.get('href')
            
            # Make sure we have the full URL
            if not school_url.startswith('http'):
                # Extract the base URL from the district URL
                base_url = re.match(r'(https?://[^/]+)', district_url).group(1)
                school_url = base_url + school_url
            
            schools.append({
                'name': school_name,
                'url': school_url
            })
    
    print(f"Found {len(schools)} schools in {district_url}")
    return schools

def scrape_coach_info(school_url):
    """
    Scrape coach information from a school detail page
    Returns a dictionary with coach name, phone, and email
    """
    try:
        response = requests.get(school_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing school page: {e}")
        return {
            'first_name': '<blank>',
            'last_name': '<blank>',
            'phone': '<blank>',
            'email': '<blank>'
        }
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all tables
    tables = soup.find_all('table')
    
    coach_info = {
        'first_name': '<blank>',
        'last_name': '<blank>',
        'phone': '<blank>',
        'email': '<blank>'
    }
    
    if not tables:
        print("No tables found on the school page")
        return coach_info
    
    # The main info table should be the first one
    main_table = tables[0]
    rows = main_table.find_all('tr')
    
    # Print the number of rows for debugging
    print(f"Found {len(rows)} rows in the school info table")
    
    # Look for coach information in the 6th row (index 5)
    if len(rows) >= 6:
        coach_row = rows[5]
        cells = coach_row.find_all('td')
        
        if len(cells) >= 5:
            # Extract just the values, not the field labels
            # Each cell might have a structure like "First Name\nAshley"
            # We want to split and get just the value part
            
            # Process first name
            first_name_text = cells[0].text.strip()
            if '\n' in first_name_text:
                coach_info['first_name'] = first_name_text.split('\n')[-1].strip()
            else:
                coach_info['first_name'] = first_name_text
                
            # Process last name
            last_name_text = cells[1].text.strip()
            if '\n' in last_name_text:
                coach_info['last_name'] = last_name_text.split('\n')[-1].strip()
            else:
                coach_info['last_name'] = last_name_text
                
            # Process phone
            phone_text = cells[3].text.strip()
            if '\n' in phone_text:
                coach_info['phone'] = phone_text.split('\n')[-1].strip()
            else:
                coach_info['phone'] = phone_text
                
            # Process email
            email_text = cells[4].text.strip()
            if '\n' in email_text:
                coach_info['email'] = email_text.split('\n')[-1].strip()
            else:
                coach_info['email'] = email_text
            
            # Print the extracted info for debugging
            print(f"Extracted first name: {coach_info['first_name']}")
            print(f"Extracted last name: {coach_info['last_name']}")
            print(f"Extracted phone: {coach_info['phone']}")
            print(f"Extracted email: {coach_info['email']}")
    
    return coach_info

def main():
    # List of district URLs to scrape
    district_urls = [
        'https://massa.hssailing.org/schools',
        'https://missa.hssailing.org/schools',
        'https://nessa.hssailing.org/schools',
        'https://nwisa.hssailing.org/schools',
        'https://pcisa.hssailing.org/schools',
        'https://saisa.hssailing.org/schools',
        'https://seisa.hssailing.org/schools'
    ]
    
    all_schools_with_coaches = []
    
    # Scrape each district
    for district_url in district_urls:
        schools = scrape_schools_from_district(district_url)
        
        # For testing, limit to first 2 schools per district
        # Remove the slice [:2] to process all schools
        test_schools = schools[:2]
        
        # Scrape coach info for each school
        for school in test_schools:
            print(f"Scraping coach info for: {school['name']}")
            coach_info = scrape_coach_info(school['url'])
            
            school_data = {
                'name': school['name'],
                'url': school['url'],
                'coach_first_name': coach_info['first_name'],
                'coach_last_name': coach_info['last_name'],
                'coach_phone': coach_info['phone'],
                'coach_email': coach_info['email']
            }
            
            all_schools_with_coaches.append(school_data)
            
            # Print to console
            print(f"School: {school_data['name']}")
            print(f"Coach: {school_data['coach_first_name']} {school_data['coach_last_name']}")
            print(f"Phone: {school_data['coach_phone']}")
            print(f"Email: {school_data['coach_email']}")
            print('-' * 50)
            
            # Add a small delay to avoid overloading the server
            time.sleep(1)
    
    # Print final summary
    print(f"Scraped coach information for {len(all_schools_with_coaches)} schools")

if __name__ == "__main__":
    main()