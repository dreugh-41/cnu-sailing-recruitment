# sailors/management/commands/recalculate_elo.py

from django.core.management.base import BaseCommand
from sailors.models import Sailor, Regatta
from sailors.elo import update_sailor_ratings, get_current_season, apply_inactive_decay

class Command(BaseCommand):
    help = 'Recalculate ELO ratings for all sailors'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--apply-decay',
            action='store_true',
            help='Apply inactive rating decay',
        )
    
    def handle(self, *args, **options):
        # Reset all sailor ratings to 1000
        self.stdout.write('Resetting all ELO ratings to 1000...')
        Sailor.objects.all().update(elo_rating=1000)
        
        # Get all regattas ordered by date
        regattas = Regatta.objects.all().order_by('date', 'id')
        total = regattas.count()
        
        # Process each regatta to update ELO ratings
        for i, regatta in enumerate(regattas):
            self.stdout.write(f'Processing regatta {i+1}/{total}: {regatta.name} ({regatta.season})')
            update_sailor_ratings(regatta)
        
        # Apply decay if requested
        if options['apply_decay']:
            self.stdout.write('Applying rating decay for inactive sailors...')
            apply_inactive_decay()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully recalculated ELO ratings for {Sailor.objects.count()} sailors'))