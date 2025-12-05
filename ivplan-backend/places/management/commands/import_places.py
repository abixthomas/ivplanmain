from django.core.management.base import BaseCommand
import csv
from places.models import Place

class Command(BaseCommand):
    help = "Import places from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")

    def handle(self, *args, **kwargs):
        csv_file = kwargs["csv_file"]

        with open(csv_file, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            count = 0
            for row in reader:
                Place.objects.update_or_create(
                    name=row["name"],
                    defaults={
                        "address": row.get("address", ""),
                        "category": row.get("category", ""),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "image_url": row.get("image_url", "")
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} places!"))
