from math import radians, sin, cos, sqrt, atan2

def within_radius(lat1, lon1, lat2, lon2, radius_km):
    """
    Returns True if (lat2, lon2) is within 'radius_km' of (lat1, lon1)
    """

    R = 6371  # Earth radius km

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    distance = R * c

    return distance <= radius_km


def get_city_coordinates(city: str):
    """
    Placeholder so backend doesn't break.
    Later we will replace with real geocoding (OpenCage or Nominatim)
    """

    # fallback values
    sample_cities = {
        "delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "chennai": (13.0827, 80.2707),
        "bangalore": (12.9716, 77.5946),
    }

    city = city.lower()
    return sample_cities.get(city, (20.5937, 78.9629))  # default → center of India
