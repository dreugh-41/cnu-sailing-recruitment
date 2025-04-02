# sailors/elo.py

import math
from datetime import date
from .models import Result, Regatta

def get_current_season():
    """
    Determine the current sailing season based on date
    Returns: season code (e.g., 'f23', 's24')
    """
    today = date.today()
    year = today.year % 100  # Get last two digits of year
    
    # Fall season is August through December
    if 8 <= today.month <= 12:
        return f"f{year}"
    # Spring season is January through July
    else:
        return f"s{year}"

def get_season_weight(season, current_season=None):
    """
    Calculate season weight based on historical influence
    
    Args:
        season (str): The season to calculate weight for (e.g., 'f23')
        current_season (str, optional): Override for current season
    
    Returns:
        float: Weight factor for the season (1.0 for current, 0.9 for previous, etc.)
    """
    if not current_season:
        current_season = get_current_season()
    
    # Extract season type and year
    current_type = current_season[0]  # 'f' or 's'
    current_year = int(current_season[1:])
    
    season_type = season[0]  # 'f' or 's'
    season_year = int(season[1:])
    
    # Calculate number of seasons difference
    seasons_diff = 0
    
    if current_year > season_year:
        # Different years
        full_years_diff = current_year - season_year
        if current_type == 'f' and season_type == 's':
            # Fall current, Spring past (within same calendar year)
            seasons_diff = 2 * full_years_diff - 1
        else:
            seasons_diff = 2 * full_years_diff
    elif current_year == season_year and current_type == 'f' and season_type == 's':
        # Same year, Fall current, Spring past
        seasons_diff = 1
    
    # Apply weight decay (0.1 per season)
    weight = max(0.1, 1.0 - (0.1 * seasons_diff))
    return weight

def get_k_factor(sailor):
    """
    Determine K-factor based on sailor's experience
    
    Args:
        sailor: Sailor object
    
    Returns:
        int: K-factor value
    """
    from .models import Result
    
    # Count total regattas the sailor has participated in
    regatta_count = Result.objects.filter(sailor=sailor).values('regatta').distinct().count()
    
    if regatta_count < 3:
        return 24  # Reduced from 64 to 24 for new sailors
    elif regatta_count < 5:
        return 20  # Reduced from 48 to 20
    elif regatta_count < 10:
        return 16  # Reduced from 32 to 16
    elif regatta_count < 20:
        return 12  # Reduced from 24 to 12
    else:
        return 8   # Reduced from 16 to 8 for experienced sailors

def calculate_elo_change(sailor_elo, opponent_elo, sailor_place, opponent_place, 
                        k_factor=32, fleet_size=20, regatta_weight=1.0, division_weight=1.0, season_weight=1.0):
    """
    Calculate ELO change based on regatta results with all weighting factors
    """
    # Ensure places are integers
    try:
        sailor_place = int(sailor_place)
        opponent_place = int(opponent_place)
    except (ValueError, TypeError):
        return 0
    
    # Determine match outcome based on places
    if sailor_place < opponent_place:  # Lower place is better
        actual_outcome = 1.0  # Win
    elif sailor_place == opponent_place:
        actual_outcome = 0.5  # Tie 
    else:
        actual_outcome = 0.0  # Loss
    
    # Calculate expected outcome using ELO formula
    expected_outcome = 1.0 / (1.0 + 10 ** ((opponent_elo - sailor_elo) / 400.0))
    
    # Apply exponential fleet size adjustment for larger placements
    # This makes the difference between 1st and 2nd more significant than 20th and 21st
    fleet_size_factor = max(5, fleet_size / 4)  # Adjust divisor for steepness
    place_weight = 1.0 / (1.0 + math.exp((sailor_place - 1) / fleet_size_factor))
    
    # Calculate final ELO change with all weights
    combined_weight = regatta_weight * division_weight * season_weight * place_weight
    elo_change = k_factor * combined_weight * (actual_outcome - expected_outcome)
    
    return elo_change

def update_sailor_ratings(regatta):
    """
    Update ELO ratings for all sailors in a regatta
    """
    from .models import Result, Sailor
    
    # Get regatta info
    regatta_weight = regatta.regatta_type.weight
    season = regatta.season
    current_season = get_current_season()
    season_weight = get_season_weight(season, current_season)
    
    # Get divisions in this regatta
    divisions = Result.objects.filter(regatta=regatta).values_list('division', flat=True).distinct()
    
    # Process each division
    for division in divisions:
        # Get all results for this division
        results = Result.objects.filter(regatta=regatta, division=division).select_related('sailor')
        
        # Count fleet size
        fleet_size = results.count()
        
        # Skip if less than 2 sailors
        if fleet_size < 2:
            continue
        
        # Set division weight
        division_weight = 1.2 if division == 'A' else 1.0
        
        # Calculate ELO changes for each sailor
        elo_changes = {}  # Store changes to apply them all at once
        
        for sailor_result in results:
            sailor = sailor_result.sailor
            
            if sailor.id not in elo_changes:
                elo_changes[sailor.id] = 0
            
            # Get K-factor for this sailor
            k_factor = get_k_factor(sailor)
            
            # Compare against every other sailor in division
            for opponent_result in results:
                if sailor_result.sailor.id == opponent_result.sailor.id:
                    continue  # Skip self
                
                elo_change = calculate_elo_change(
                    sailor_elo=sailor.elo_rating,
                    opponent_elo=opponent_result.sailor.elo_rating,
                    sailor_place=sailor_result.place,
                    opponent_place=opponent_result.place,
                    k_factor=k_factor,
                    fleet_size=fleet_size,
                    regatta_weight=regatta_weight,
                    division_weight=division_weight,
                    season_weight=season_weight
                )
                
                elo_changes[sailor.id] += elo_change
        
        # Apply all changes at once and store them
        for sailor_id, change in elo_changes.items():
            sailor = Sailor.objects.get(id=sailor_id)
            sailor.elo_rating += change
            sailor.save()
            
            # Store the ELO change in the result
            sailor_result = results.get(sailor_id=sailor_id)
            sailor_result.elo_change = change
            sailor_result.save()

def apply_inactive_decay():
    """
    Apply rating decay to inactive sailors
    Should be run once per season
    """
    from .models import Sailor, Result
    
    current_season = get_current_season()
    all_sailors = Sailor.objects.all()
    
    for sailor in all_sailors:
        # Check if sailor competed in current season
        competed_this_season = Result.objects.filter(
            sailor=sailor,
            regatta__season=current_season
        ).exists()
        
        if not competed_this_season:
            # Apply 3% decay for inactive sailors
            sailor.elo_rating *= 0.97
            sailor.save()