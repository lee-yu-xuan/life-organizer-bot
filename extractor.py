import subprocess
import json
import os
import logging
import re

logger = logging.getLogger(__name__)

MODEL = "opencode/big-pickle"


def _run_opencode(prompt: str) -> str:
    """Run OpenCode with the given prompt and return the response."""
    cmd = [
        "opencode", "run",
        "--model", MODEL,
        prompt
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            logger.error(f"OpenCode error: {result.stderr}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("OpenCode timed out")
        return ""
    except Exception as e:
        logger.error(f"OpenCode failed: {e}")
        return ""


def _extract_json_from_text(text: str) -> dict:
    """Try to extract JSON from text that may contain other content."""
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def extract_food_info(caption: str, hashtags: list = None) -> dict:
    """Use OpenCode Big Pickle to extract food info from caption."""
    if not caption:
        return {}

    hashtag_text = ""
    if hashtags:
        hashtag_text = " ".join(f"#{h}" for h in hashtags)

    prompt = f"""Extract restaurant info from this caption. Return ONLY valid JSON with no other text.

Caption: {caption}
Hashtags: {hashtag_text}

Return this exact JSON format:
{{"restaurant_name": "name or null", "city": "city or null", "cuisine": "cuisine type or null", "famous_dishes": ["dish1"], "price_range": "$$ or null", "address": "address or null"}}"""

    response = _run_opencode(prompt)

    if not response:
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    data = _extract_json_from_text(response)

    if not data:
        logger.error(f"Failed to parse OpenCode response: {response}")
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    locations = []
    if data.get("address"):
        locations.append(data["address"])
    elif data.get("restaurant_name") and data.get("city"):
        locations.append(f"{data['restaurant_name']}, {data['city']}")

    return {
        "locations": locations,
        "price": data.get("price_range"),
        "tags": hashtags or [],
        "subcategory": data.get("cuisine"),
        "restaurant_name": data.get("restaurant_name"),
        "cuisine": data.get("cuisine"),
        "famous_dishes": data.get("famous_dishes", []),
        "address": data.get("address"),
        "city": data.get("city"),
    }


def format_food_message(extracted: dict, url: str, platform: str) -> str:
    """Use OpenCode Big Pickle to format a Telegram message for a food place."""
    prompt = f"""Format this restaurant info as a Telegram message. Return ONLY the message text, no other text.

Restaurant: {json.dumps(extracted)}
URL: {url}
Platform: {platform}

Format:
🍔 Food Places

**name**

📍 address

🍽️ Cuisine: cuisine
🍜 Famous Dishes: dishes

💰 Price Range: price

🔗 [View on platform](url)

🗺️ [Open in Google Maps](maps_url)

#tags"""

    response = _run_opencode(prompt)

    if not response:
        return _fallback_format(extracted, url, platform)

    return response


def _fallback_format(extracted: dict, url: str, platform: str) -> str:
    """Fallback formatting if OpenCode fails."""
    name = extracted.get("restaurant_name") or "Unknown Place"
    address = extracted.get("address")
    cuisine = extracted.get("cuisine")
    dishes = extracted.get("famous_dishes", [])
    price = extracted.get("price")

    lines = ["🍔 Food Places\n"]
    lines.append(f"**{name}**\n")

    if address:
        lines.append(f"📍 {address}\n")

    if cuisine:
        lines.append(f"🍽️ Cuisine: {cuisine}")

    if dishes:
        lines.append(f"🍜 Famous Dishes: {', '.join(dishes)}")

    if price:
        lines.append(f"💰 Price Range: {price}")

    lines.append(f"\n🔗 [View on {platform.title()}]({url})")

    if address:
        import urllib.parse
        maps_url = f"https://maps.google.com/?q={urllib.parse.quote(address)}"
        lines.append(f"🗺️ [Open in Google Maps]({maps_url})")

    if cuisine:
        tags = [cuisine.lower()]
        for dish in dishes[:2]:
            tags.append(dish.lower().replace(" ", ""))
        lines.append(f"\n{' '.join(f'#{t}' for t in tags)}")

    return "\n".join(lines)


def extract_date_info(caption, hashtags=None):
    """Extract date idea info from caption."""
    if not caption:
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    locations = []
    price = None

    price_patterns = [
        r'\$\$+', r'cheap', r'affordable', r'budget', r'expensive',
        r'pricey', r'luxury', r'mid-range', r'free',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            price = match.group(0)
            break

    activity_type = None
    activity_keywords = {
        "outdoor": ["park", "garden", "hiking", "beach", "lake", "sunset", "scenic"],
        "indoor": ["museum", "gallery", "cinema", "karaoke", "bowling", "spa"],
        "dining": ["restaurant", "cafe", "rooftop", "bar", "dinner"],
        "entertainment": ["concert", "live music", "movie", "theatre"],
    }
    lower_caption = caption.lower()
    for act_type, keywords in activity_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                activity_type = act_type
                break
        if activity_type:
            break

    return {
        "locations": locations,
        "price": price,
        "tags": hashtags or [],
        "subcategory": activity_type,
    }


def extract_wedding_info(caption, hashtags=None):
    """Extract wedding info from caption."""
    if not caption:
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    locations = []
    price = None

    price_patterns = [
        r'\$\$+', r'cheap', r'affordable', r'budget', r'expensive',
        r'pricey', r'luxury', r'mid-range', r'free',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            price = match.group(0)
            break

    service_type = None
    service_keywords = {
        "venue": ["venue", "banquet", "hall", "garden", "chapel"],
        "dress": ["dress", "gown", "suit", "attire"],
        "decoration": ["decoration", "florist", "bouquet", "flower"],
        "photography": ["photographer", "videographer", "photo", "video"],
        "catering": ["catering", "food", "menu", "buffet"],
    }
    lower_caption = caption.lower()
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                service_type = svc_type
                break
        if service_type:
            break

    return {
        "locations": locations,
        "price": price,
        "tags": hashtags or [],
        "subcategory": service_type,
    }


def extract_renovation_info(caption, hashtags=None):
    """Extract renovation info from caption."""
    if not caption:
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    locations = []
    price = None

    price_patterns = [
        r'\$\$+', r'cheap', r'affordable', r'budget', r'expensive',
        r'pricey', r'luxury', r'mid-range', r'free',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            price = match.group(0)
            break

    service_type = None
    service_keywords = {
        "contractor": ["contractor", "builder", "renovation", "remodel"],
        "interior_design": ["interior", "design", "decor", "makeover"],
        "furniture": ["furniture", "sofa", "table", "chair", "cabinet"],
        "kitchen": ["kitchen", "cabinet", "countertop", "appliance"],
        "bathroom": ["bathroom", "shower", "toilet", "vanity"],
        "flooring": ["floor", "tile", "wood", "laminate", "vinyl"],
        "lighting": ["light", "lighting", "lamp", "chandelier"],
    }
    lower_caption = caption.lower()
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                service_type = svc_type
                break
        if service_type:
            break

    return {
        "locations": locations,
        "price": price,
        "tags": hashtags or [],
        "subcategory": service_type,
    }
