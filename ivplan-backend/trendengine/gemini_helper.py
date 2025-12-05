# trendengine/gemini_helper.py
import os
import json
from typing import List, Dict, Any
import google.generativeai as genai

# initialize the SDK
GENIE_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
if not GENIE_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment. Add it to your .env")

genai.configure(api_key=GENIE_API_KEY)


def build_places_prompt(places: List[Dict[str, Any]], city: str, days: int, category: str, max_per_day: int):
    """
    Build a compact text prompt for Gemini Pro. The model is asked to return strict JSON array.
    """
    # Create a compact candidate list: id | name | lat | lon | category | address
    lines = []
    for p in places:
        # guard and shorten fields to keep prompt small
        pid = p.get("id")
        name = str(p.get("name", "")).replace("\n", " ")[:120]
        lat = p.get("latitude")
        lon = p.get("longitude")
        cat = str(p.get("category", "")).replace("\n", " ")[:40]
        addr = str(p.get("address", "")).replace("\n", " ")[:120]
        lines.append(f"{pid} | {name} | {lat} | {lon} | {cat} | {addr}")

    place_block = "\n".join(lines)
    max_results = max(1, days * max_per_day)

    prompt = f"""
You are an expert travel planner. The user will visit {city} for {days} day(s) and wants places of category: {category}.

You are given a list of candidate places (each line formatted as: id | name | latitude | longitude | category | address).

Select up to {max_results} places that best match the category and make sense for {days} day(s) of visiting. Prioritize variety (not many identical coordinates) and geographic sensibility (no impossible grouping). Consider popularity, uniqueness and ease of visiting.

Return STRICT JSON only — a single JSON array. Each array item must be an object with:
- id (int)
- name (string)
- latitude (float)
- longitude (float)
- score (float between 0 and 100)  <-- optional but recommended
- reason (short string)             <-- optional

Example output (exactly this structure):
[
  {{
    "id": 123,
    "name": "Place Name",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "score": 92.5,
    "reason": "Iconic landmark, short visit time"
  }},
  ...
]

Candidate places:
{place_block}
"""
    return prompt


def call_gemini_rank(places: List[Dict], city: str, days: int, category: str, max_per_day: int = 5):
    """
    Call Gemini Pro to pick & rank places. Returns parsed JSON (list) or raises on parse failure.
    """
    prompt = build_places_prompt(places, city, days, category, max_per_day)

    # Generate with deterministic temperature
    response = genai.generate(
        model=MODEL,
        prompt=prompt,
        temperature=0.0,
        max_output_tokens=1024
    )

    # Extract text: different SDK versions store text in different places.
    text = ""
    if hasattr(response, "text") and response.text:
        text = response.text
    else:
        # try common alternatives
        try:
            # some SDKs wrap choices
            text = response["candidates"][0]["content"][0]["text"]
        except Exception:
            text = str(response)

    # Extract first JSON array in the response for robustness
    first = text.find("[")
    last = text.rfind("]")
    if first == -1 or last == -1:
        raise ValueError(f"Gemini returned no JSON array. Raw response:\n{text}")

    json_text = text[first:last+1]

    parsed = json.loads(json_text)
    return parsed
