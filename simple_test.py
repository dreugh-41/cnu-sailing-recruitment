# simple_test.py
import requests
from bs4 import BeautifulSoup

def test_district_page(url):
    print(f"Testing access to {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Successfully accessed {url}")
        
        # Print basic info
        print(f"Response code: {response.status_code}")
        print(f"Content type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Page size: {len(response.text)} bytes")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links on the page
        all_links = soup.find_all('a')
        print(f"Found {len(all_links)} links on the page")
        
        # Print first 5 links to see what they look like
        for i, link in enumerate(all_links[:5]):
            print(f"Link {i+1}: {link.get('href', 'no href')} - {link.text.strip()}")
        
        # Look for tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on the page")
        
        # If there are tables, look at the structure of the first one
        if tables:
            first_table = tables[0]
            rows = first_table.find_all('tr')
            print(f"First table has {len(rows)} rows")
            
            # Print structure of first 3 rows
            for i, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                print(f"Row {i+1} has {len(cells)} cells")
                for j, cell in enumerate(cells):
                    cell_text = cell.text.strip()
                    links = cell.find_all('a')
                    print(f"  Cell {j+1}: {cell_text[:30]}... [Links: {len(links)}]")
        
    except Exception as e:
        print(f"Error: {e}")

# Test one district URL
test_district_page('https://massa.hssailing.org/schools')