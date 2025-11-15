from django.db import models
from django.utils import timezone

class TrackedUser(models.Model):
    """
    Store information about tracked LeetCode users
    """
    username = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=200, blank=True)
    
    # Statistics (cached for performance)
    total_solved = models.IntegerField(default=0)
    easy_solved = models.IntegerField(default=0)
    medium_solved = models.IntegerField(default=0)
    hard_solved = models.IntegerField(default=0)
    ranking = models.IntegerField(null=True, blank=True)
    contest_rating = models.FloatField(null=True, blank=True)
    
    # Metadata
    first_tracked = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    # Timestamp of the user's most recent submission (if available)
    last_submission = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-view_count', '-total_solved']
        indexes = [
            models.Index(fields=['-view_count']),
            models.Index(fields=['-total_solved']),
        ]
    
    def __str__(self):
        return f"{self.display_name or self.username} ({self.total_solved} solved)"
    
    def increment_views(self):
        """Increment view count when profile is visited"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def update_stats(self, stats_data):
        """Update cached statistics from API response"""
        self.display_name = stats_data.get('display_name', self.username)
        self.total_solved = stats_data.get('total_solved', 0)
        self.easy_solved = stats_data.get('easy', 0)
        self.medium_solved = stats_data.get('medium', 0)
        self.hard_solved = stats_data.get('hard', 0)
        self.ranking = stats_data.get('ranking') if stats_data.get('ranking') != 'N/A' else None
        
        # Update contest rating - ensure it's stored as a number or None
        contest_rating = stats_data.get('contest_rating')
        if contest_rating != 'N/A' and contest_rating is not None:
            try:
                self.contest_rating = float(contest_rating) if contest_rating != 'N/A' else None
            except (ValueError, TypeError):
                self.contest_rating = None
        else:
            self.contest_rating = None

        # Update last_submission if recent_submissions present
        recent = stats_data.get('recent_submissions')
        if recent and isinstance(recent, list) and len(recent) > 0:
            try:
                ts = recent[0].get('timestamp')
                if ts:
                    # timestamp is unix seconds
                    self.last_submission = timezone.datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except Exception:
                pass

        self.save()