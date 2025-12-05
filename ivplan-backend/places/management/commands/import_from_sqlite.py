from django.core.management.base import BaseCommand
import sqlite3
from places.models import Place

class Command(BaseCommand):
    help = "Import old SQLite data (places) into PostgreSQL"

    def handle(self, *args, **kwargs):
        conn = sqlite3.connect("db.sqlite3")
        cursor = conn.cursor()

        # Get column names in SQLite table
        cursor.execute("PRAGMA table_info(places_place);")
        columns = [col[1] for col in cursor.fetchall()]
        print("SQLite Columns:", columns)

        # Build dynamic query only for columns that exist
        valid_cols = []
        for col in ["name", "address", "category", "latitude", "longitude", "image_url"]:
            if col in columns:
                valid_cols.append(col)

        sql = f"SELECT {', '.join(valid_cols)} FROM places_place"
        print("Executing:", sql)

        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        count = 0

        for row in rows:
            data = dict(zip(valid_cols, row))

            Place.objects.update_or_create(
                name=data.get("name", ""),
                defaults={
                    "address": data.get("address", "") or "",
                    "category": data.get("category", "") or "",
                    "latitude": data.get("latitude", 0),
                    "longitude": data.get("longitude", 0),
                    "image_url": data.get("image_url", "") or "",
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} places from SQLite → PostgreSQL"))













