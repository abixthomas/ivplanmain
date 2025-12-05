# trendengine/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Q
from places.models import Place
from trendengine.models import PopularityScore
import math
import json
import logging
import requests

logger = logging.getLogger(__name__)


class AIRecommendView(APIView):
    """
    GET /api/ai/recommend/?city=Delhi&days=2&category=restaurant&limit=5
    Uses Gemini if GEMINI_API_KEY present; falls back to popularity_score.
    """

    def get(self, request):
        city = request.GET.get("city", "").strip()
        try:
            days = int(request.GET.get("days", 2))
        except:
            days = 2

        category = request.GET.get("category", "").strip()
        try:
            limit = int(request.GET.get("limit", 5))
        except:
            limit = 5

        # Base queryset
        qs = Place.objects.all()

        if city:
            qs = qs.filter(Q(name__icontains=city) | Q(address__icontains=city))

        if category:
            qs = qs.filter(category__icontains=category)

        # Order first
        qs = qs.order_by("-popularity_score")

        # Limit to a reasonable working set (slice -> convert to list to avoid reorder errors)
        limited_list = list(qs[:200])

        # Prepare JSON for Gemini
        places_data = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "address": (p.address or "")[:200],
                "lat": p.latitude,
                "lng": p.longitude,
                "popularity_score": p.popularity_score,
            }
            for p in limited_list
        ]

        # GEMINI (optional)
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or None
        gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-pro")

        if gemini_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=gemini_key)
                prompt = (
                    f"You are a travel planner. From the following places in '{city}', "
                    f"choose up to {limit} places best for {days} days. "
                    f"Return STRICT JSON array like "
                    f"[{{'id':int,'name':str,'reason':str,'lat':float,'lng':float,'score':float}}].\n\n"
                    f"Places:\n{json.dumps(places_data)}"
                )
                model = genai.GenerativeModel(gemini_model)
                response = model.generate_content(prompt)

                raw = (getattr(response, "text", "") or "").strip()
                clean = raw.replace("```json", "").replace("```", "").strip()

                try:
                    data = json.loads(clean)
                except Exception:
                    # Try to extract first JSON array in text
                    import re

                    m = re.search(r"(\[.*\])", clean, re.S)
                    data = json.loads(m.group(1)) if m else []

                if isinstance(data, list):
                    return Response(data[:limit])

            except Exception as e:
                logger.exception("Gemini failed: %s", e)

        # Fallback: top by popularity score from limited_list
        fallback = sorted(limited_list, key=lambda p: p.popularity_score, reverse=True)[:limit]
        data = [
            {
                "id": p.id,
                "name": p.name,
                "reason": "Popular choice",
                "lat": p.latitude,
                "lng": p.longitude,
                "score": p.popularity_score,
            }
            for p in fallback
        ]
        return Response(data)


class RouteOptimizeView(APIView):
    """
    POST /api/ai/route-optimize/
    Body:
    {
      "places": [
         {"id":1, "lat":28.7, "lng":77.1},
         {"id":2, "lat":28.6, "lng":77.2}
       ]
    }
    Returns a simple nearest-neighbour optimized route.
    """

    def post(self, request):
        places = request.data.get("places", [])
        if not isinstance(places, list) or len(places) < 2:
            return Response({"error": "Need at least 2 places"}, status=400)

        def haversine(a, b):
            R = 6371.0
            lat1, lon1 = math.radians(a["lat"]), math.radians(a["lng"])
            lat2, lon2 = math.radians(b["lat"]), math.radians(b["lng"])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            aa = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))
            return R * c

        unvisited = places.copy()
        path = [unvisited.pop(0)]  # start at first place provided
        while unvisited:
            next_p = min(unvisited, key=lambda p: haversine(path[-1], p))
            path.append(next_p)
            unvisited.remove(next_p)

        return Response({"optimized_route": path})


class MustWatchView(APIView):
    """
    GET /api/ai/must-watch/?city=Delhi&limit=10
    Returns top places in the city by popularity_score.
    """

    def get(self, request):
        city = request.GET.get("city", "").strip()
        try:
            limit = int(request.GET.get("limit", 10))
        except:
            limit = 10

        qs = Place.objects.all()
        if city:
            qs = qs.filter(Q(name__icontains=city) | Q(address__icontains=city))
        qs = qs.order_by("-popularity_score")[:limit]
        data = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "lat": p.latitude,
                "lng": p.longitude,
                "score": p.popularity_score,
                "address": p.address,
            }
            for p in qs
        ]
        return Response(data)


class WeatherView(APIView):
    """
    GET /api/ai/weather/?lat=12.9&lng=77.6
    Uses OpenWeatherMap API (OPENWEATHER_API_KEY must be set in env)
    """

    def get(self, request):
        try:
            lat = float(request.GET.get("lat"))
            lng = float(request.GET.get("lng"))
        except Exception:
            return Response({"error": "lat and lng required"}, status=400)

        key = getattr(settings, "OPENWEATHER_API_KEY", None) or None
        if not key:
            return Response({"error": "OPENWEATHER_API_KEY not configured"}, status=500)

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lng, "appid": key, "units": "metric"}
        try:
            resp = requests.get(url, params=params, timeout=8)
            resp.raise_for_status()
            return Response(resp.json())
        except Exception as e:
            logger.exception("Weather fetch failed: %s", e)
            return Response({"error": "weather fetch failed"}, status=500)
