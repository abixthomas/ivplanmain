from geopy.distance import geodesic
import requests

def get_city_coordinates(city_name):
    """
    Get latitude and longitude for a city using Nominatim (OpenStreetMap).
    """
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={city_name}"

    try:
        response = requests.get(url, headers={"User-Agent": "ivplan-app"})
        data = response.json()

        if len(data) == 0:
            return None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return lat, lon

    except:
        return None


def within_radius(lat1, lon1, lat2, lon2, km):
    """
    Returns True if (lat2, lon2) is within km distance of (lat1, lon1)
    """
    distance = geodesic((lat1, lon1), (lat2, lon2)).km
    return distance <= km
