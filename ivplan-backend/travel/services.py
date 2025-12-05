import requests
from django.conf import settings

def get_weather(lat, lon):
    """
    Calls OpenWeatherMap API to get weather info.
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return {"error": "No API key provided in .env"}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    return response.json()
