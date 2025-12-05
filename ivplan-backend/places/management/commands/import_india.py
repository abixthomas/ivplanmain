# places/management/commands/import_india.py
import time
import math
import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from places.models import Place

"""
India-wide Overpass importer.

How it works:
- Splits India bounding box into a grid of tiles (lon_step x lat_step in degrees).
- For each tile, runs an Overpass query (tourism/amenity/leisure).
- Inserts/updates Place rows with name, lat, lon, category, address, description.
- Has retry logic, a sleep between requests, and a start index (resume) parameter.

IMPORTANT:
- Don't set very small step with very low sleep or Overpass will rate limit.
- Default step=2.5 degrees is a good balance (about 100-200 tiles). Increase sleep if you get rate-limited.
"""

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Rough India bounding box (minlon, minlat, maxlon, maxlat)
INDIA_BBOX = (68.0, 6.5, 98.5, 36.0)

# Overpass query template (we ask for nodes and ways centers)
OVERPASS_TEMPLATE = """
[out:json][timeout:60];
(
  node["tourism"]({minlat},{minlon},{maxlat},{maxlon});
  way["tourism"]({minlat},{minlon},{maxlat},{maxlon});
  relation["tourism"]({minlat},{minlon},{maxlat},{maxlon});
  node["amenity"~"restaurant|cafe|bar|hotel|guest_house"]({minlat},{minlon},{maxlat},{maxlon});
  way["amenity"~"restaurant|cafe|bar|hotel|guest_house"]({minlat},{minlon},{maxlat},{maxlon});
  relation["amenity"~"restaurant|cafe|bar|hotel|guest_house"]({minlat},{minlon},{maxlat},{maxlon});
  node["leisure"]({minlat},{minlon},{maxlat},{maxlon});
  way["leisure"]({minlat},{minlon},{maxlat},{maxlon});
  relation["leisure"]({minlat},{minlon},{maxlat},{maxlon});
);
out center;
"""


class Command(BaseCommand):
    help = "Import tourist places across India by splitting into tiles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--step",
            type=float,
            default=2.5,
            help="Tile size in degrees (lon/lat). Default 2.5",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=1.2,
            help="Seconds to sleep between Overpass requests (default 1.2). Increase if rate-limited.",
        )
        parser.add_argument(
            "--start",
            type=int,
            default=0,
            help="Start tile index (for resuming).",
        )
        parser.add_argument(
            "--max-tiles",
            type=int,
            default=0,
            help="Limit how many tiles to process (0 = all). Useful for testing.",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="If set, will print extra debug info and not sleep between requests.",
        )

    def handle(self, *args, **options):
        minlon, minlat, maxlon, maxlat = INDIA_BBOX
        step = float(options["step"])
        sleep_sec = float(options["sleep"])
        start_index = int(options["start"])
        max_tiles = int(options["max_tiles"])
        debug = bool(options["debug"])

        lons = self._frange(minlon, maxlon, step)
        lats = self._frange(minlat, maxlat, step)

        tiles = []
        for lon0 in lons:
            for lat0 in lats:
                lon1 = min(lon0 + step, maxlon)
                lat1 = min(lat0 + step, maxlat)
                tiles.append((lon0, lat0, lon1, lat1))

        total_tiles = len(tiles)
        self.stdout.write(self.style.NOTICE(f"India importer: {total_tiles} tiles (step={step})."))
        if start_index >= total_tiles:
            self.stdout.write(self.style.ERROR("Start index >= total tiles. Nothing to do."))
            return

        end_index = total_tiles if max_tiles == 0 else min(total_tiles, start_index + max_tiles)

        for idx in range(start_index, end_index):
            lon0, lat0, lon1, lat1 = tiles[idx]
            bbox_str = f"{lon0},{lat0},{lon1},{lat1}"
            self.stdout.write(self.style.WARNING(f"[{idx+1}/{total_tiles}] Processing tile bbox: {bbox_str}"))

            try:
                self._process_tile(lon0, lat0, lon1, lat1, debug=debug)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Tile {idx} failed: {e}"))
            # Respectful sleep to avoid rate limits
            if not debug:
                time.sleep(sleep_sec)

        self.stdout.write(self.style.SUCCESS("India import complete."))

    def _process_tile(self, lon0, lat0, lon1, lat1, debug=False):
        query = OVERPASS_TEMPLATE.format(minlat=lat0, minlon=lon0, maxlat=lat1, maxlon=lon1)
        tries = 0
        max_retries = 3
        while tries < max_retries:
            tries += 1
            try:
                resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
                if resp.status_code != 200:
                    raise RuntimeError(f"Overpass returned status {resp.status_code}")
                data = resp.json()
                elements = data.get("elements", [])
                if debug:
                    self.stdout.write(f"  got {len(elements)} elements")
                self._import_elements(elements)
                return
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Overpass attempt {tries} failed: {exc}"))
                if tries < max_retries:
                    backoff = 2 ** tries
                    self.stdout.write(self.style.WARNING(f"  retrying in {backoff} seconds..."))
                    time.sleep(backoff)
                else:
                    self.stdout.write(self.style.ERROR("  max retries reached for this tile. Skipping."))
                    return

    def _import_elements(self, elements):
        count = 0
        for el in elements:
            tags = el.get("tags", {}) or {}
            name = tags.get("name")
            if not name:
                continue

            # Determine coordinates: node has lat/lon; way/relation have center
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue

            # Build a source-based place_id (unique-ish)
            osm_id = el.get("id")
            osm_type = el.get("type")
            source_id = f"osm-{osm_type}-{osm_id}"

            category = tags.get("tourism") or tags.get("amenity") or tags.get("leisure") or ""
            description = tags.get("description", "")
            address = tags.get("addr:full") or tags.get("addr:street") or tags.get("addr:housenumber") or ""

            # Use update_or_create based on source_id OR (name+lat+lon) fallback
            defaults = {
                "category": category,
                "description": description,
                "address": address,
                "latitude": float(lat),
                "longitude": float(lon),
            }

            # If your Place model has a place_id or unique field, prefer that. Otherwise use name+coords.
            # This code attempts to use 'place_id' if the model has it, else falls back to name/coords.
            try:
                # Try update_or_create by place_id field if exists
                if hasattr(Place, "place_id"):
                    Place.objects.update_or_create(place_id=source_id, defaults={**defaults, "name": name})
                else:
                    Place.objects.update_or_create(
                        name=name, latitude=float(lat), longitude=float(lon), defaults=defaults
                    )
                count += 1
            except IntegrityError:
                # Rare race/unique issues — ignore and continue
                continue
            except Exception as e:
                # Log and continue
                self.stdout.write(self.style.ERROR(f"    Error saving place {name}: {e}"))
                continue

        if count:
            self.stdout.write(self.style.SUCCESS(f"    Imported/updated {count} places from tile."))

    def _frange(self, start, stop, step):
        # inclusive-friendly floating range
        vals = []
        cur = start
        # small safe rounding to avoid infinite loops
        max_iter = 10000
        i = 0
        while cur < stop - 1e-9 and i < max_iter:
            vals.append(round(cur, 6))
            cur += step
            i += 1
        # ensure last tile includes the stop boundary
        if not vals or vals[-1] < stop - 1e-9:
            vals.append(round(stop - step if stop - step > start else start, 6))
        return vals
