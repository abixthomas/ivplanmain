from places.models import Place
from .models import PopularityScore
from .utils import compute_popularity_score

def update_all_popularity():
    places = Place.objects.all()
    for place in places:
        score = compute_popularity_score(place)
        PopularityScore.objects.update_or_create(
            place=place,
            defaults={"score": score}
        )
    return "Popularity scores updated"
