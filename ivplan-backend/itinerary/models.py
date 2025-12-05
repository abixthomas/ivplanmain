from django.db import models
from places.models import Place

class Itinerary(models.Model):
    name = models.CharField(max_length=255, default="My Trip")
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ItineraryItem(models.Model):
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="items")
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    day = models.IntegerField()
    order = models.IntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["day", "order"]
