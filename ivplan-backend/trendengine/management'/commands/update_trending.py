from django.core.management.base import BaseCommand
from trendengine.engine import update_trending_places

class Command(BaseCommand):
    help = "Update trending/popularity scores for places."

    def handle(self, *args, **options):
        update_trending_places()
        self.stdout.write(self.style.SUCCESS("Trending update complete."))
