from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import get_weather

@api_view(["GET"])
def weather_view(request):
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")

    if not lat or not lon:
        return Response({"error": "lat and lon required"}, status=status.HTTP_400_BAD_REQUEST)

    data = get_weather(lat, lon)
    return Response(data)
