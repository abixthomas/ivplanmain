# places/urls.py
from django.urls import path
from .views import (
    PlaceListView,
    PlaceSearchView,
    PlaceRadiusView,
    PopularPlacesView,
    CategoryPlacesView,   # <-- NEW
)

urlpatterns = [
    path("", PlaceListView.as_view(), name="place-list"),  
    # /api/places/

    path("search/", PlaceSearchView.as_view(), name="place-search"),  
    # /api/places/search/?search=delhi

    path("nearby/", PlaceRadiusView.as_view(), name="place-radius"),  
    # /api/places/nearby/?lat=28.7&lon=77.1&radius=5

    path("popular/", PopularPlacesView.as_view(), name="popular-places"),  
    # /api/places/popular/

    path("category/", CategoryPlacesView.as_view(), name="category-places"),
    # /api/places/category/?category=restaurant
]
