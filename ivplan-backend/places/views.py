# places/views.py
from rest_framework.generics import ListAPIView
from django.db.models import Q, F
from django.db.models.functions import Length
from rest_framework.response import Response
from rest_framework import status
from .models import Place
from .serializers import PlaceSerializer
import math


# -----------------------------------------
# 1️⃣ List all places
# -----------------------------------------
class PlaceListView(ListAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer


# -----------------------------------------
# 2️⃣ Smart Search (Popularity + Relevance)
# -----------------------------------------
class PlaceSearchView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()

        if not search:
            return Place.objects.none()

        queryset = Place.objects.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(category__icontains=search)
        )

        # SMART RELEVANCE FORMULA
        queryset = queryset.annotate(
            name_length=Length("name"),
            relevance_score=(
                1000 - Length("name") + F("popularity_score") * 10.0
            )
        ).order_by("-relevance_score")

        return queryset


# -----------------------------------------
# 3️⃣ Radius-based Search (Geo Filter)
# -----------------------------------------
class PlaceRadiusView(ListAPIView):
    serializer_class = PlaceSerializer

    def get(self, request):
        # Validate required params
        if not request.query_params.get("lat") or not request.query_params.get("lon"):
            return Response(
                {"error": "lat and lon are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            radius = float(request.query_params.get("radius", 10))
        except ValueError:
            return Response(
                {"error": "lat, lon, and radius must be numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        def within_radius(place):
            R = 6371
            dlat = math.radians(place.latitude - lat)
            dlon = math.radians(place.longitude - lon)

            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) *
                 math.cos(math.radians(place.latitude)) *
                 math.sin(dlon / 2) ** 2)

            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
            return distance <= radius

        places_in_radius = [p for p in Place.objects.all() if within_radius(p)]

        serializer = PlaceSerializer(places_in_radius, many=True)
        return Response(serializer.data)


# -----------------------------------------
# 4️⃣ Popular Places (Trending Score)
# -----------------------------------------
class PopularPlacesView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        return Place.objects.order_by("-popularity_score")[:20]


# -----------------------------------------
# 5️⃣ Category-based listings (Hotels, Restaurants, Cafes)
# -----------------------------------------
class CategoryPlacesView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        category = self.request.query_params.get("category", "").strip()

        if not category:
            return Place.objects.none()

        return Place.objects.filter(
            category__icontains=category
        ).order_by("-popularity_score")
