# coaches/models.py
from django.db import models
from django.utils import timezone

class Coach(models.Model):
    """Model to store coach information"""
    school_name = models.CharField(max_length=200)
    district = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True, null=True)
    league = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    school_url = models.URLField(blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)
    last_reached_out = models.DateTimeField(blank=True, null=True)
    last_heard_from = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['school_name']
        verbose_name_plural = 'Coaches'
    
    def __str__(self):
        return f"{self.school_name} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        """Return the coach's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return "Unknown"
    
    def update_reached_out(self):
        """Update the last reached out date to now"""
        self.last_reached_out = timezone.now()
        self.save()
    
    def update_heard_from(self):
        """Update the last heard from date to now"""
        self.last_heard_from = timezone.now()
        self.save()

    # coaches/models.py (add a method to determine row color)

def get_row_class(self):
    """Return a CSS class based on when coach was last contacted"""
    if not self.last_reached_out:
        return ""
        
    from datetime import timedelta
    from django.utils import timezone
    
    now = timezone.now()
    days_diff = (now - self.last_reached_out).days
    
    if days_diff <= 7:
        return "table-success"
    elif days_diff <= 14:
        return "table-warning"
    else:
        return "table-danger"