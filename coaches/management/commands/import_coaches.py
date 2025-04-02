# coaches/management/commands/import_coaches.py
from django.core.management.base import BaseCommand
from coaches.models import Coach
import requests
from bs4 import BeautifulSoup
import time
import re

class Command(BaseCommand):
    help = 'Scrape coach information from district websites and import into database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing coach data before import',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing coach data...')
            Coach.objects.all().delete()
        
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
        
        total_schools = 0
        
        # Scrape each district
        for district_url in district_urls:
            schools = self.scrape_schools_from_district(district_url)
            
            # Scrape coach info for each school
            for school in schools:
                self.stdout.write(f"Scraping coach info for: {school['name']}")
                coach_info = self.scrape_coach_info(school['url'])
                
                # Create or update the Coach record
                coach, created = Coach.objects.update_or_create(
                    school_name=school['name'],
                    district=school['district'],
                    defaults={
                        'location': school['location'],
                        'league': school['league'],
                        'first_name': coach_info['first_name'],
                        'last_name': coach_info['last_name'],
                        'phone': coach_info['phone'],
                        'email': coach_info['email'],
                        'school_url': school['url']
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Added: {school['name']}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Updated: {school['name']}"))
                
                total_schools += 1
                
                # Add a small delay to avoid overloading the server
                time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {total_schools} schools"))
    
    def scrape_schools_from_district(self, district_url):
        """
        Scrape school information from a district URL
        Returns a list of dictionaries with school names and detail URLs
        """
        self.stdout.write(f"Scraping district: {district_url}")
        
        try:
            response = requests.get(district_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error accessing district page: {e}"))
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract district name from URL for reference
        district_name = district_url.split('/')[2].split('.')[0].upper()
        
        # Find the main table
        tables = soup.find_all('table')
        if not tables:
            self.stdout.write(self.style.ERROR("No tables found on the page"))
            return []
        
        main_table = tables[0]  # First table contains the schools
        rows = main_table.find_all('tr')
        
        # Skip the header row and any subheading rows
        # The first actual school data starts at the third row (index 2)
        data_rows = rows[2:]
        
        schools = []
        for row in data_rows:
            cells = row.find_all('td')
            if not cells or len(cells) < 1:
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
                
                # Get location if available (usually the second cell)
                location = ""
                if len(cells) > 1:
                    location = cells[1].text.strip()
                
                # Get league if available (usually the third cell)
                league = ""
                if len(cells) > 2:
                    league = cells[2].text.strip()
                
                schools.append({
                    'name': school_name,
                    'url': school_url,
                    'location': location,
                    'league': league,
                    'district': district_name
                })
        
        self.stdout.write(f"Found {len(schools)} schools in {district_url}")
        return schools
    
    def scrape_coach_info(self, school_url):
        """
        Scrape coach information from a school detail page
        Returns a dictionary with coach name, phone, and email
        """
        try:
            response = requests.get(school_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error accessing school page: {e}"))
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
            self.stdout.write(self.style.ERROR("No tables found on the school page"))
            return coach_info
        
        # The main info table should be the first one
        main_table = tables[0]
        rows = main_table.find_all('tr')
        
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
        
        return coach_info