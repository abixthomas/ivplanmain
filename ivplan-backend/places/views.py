# places/views.py
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Q, F, Value, FloatField, Case, When
from django.db.models.functions import Coalesce
from .models import Place
from .serializers import PlaceSerializer
import math

"""
Improved Place views to prioritize tourist attractions and reduce restaurants noise.
Endpoints supported (examples):
- /api/places/search/?search=delhi                      (text search)
- /api/places/search/?search=delhi&only_tourist=1      (tourist-only)
- /api/places/popular/?only_tourist=1&limit=30         (popular tourist first)
- /api/places/category/?category=restaurant&only_tourist=0
- /api/places/nearby/?lat=28.7&lon=77.1&radius=10
"""

# Keywords/category tokens that strongly indicate a tourist attraction.
TOURIST_KEYWORDS = [
    "museum", "monument", "temple", "fort", "palace", "park", "national park",
    "zoo", "garden", "viewpoint", "beach", "waterfall", "hill", "lake",
    "histor", "heritage", "memorial", "archaeolog", "cathedral", "basilica",
    "shrine", "observatory", "gallery", "monastery", "gurdwara", "stupa",
    "pagoda", "ruins", "fortress", "riverfront", "island", "cave"
]

# Categories that are typically tourist attractions (strings to match in category field)
TOURIST_CATEGORIES = [
    "attraction", "tourism", "museum", "monument", "park", "viewpoint",
    "historic", "heritage", "beach", "waterfall", "palace", "fort"
]

# Categories that are noise for tourist list (we will down-weight these when only_tourist=1)
NOISE_CATEGORIES = [
    "restaurant", "cafe", "bar", "pub", "fast_food", "food_court"
]


def _build_tourism_boost_case():
    """
    Build a Case() expression that returns a tourism boost factor.
    Higher = stronger tourist signal.
    We'll return a float to be added to popularity_score.
    """
    whens = []
    # Strong category matches -> big boost
    for cat in TOURIST_CATEGORIES:
        whens.append(When(category__icontains=cat, then=Value(20.0)))

    # Noise categories -> negative small penalty (only applied if only_tourist)
    for ncat in NOISE_CATEGORIES:
        whens.append(When(category__icontains=ncat, then=Value(-10.0)))

    # Fallback default 0.0
    return Case(*whens, default=Value(0.0), output_field=FloatField())


def _name_desc_keyword_boost():
    """
    Boost based on presence of tourist keywords in name or description or address.
    Each matching keyword gives a small boost.
    """
    whens = []
    for kw in TOURIST_KEYWORDS:
        # check name OR address OR description contains keyword
        whens.append(When(Q(name__icontains=kw) | Q(address__icontains=kw) | Q(description__icontains=kw), then=Value(3.0)))
    return Case(*whens, default=Value(0.0), output_field=FloatField())


# -----------------------------------------
# 1️⃣ List all places (unchanged)
# -----------------------------------------
class PlaceListView(ListAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer


# -----------------------------------------
# 2️⃣ Smart Search (Popularity + Tourist prioritization)
# -----------------------------------------
class PlaceSearchView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        only_tourist = self.request.query_params.get("only_tourist", "0") in ("1", "true", "True")
        boost_tourist = self.request.query_params.get("boost_tourist", "1") in ("1", "true", "True")
        min_score = float(self.request.query_params.get("min_score", -9999))
        limit = int(self.request.query_params.get("limit", 200))

        if not search:
            return Place.objects.none()

        # base filter: text search across name/address/category/description
        qs = Place.objects.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(category__icontains=search) |
            Q(description__icontains=search)
        )

        # apply tourist-only filter if requested (exclude obvious noise categories first)
        if only_tourist:
            # Keep anything that has tourist keywords OR tourist categories (broad)
            tourist_q = Q()
            for kw in TOURIST_KEYWORDS:
                tourist_q |= Q(name__icontains=kw) | Q(address__icontains=kw) | Q(description__icontains=kw)
            for cat in TOURIST_CATEGORIES:
                tourist_q |= Q(category__icontains=cat)
            qs = qs.filter(tourist_q)

        # annotate with boosts
        tourism_boost = _build_tourism_boost_case()
        keyword_boost = _name_desc_keyword_boost()
        # popularity_score may be null — coalesce to 0
        qs = qs.annotate(
            pop_score_coalesced=Coalesce(F("popularity_score"), Value(0.0)),
            tourism_boost=tourism_boost,
            keyword_boost=keyword_boost,
        )

        # combined score = pop_score + (tourism_boost * factor) + keyword_boost
        # allow API param to control boost_tourist weight (we keep fixed small weights)
        if boost_tourist:
            qs = qs.annotate(
                combined_score=F("pop_score_coalesced") + F("tourism_boost") + F("keyword_boost")
            )
        else:
            qs = qs.annotate(combined_score=F("pop_score_coalesced"))

        # filter by min_score if provided
        qs = qs.filter(combined_score__gte=min_score)

        # final ordering by combined_score desc, then popularity
        qs = qs.order_by("-combined_score", "-pop_score_coalesced")

        return qs[:limit]


# -----------------------------------------
# 3️⃣ Radius-based search (Haversine formula)
# -----------------------------------------
class PlaceRadiusView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        # lat & lon required
        lat = float(self.request.query_params.get("lat", 0))
        lon = float(self.request.query_params.get("lon", 0))
        radius = float(self.request.query_params.get("radius", 10))  # km
        only_tourist = self.request.query_params.get("only_tourist", "0") in ("1", "true", "True")

        # Basic bounding box optimization to avoid scanning entire DB
        # lat +/- delta, lon +/- delta (approx)
        # 1 degree lat ≈ 111 km
        delta_lat = radius / 111.0
        # 1 degree lon ≈ 111 * cos(lat) km
        delta_lon = radius / (111.0 * max(0.0001, math.cos(math.radians(lat))))

        bbox_qs = Place.objects.filter(
            latitude__gte=(lat - delta_lat),
            latitude__lte=(lat + delta_lat),
            longitude__gte=(lon - delta_lon),
            longitude__lte=(lon + delta_lon),
        )

        if only_tourist:
            # keep tourist-like ones only
            tourist_q = Q()
            for kw in TOURIST_KEYWORDS:
                tourist_q |= Q(name__icontains=kw) | Q(address__icontains=kw) | Q(description__icontains=kw)
            for cat in TOURIST_CATEGORIES:
                tourist_q |= Q(category__icontains=cat)
            bbox_qs = bbox_qs.filter(tourist_q)

        # compute true Haversine distance and filter
        def within_radius(place):
            R = 6371  # Earth radius km
            dlat = math.radians(place.latitude - lat)
            dlon = math.radians(place.longitude - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) *
                 math.cos(math.radians(place.latitude)) *
                 math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return (R * c) <= radius

        # materialize list and filter precisely
        result = [p for p in bbox_qs if within_radius(p)]

        # Sort result: compute score inline similarly to search
        def compute_score(p):
            pop = p.popularity_score or 0.0
            boost = 0.0
            # category boost
            for cat in TOURIST_CATEGORIES:
                if cat in (p.category or "").lower():
                    boost += 20.0
            # keyword boost
            name_addr_desc = " ".join([str(p.name or ""), str(p.address or ""), str(getattr(p, "description", "") or "")]).lower()
            for kw in TOURIST_KEYWORDS:
                if kw in name_addr_desc:
                    boost += 3.0
            return pop + boost

        result.sort(key=lambda p: compute_score(p), reverse=True)
        return result


# -----------------------------------------
# 4️⃣ Popular places (Trending score)
# -----------------------------------------
class PopularPlacesView(ListAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        only_tourist = self.request.query_params.get("only_tourist", "0") in ("1", "true", "True")
        limit = int(self.request.query_params.get("limit", 20))

        qs = Place.objects.all()

        if only_tourist:
            tourist_q = Q()
            for kw in TOURIST_KEYWORDS:
                tourist_q |= Q(name__icontains=kw) | Q(address__icontains=kw) | Q(description__icontains=kw)
            for cat in TOURIST_CATEGORIES:
                tourist_q |= Q(category__icontains=cat)
            qs = qs.filter(tourist_q)

        # annotate and order
        qs = qs.annotate(pop_score_coalesced=Coalesce(F("popularity_score"), Value(0.0)))
        qs = qs.order_by("-pop_score_coalesced")[:limit]
        return qs
