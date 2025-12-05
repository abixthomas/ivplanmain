from django.urls import path
from .views import (
    PlaceListView,
    PlaceSearchView,
    PlaceRadiusView,
    PopularPlacesView,
)

urlpatterns = [
    path("", PlaceListView.as_view()),                     # /api/places/
    path("search/", PlaceSearchView.as_view()),            # /api/places/search/?search=delhi
    path("nearby/", PlaceRadiusView.as_view()),            # /api/places/nearby/?lat=&lon=&radius=10
    path("popular/", PopularPlacesView.as_view()),         # /api/places/popular/?only_tourist=1
]
