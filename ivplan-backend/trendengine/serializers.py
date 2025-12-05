from rest_framework import serializers
from .models import PopularityScore

class PopularityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopularityScore
        fields = "__all__"
