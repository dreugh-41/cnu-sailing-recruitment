import requests
from bs4 import BeautifulSoup
import sys
import re
import os
import time

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
    except requests.exceptions.RequestException as e:
        print(f"Error accessing season page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all table rows that have a class (these contain regatta info)
    regatta_rows = soup.select("tr[class]")
    
    regattas = []
    for row in regatta_rows:
        # Find the first td which contains the regatta link
        first_td = row.find('td')
        if first_td:
            link_tag = first_td.find('a')
            if link_tag:
                regatta_name = link_tag.text.strip()
                regatta_path = link_tag['href']
                regatta_url = base_url + regatta_path
                regattas.append({
                    'name': regatta_name,
                    'url': regatta_url
                })
    
    return regattas

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

def scrape_sailors_from_regatta(regatta_url, regatta_name, debug=False):
    """
    Scrape sailor information from a regatta's sailors page
    
    Args:
        regatta_url (str): URL of the regatta
        regatta_name (str): Name of the regatta
        debug (bool): Whether to print debug information
    
    Returns:
        list: List of dictionaries with sailor information
    """
    sailors_url = regatta_url + "/sailors"
    print(f"Fetching: {sailors_url}")
    
    try:
        response = requests.get(sailors_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing sailors page: {e}")
        return []
    
    html_content = response.text
    
    # Save HTML for debugging if needed
    if debug:
        with open(f"regatta_{regatta_name.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Saved HTML to regatta_{regatta_name.replace(' ', '_')}.html")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    sailors = []
    current_school = None
    current_division = None
    current_place = None
    
    # Find the sailor table
    table = soup.find('table')
    if not table:
        print("No table found")
        return []
    
    # Get tbody which contains all rows
    tbody = table.find('tbody')
    if not tbody:
        print("No tbody found")
        return []
    
    # Get all rows
    rows = tbody.find_all('tr')
    print(f"Found {len(rows)} rows in table")
    
    # Process rows
    for i, row in enumerate(rows):
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
                    if debug:
                        print(f"Row {i}: Found school: {current_school}")
                        
        # Skip if we don't have a current school
        if not current_school:
            continue
        
        # For Types 1 and 2, look for division and place cells
        # Also check if row contains any division or rank cells
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
        # Type 1: topborder row
        # Type 2: Has division-cell and rank-cell but not topborder
        # Type 3: No division-cell or rank-cell, not topborder
        is_type1 = is_topborder
        is_type2 = not is_topborder and has_division_cell and has_rank_cell
        is_type3 = not is_topborder and not has_division_cell and not has_rank_cell
        
        if debug:
            print(f"Row {i}: Type1={is_type1}, Type2={is_type2}, Type3={is_type3}")
            
        # Now extract sailor information based on row type
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
        
        # Process skipper
        if skipper_cell:
            skipper_name, skipper_year = extract_sailor_info(skipper_cell)
            if skipper_name:
                sailors.append({
                    'name': skipper_name,
                    'grad_year': skipper_year if skipper_year else 'N/A',
                    'school': current_school,
                    'division': current_division,
                    'place': current_place,
                    'position': 'Skipper',
                    'regatta': regatta_name
                })
                if debug:
                    print(f"Added Skipper: {skipper_name} ({skipper_year})")
                    
        # Process crew
        if crew_cell:
            crew_name, crew_year = extract_sailor_info(crew_cell)
            if crew_name:
                sailors.append({
                    'name': crew_name,
                    'grad_year': crew_year if crew_year else 'N/A',
                    'school': current_school,
                    'division': current_division,
                    'place': current_place,
                    'position': 'Crew',
                    'regatta': regatta_name
                })
                if debug:
                    print(f"Added Crew: {crew_name} ({crew_year})")
    
    return sailors

def process_multiple_regattas(season, max_regattas=5, debug=False):
    """
    Process multiple regattas from a season and save the results to a text file
    
    Args:
        season (str): Season code (e.g., 'f23', 's24')
        max_regattas (int): Maximum number of regattas to process
        debug (bool): Whether to print debug information
    
    Returns:
        list: Combined list of all sailors from processed regattas
    """
    print(f"Fetching regattas for season {season}...")
    regattas = get_regattas_in_season(season)
    
    if not regattas:
        print(f"No regattas found for season {season}")
        return []
    
    print(f"Found {len(regattas)} regattas in {season}. Processing the first {min(max_regattas, len(regattas))}.")
    
    all_sailors = []
    
    # Process each regatta up to the limit
    for i, regatta in enumerate(regattas[:max_regattas]):
        print(f"\nProcessing regatta {i+1}/{min(max_regattas, len(regattas))}: {regatta['name']}")
        sailors = scrape_sailors_from_regatta(regatta['url'], regatta['name'], debug)
        
        if sailors:
            print(f"Found {len(sailors)} sailors in {regatta['name']}")
            all_sailors.extend(sailors)
        else:
            print(f"No sailor data found for {regatta['name']}")
        
        # Wait a bit between requests to be polite to the server
        if i < min(max_regattas, len(regattas)) - 1:
            time.sleep(1)
    
    return all_sailors

def save_sailors_to_file(sailors, filename):
    """
    Save sailor data to a text file
    
    Args:
        sailors (list): List of sailor dictionaries
        filename (str): Name of the output file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Found {len(sailors)} sailor entries:\n\n")
        f.write(f"{'Name':<25} {'Grad Year':<10} {'School':<35} {'Div':<5} {'Place':<7} {'Position':<8} {'Regatta':<40}\n")
        f.write("-" * 130 + "\n")
        
        # Sort by school, division, place, and position
        sailors.sort(key=lambda x: (
            x['school'], 
            x['division'], 
            int(x['place']) if x['place'].isdigit() else 999, 
            0 if x['position'] == 'Skipper' else 1
        ))
        
        for sailor in sailors:
            f.write(f"{sailor['name']:<25} {sailor['grad_year']:<10} {sailor['school']:<35} {sailor['division']:<5} {sailor['place']:<7} {sailor['position']:<8} {sailor['regatta']:<40}\n")
        
        # Add summary statistics
        f.write("\nSailors by school:\n")
        schools = {}
        for sailor in sailors:
            school = sailor['school']
            if school not in schools:
                schools[school] = 0
            schools[school] += 1
        
        for school, count in sorted(schools.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{school}: {count} sailors\n")
        
        # Display totals by position
        skippers = sum(1 for s in sailors if s['position'] == 'Skipper')
        crews = sum(1 for s in sailors if s['position'] == 'Crew')
        f.write(f"\nTotal Skippers: {skippers}\n")
        f.write(f"Total Crews: {crews}\n")
        
        # Display counts by division
        div_a = sum(1 for s in sailors if s['division'] == 'A')
        div_b = sum(1 for s in sailors if s['division'] == 'B')
        f.write(f"Total Division A: {div_a}\n")
        f.write(f"Total Division B: {div_b}\n")
        
        # Count unique regattas
        regattas = set(s['regatta'] for s in sailors)
        f.write(f"\nTotal Regattas: {len(regattas)}\n")
        f.write("Regattas processed:\n")
        for regatta in sorted(regattas):
            f.write(f"- {regatta}\n")

def main():
    # Enable debug mode by default to help troubleshoot
    debug_mode = False
    
    if len(sys.argv) > 1:
        season = sys.argv[1]
    else:
        season = input("Enter season code (e.g., f23, s24): ")
    
    # Number of regattas to process
    max_regattas = 5
    
    # Process multiple regattas
    all_sailors = process_multiple_regattas(season, max_regattas, debug_mode)
    
    if not all_sailors:
        print("No sailor data found for any regatta.")
        return
    
    # Save the data to a file
    output_file = f"{season}_sailors_data.txt"
    save_sailors_to_file(all_sailors, output_file)
    
    print(f"\nProcessed {len(all_sailors)} sailor entries from {season}.")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()