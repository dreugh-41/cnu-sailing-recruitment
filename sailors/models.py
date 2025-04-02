# sailors/models.py
from django.db import models

class School(models.Model):
    """High school with sailing team"""
    name = models.CharField(max_length=200, unique=True)
    
    def __str__(self):
        return self.name

class RegattaType(models.Model):
    """Type of regatta with associated weight for ELO calculations"""
    name = models.CharField(max_length=100, unique=True)
    weight = models.FloatField(default=1.0)
    
    def __str__(self):
        return self.name

class Regatta(models.Model):
    """Sailing regatta information"""
    name = models.CharField(max_length=200)
    url = models.URLField(unique=True)
    date = models.DateField()
    season = models.CharField(max_length=10)  # e.g., "f22" or "s23"
    regatta_type = models.ForeignKey(RegattaType, on_delete=models.CASCADE)
    is_jv = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.season})"

class Sailor(models.Model):
    """High school sailor"""
    name = models.CharField(max_length=200)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    elo_rating = models.FloatField(default=1000)  # Starting ELO score
    
    class Meta:
        unique_together = ('name', 'school')
    
    def __str__(self):
        return f"{self.name} - {self.school.name}"

class Result(models.Model):
    sailor = models.ForeignKey(Sailor, on_delete=models.CASCADE)
    regatta = models.ForeignKey(Regatta, on_delete=models.CASCADE)
    division = models.CharField(max_length=5)  # A, B, etc.
    position = models.CharField(max_length=50)  # Skipper, Crew
    place = models.IntegerField()
    elo_change = models.FloatField(default=0.0)  # Add this field
    
    class Meta:
        unique_together = ('sailor', 'regatta', 'division', 'position')
        
    def __str__(self):
        return f"{self.sailor.name} - {self.regatta.name} - Div {self.division} - {self.position}"

# sailors/models.py - update the InterestedSailor model

class InterestedSailor(models.Model):
    """Sailors flagged as interesting for recruitment"""
    sailor = models.OneToOneField(Sailor, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    last_heard_from = models.DateTimeField(blank=True, null=True)
    last_reached_out = models.DateTimeField(blank=True, null=True)
    
    # Additional recruit information
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    position = models.CharField(max_length=20, blank=True, null=True)
    gpa = models.CharField(max_length=10, blank=True, null=True)
    major = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    hometown = models.CharField(max_length=100, blank=True, null=True)
    coach_name = models.CharField(max_length=100, blank=True, null=True)
    coach_contact = models.CharField(max_length=100, blank=True, null=True)
    references = models.TextField(blank=True, null=True)
    
    # File uploads
    transcript = models.FileField(upload_to='transcripts/', blank=True, null=True)
    sailing_resume = models.FileField(upload_to='sailing_resumes/', blank=True, null=True)
    
    def __str__(self):
        return f"Interest in {self.sailor.name}"
    
    @property
    def get_coach_info(self):
        """Get coach information for the sailor's school"""
        try:
            from coaches.models import Coach
            # Try to find a coach for this sailor's school
            coach = Coach.objects.filter(school_name=self.sailor.school.name).first()
            if coach:
                return {
                    'name': coach.full_name,
                    'email': coach.email,
                    'phone': coach.phone,
                    'school_url': coach.school_url
                }
        except (ImportError, Exception):
            pass
        
        # Return empty dict if no coach found or error occurred
        return {
            'name': '',
            'email': '',
            'phone': '',
            'school_url': ''
        }