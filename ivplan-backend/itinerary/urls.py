from django.urls import path
from . import views

urlpatterns = [
    path("", views.ItineraryListCreateView.as_view()),
    path("<int:pk>/", views.ItineraryDetailView.as_view()),
]
