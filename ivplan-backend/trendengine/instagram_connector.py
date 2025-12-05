import os
import requests
from typing import List, Dict, Any

# env settings - add these to your .env or Windows environment
# INSTAGRAM_BUSINESS_ACCOUNT_ID, FB_PAGE_ACCESS_TOKEN

GRAPH_BASE = "https://graph.facebook.com/v17.0"  # version may change

def fetch_recent_media(ig_user_id: str, access_token: str, limit: int = 50) -> List[Dict[str,Any]]:
    """
    Fetch recent media ids for an Instagram Business account.
    Returns list of media dicts with id, caption, timestamp, permalink, like_count, comments_count.
    If API not accessible, returns [].
    """
    if not ig_user_id or not access_token:
        return []

    # first list media ids
    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,timestamp,permalink,media_type",
        "limit": limit,
        "access_token": access_token,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        media_list = r.json().get("data", [])
    except Exception:
        return []

    results = []
    for m in media_list:
        media_id = m.get("id")
        # fetch engagement fields
        try:
            media_url = f"{GRAPH_BASE}/{media_id}"
            media_params = {
                "fields": "id,caption,timestamp,permalink,like_count,comments_count,insights.metric(impressions,reach)",
                "access_token": access_token,
            }
            mr = requests.get(media_url, params=media_params, timeout=15)
            mr.raise_for_status()
            media_full = mr.json()
        except Exception:
            media_full = m  # fallback minimal

        results.append(media_full)

    return results


def calculate_instagram_score_for_place(place_name: str, media_items: List[Dict]) -> float:
    """
    Very simple: sum( like_count + 2*comments_count ) for media where caption contains place_name (case-insensitive).
    Apply small penalty/boosting heuristics as needed.
    """
    if not place_name or not media_items:
        return 0.0

    score = 0.0
    name_lower = place_name.lower()
    for it in media_items:
        caption = (it.get("caption") or "").lower()
        if name_lower in caption or f"#{name_lower.replace(' ', '')}" in caption:
            likes = int(it.get("like_count", 0) or 0)
            comments = int(it.get("comments_count", 0) or 0)
            score += likes + 2 * comments

    # normalize (simple) - scale down
    return float(score) / 100.0
