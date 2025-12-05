from django.db import models
from django.utils import timezone
from places.models import Place   # <-- IMPORTANT

class PopularityScore(models.Model):
    
    # Proper relationship to Place
    place = models.OneToOneField(Place, on_delete=models.CASCADE, related_name="popularity")

    score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(default=timezone.now)

    instagram_signal = models.FloatField(default=0.0)
    local_usage_signal = models.FloatField(default=0.0)
    trends_signal = models.FloatField(default=0.0)

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return f"{self.place.name} ({self.score:.2f})"
