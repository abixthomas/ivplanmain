from rest_framework import serializers
from .models import Itinerary, ItineraryItem
from places.serializers import PlaceSerializer

class ItineraryItemSerializer(serializers.ModelSerializer):
    place = PlaceSerializer(read_only=True)

    class Meta:
        model = ItineraryItem
        fields = "__all__"

class ItinerarySerializer(serializers.ModelSerializer):
    items = ItineraryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Itinerary
        fields = "__all__"
