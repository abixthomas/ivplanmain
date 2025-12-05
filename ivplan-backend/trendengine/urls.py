# trendengine/urls.py
from django.urls import path
from .views import AIRecommendView, RouteOptimizeView, MustWatchView, WeatherView

urlpatterns = [
    path("recommend/", AIRecommendView.as_view(), name="ai-recommend"),
    path("route-optimize/", RouteOptimizeView.as_view(), name="route-optimize"),
    path("must-watch/", MustWatchView.as_view(), name="must-watch"),
    path("weather/", WeatherView.as_view(), name="weather"),
]
