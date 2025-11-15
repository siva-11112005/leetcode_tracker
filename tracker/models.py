from django.db import models
from django.utils import timezone

class TrackedUser(models.Model):
    """Store information about tracked LeetCode users"""
    username = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=200, blank=True)
    
    # Statistics (all normalized to integers)
    total_solved = models.IntegerField(default=0)
    easy_solved = models.IntegerField(default=0)
    medium_solved = models.IntegerField(default=0)
    hard_solved = models.IntegerField(default=0)
    ranking = models.IntegerField(null=True, blank=True)
    contest_rating = models.FloatField(null=True, blank=True)
    
    # Streaks
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    
    # Recent submissions (normalized JSON array)
    recent_submissions = models.JSONField(default=list, blank=True)
    
    # Metadata
    first_tracked = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
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
        """Increment view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def update_stats(self, stats_data: dict):
        """Update cached statistics from normalized stats dict."""
        self.display_name = stats_data.get('display_name', self.username)
        self.total_solved = int(stats_data.get('total_solved', 0) or 0)
        self.easy_solved = int(stats_data.get('easy_solved', 0) or 0)
        self.medium_solved = int(stats_data.get('medium_solved', 0) or 0)
        self.hard_solved = int(stats_data.get('hard_solved', 0) or 0)
        
        ranking = stats_data.get('ranking')
        try:
            self.ranking = int(ranking) if ranking and ranking != 'N/A' else None
        except (ValueError, TypeError):
            self.ranking = None
        
        contest_rating = stats_data.get('contest_rating')
        try:
            self.contest_rating = float(contest_rating) if contest_rating and contest_rating != 'N/A' else None
        except (ValueError, TypeError):
            self.contest_rating = None
        
        try:
            self.current_streak = int(stats_data.get('current_streak', 0) or 0)
        except (ValueError, TypeError):
            self.current_streak = 0
        
        try:
            self.max_streak = int(stats_data.get('max_streak', 0) or 0)
        except (ValueError, TypeError):
            self.max_streak = 0
        
        # Store recent submissions (limit to 50)
        try:
            recs = stats_data.get('recent_submissions', [])
            if isinstance(recs, list):
                self.recent_submissions = recs[:50]
        except Exception:
            self.recent_submissions = []
        
        # Update last_submission timestamp
        try:
            if self.recent_submissions and len(self.recent_submissions) > 0:
                ts = self.recent_submissions[0].get('timestamp')
                if ts:
                    self.last_submission = timezone.datetime.fromtimestamp(
                        int(ts), tz=timezone.utc
                    )
        except Exception:
            pass
        
        self.save()
