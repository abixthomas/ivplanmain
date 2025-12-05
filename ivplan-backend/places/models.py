from django.db import models

class Place(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)

    latitude = models.FloatField()
    longitude = models.FloatField()

    image_url = models.URLField(blank=True)

    # ⭐ Automatic AI + Trending engine uses this
    popularity_score = models.FloatField(default=0)

    def __str__(self):
        return self.name
