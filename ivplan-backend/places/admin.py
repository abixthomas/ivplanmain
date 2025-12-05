from django.contrib import admin
from .models import Place

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "latitude", "longitude")
    search_fields = ("name", "category", "address")
