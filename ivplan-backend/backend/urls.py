# backend/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/places/", include("places.urls")),
    path("api/itinerary/", include("itinerary.urls")),
    path("api/travel/", include("travel.urls")),
    path("api/ai/", include("trendengine.urls")),   # <-- ensure this line exists
    path("api/trending/", include("trendengine.urls")),  # optional if you used this previously
]
