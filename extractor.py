import json
import os
import logging
import re
import subprocess

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str) -> str:
    """Call OpenCode CLI headlessly."""
    try:
        result = subprocess.run(
            ["opencode", "run", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.error(f"OpenCode error: {result.stderr}")
            return ""
    except Exception as e:
        logger.error(f"OpenCode subprocess error: {e}")
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


def _regex_extract_food(caption: str, hashtags: list = None) -> dict:
    """Regex-based fallback extraction when API is unavailable."""
    if not caption:
        return {"locations": [], "price": None, "tags": hashtags or [], "subcategory": None}

    restaurant_name = None
    name_match = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name_match:
        restaurant_name = name_match.group(1).strip()

    address = None
    address_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|S\d{6}|Malaysia|KL|Penang|Jakarta|Bali|Bangkok|Tokyo|Seoul))', caption, re.IGNORECASE)
    if address_match:
        address = address_match.group(1).strip()

    city = None
    if address:
        city_match = re.search(r'(Singapore|KL|Kuala Lumpur|Penang|Jakarta|Bali|Bangkok|Tokyo|Seoul)', address, re.IGNORECASE)
        if city_match:
            city = city_match.group(1)

    cuisine = None
    cuisines = ['Japanese', 'Chinese', 'Korean', 'Thai', 'Vietnamese', 'Italian', 'French', 'Indian', 'Mexican', 'American', 'Fusion', 'Peranakan', 'Nyonya', 'Hainanese', 'Cantonese', 'Hokkien', 'Teochew']
    for c in cuisines:
        if c.lower() in caption.lower():
            cuisine = c
            break

    price = None
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        price = price_match.group(1)
    else:
        price_keywords = {'cheap': '$', 'budget': '$', 'affordable': '$', 'mid-range': '$$', 'expensive': '$$$', 'luxury': '$$$', 'fine dining': '$$$$'}
        for kw, p in price_keywords.items():
            if kw in caption.lower():
                price = p
                break

    famous_dishes = []
    dish_keywords = ['ramen', 'sushi', 'tempura', 'udon', 'soba', 'curry', 'donburi', 'katsu', 'gyoza', 'takoyaki', 'pad thai', 'pho', 'biryani', 'pizza', 'pasta', 'steak', 'burger', 'tacos', 'burrito']
    for dish in dish_keywords:
        if dish in caption.lower():
            famous_dishes.append(dish.title())

    locations = []
    if address:
        locations.append(address)
    elif restaurant_name and city:
        locations.append(f"{restaurant_name}, {city}")

    return {
        "locations": locations,
        "price": price,
        "tags": hashtags or [],
        "subcategory": cuisine,
        "restaurant_name": restaurant_name,
        "cuisine": cuisine,
        "famous_dishes": famous_dishes,
        "address": address,
        "city": city,
    }


def extract_food_info(caption: str, hashtags: list = None) -> dict:
    """Use OpenCode Zen API to extract food info from caption."""
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

    response = _call_opencode(prompt)

    if not response:
        logger.warning("OpenCode failed, using regex fallback")
        return _regex_extract_food(caption, hashtags)

    data = _extract_json_from_text(response)

    if not data:
        logger.error(f"Failed to parse API response: {response}")
        return _regex_extract_food(caption, hashtags)

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
    """Use OpenCode Zen API to format a Telegram message for a food place."""
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

    response = _call_opencode(prompt)

    if not response:
        logger.warning("OpenCode formatting failed, using Python fallback")
        return _fallback_format(extracted, url, platform)

    return response


def _fallback_format(extracted: dict, url: str, platform: str) -> str:
    """Fallback formatting if API fails."""
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
    """Extract date idea info from caption using OpenCode."""
    if not caption:
        return {}

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    prompt = f"""Extract date idea info from this caption. Return ONLY valid JSON.

Caption: {caption}
Hashtags: {hashtag_text}

Activity types: outdoor, indoor, dining, entertainment, adventure, relaxation

Return this exact JSON format:
{{"venue_name": "name or null", "activity_type": "one of the activity types above or null", "description": "brief description", "price_range": "$$ or null", "address": "address or null", "highlights": ["highlight1"]}}"""

    response = _call_opencode(prompt)

    if not response:
        return _regex_extract_date(caption, hashtags)

    data = _extract_json_from_text(response)
    if not data:
        return _regex_extract_date(caption, hashtags)

    locations = []
    if data.get("address"):
        locations.append(data["address"])
    elif data.get("venue_name"):
        locations.append(data["venue_name"])

    return {
        "locations": locations,
        "price": data.get("price_range"),
        "tags": hashtags or [],
        "subcategory": data.get("activity_type"),
        "venue_name": data.get("venue_name"),
        "description": data.get("description"),
        "highlights": data.get("highlights", []),
        "address": data.get("address"),
    }


def _regex_extract_date(caption, hashtags=None):
    """Fallback regex extraction for date ideas."""
    locations = []
    address_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur))', caption, re.IGNORECASE)
    if address_match:
        locations.append(address_match.group(1).strip())

    price = None
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        price = price_match.group(1)

    activity_type = None
    activity_keywords = {
        "outdoor": ["park", "garden", "hiking", "beach", "lake", "sunset", "scenic", "nature", "outdoor", "view"],
        "indoor": ["museum", "gallery", "cinema", "karaoke", "bowling", "spa", "indoor"],
        "dining": ["restaurant", "cafe", "rooftop", "bar", "dinner", "brunch", "breakfast", "lunch"],
        "entertainment": ["concert", "live music", "movie", "theatre", "show", "comedy", "magic"],
        "adventure": ["adventure", "escape room", "climbing", "zip line", "skydiving", "bungee", "kayak", "cycling"],
        "relaxation": ["spa", "massage", "hot spring", "yoga", "meditation", "wellness"],
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
        "venue_name": None,
        "description": caption[:200] if caption else None,
        "highlights": [],
        "address": locations[0] if locations else None,
    }


def format_date_message(extracted, url, platform):
    """Format a Telegram message for a date idea."""
    prompt = f"""Format this date idea as a Telegram message. Return ONLY the message text.

Date Idea: {json.dumps(extracted)}
URL: {url}

Format:
💕 Date Ideas

**venue name**

📍 address

🎭 Activity: type
📝 Description

💰 Price Range: price

✨ Highlights:
- highlight1
- highlight2

🔗 [View on TikTok](url)

🗺️ [Open in Google Maps](maps_url)"""

    response = _call_opencode(prompt)
    if response:
        return response

    # Fallback formatting
    name = extracted.get("venue_name") or "Date Spot"
    address = extracted.get("address")
    activity = extracted.get("subcategory")
    description = extracted.get("description")
    price = extracted.get("price")
    highlights = extracted.get("highlights", [])

    lines = ["💕 Date Ideas\n"]
    lines.append(f"**{name}**\n")

    if address:
        lines.append(f"📍 {address}\n")

    if activity:
        lines.append(f"🎭 Activity: {activity.title()}")

    if description:
        lines.append(f"📝 {description}\n")

    if price:
        lines.append(f"💰 Price Range: {price}")

    if highlights:
        lines.append("\n✨ Highlights:")
        for h in highlights[:3]:
            lines.append(f"- {h}")

    lines.append(f"\n🔗 [View on TikTok]({url})")

    if address:
        import urllib.parse
        maps_url = f"https://maps.google.com/?q={urllib.parse.quote(address)}"
        lines.append(f"🗺️ [Open in Google Maps]({maps_url})")

    return "\n".join(lines)


def extract_wedding_info(caption, hashtags=None):
    """Extract wedding info from caption using OpenCode."""
    if not caption:
        return {}

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    prompt = f"""Extract wedding service info from this caption. Return ONLY valid JSON.

Caption: {caption}
Hashtags: {hashtag_text}

Service types: venue, photography, videography, decoration, wedding_favors, live_station, catering, dress, emcee, music

Return this exact JSON format:
{{"vendor_name": "name or null", "service_type": "one of the service types above or null", "description": "brief description", "price_range": "$$ or null", "address": "address or null", "highlights": ["highlight1"]}}"""

    response = _call_opencode(prompt)

    if not response:
        return _regex_extract_wedding(caption, hashtags)

    data = _extract_json_from_text(response)
    if not data:
        return _regex_extract_wedding(caption, hashtags)

    locations = []
    if data.get("address"):
        locations.append(data["address"])
    elif data.get("vendor_name"):
        locations.append(data["vendor_name"])

    return {
        "locations": locations,
        "price": data.get("price_range"),
        "tags": hashtags or [],
        "subcategory": data.get("service_type"),
        "vendor_name": data.get("vendor_name"),
        "description": data.get("description"),
        "highlights": data.get("highlights", []),
        "address": data.get("address"),
    }


def _regex_extract_wedding(caption, hashtags=None):
    """Fallback regex extraction for wedding services."""
    locations = []
    address_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur))', caption, re.IGNORECASE)
    if address_match:
        locations.append(address_match.group(1).strip())

    price = None
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        price = price_match.group(1)

    service_type = None
    service_keywords = {
        "venue": ["venue", "banquet", "hall", "garden", "chapel"],
        "photography": ["photographer", "photo", "album", "photoshoot"],
        "videography": ["videographer", "video", "film", "highlight reel"],
        "decoration": ["decoration", "florist", "bouquet", "flower", "floral", "floral arrangement"],
        "wedding_favors": ["favour", "favor", "gift", "souvenir", "door gift", "wedding favour"],
        "live_station": ["live station", "livestation", "interactive", "keychain", "customisation", "customisation station"],
        "catering": ["catering", "food", "menu", "buffet", "cake", "wedding cake"],
        "dress": ["dress", "gown", "suit", "attire", "bride", "wedding dress"],
        "emcee": ["emcee", "mc", "host", "master of ceremony"],
        "music": ["band", "music", "dj", "singer", "live band"],
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
        "vendor_name": None,
        "description": caption[:200] if caption else None,
        "highlights": [],
        "address": locations[0] if locations else None,
    }


def format_wedding_message(extracted, url, platform):
    """Format a Telegram message for a wedding service."""
    prompt = f"""Format this wedding service as a Telegram message. Return ONLY the message text.

Wedding Service: {json.dumps(extracted)}
URL: {url}

Format:
💒 Wedding

**vendor name**

📍 address

💍 Service: type
📝 Description

💰 Price Range: price

✨ Highlights:
- highlight1

🔗 [View on TikTok](url)

🗺️ [Open in Google Maps](maps_url)"""

    response = _call_opencode(prompt)
    if response:
        return response

    # Fallback formatting
    name = extracted.get("vendor_name") or "Wedding Vendor"
    address = extracted.get("address")
    service = extracted.get("subcategory")
    description = extracted.get("description")
    price = extracted.get("price")
    highlights = extracted.get("highlights", [])

    lines = ["💒 Wedding\n"]
    lines.append(f"**{name}**\n")

    if address:
        lines.append(f"📍 {address}\n")

    if service:
        lines.append(f"💍 Service: {service.title()}")

    if description:
        lines.append(f"📝 {description}\n")

    if price:
        lines.append(f"💰 Price Range: {price}")

    if highlights:
        lines.append("\n✨ Highlights:")
        for h in highlights[:3]:
            lines.append(f"- {h}")

    lines.append(f"\n🔗 [View on TikTok]({url})")

    if address:
        import urllib.parse
        maps_url = f"https://maps.google.com/?q={urllib.parse.quote(address)}"
        lines.append(f"🗺️ [Open in Google Maps]({maps_url})")

    return "\n".join(lines)


def extract_renovation_info(caption, hashtags=None):
    """Extract renovation info from caption using OpenCode."""
    if not caption:
        return {}

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    prompt = f"""Extract home renovation info from this caption. Return ONLY valid JSON.

Caption: {caption}
Hashtags: {hashtag_text}

Service types: contractor, interior_design, furniture, kitchen, bathroom, flooring, lighting, painting, plumbing, electrical

Return this exact JSON format:
{{"vendor_name": "name or null", "service_type": "one of the service types above or null", "description": "brief description", "price_range": "$$ or null", "address": "address or null", "highlights": ["highlight1"]}}"""

    response = _call_opencode(prompt)

    if not response:
        return _regex_extract_renovation(caption, hashtags)

    data = _extract_json_from_text(response)
    if not data:
        return _regex_extract_renovation(caption, hashtags)

    locations = []
    if data.get("address"):
        locations.append(data["address"])
    elif data.get("vendor_name"):
        locations.append(data["vendor_name"])

    return {
        "locations": locations,
        "price": data.get("price_range"),
        "tags": hashtags or [],
        "subcategory": data.get("service_type"),
        "vendor_name": data.get("vendor_name"),
        "description": data.get("description"),
        "highlights": data.get("highlights", []),
        "address": data.get("address"),
    }


def _regex_extract_renovation(caption, hashtags=None):
    """Fallback regex extraction for renovation services."""
    locations = []
    address_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur))', caption, re.IGNORECASE)
    if address_match:
        locations.append(address_match.group(1).strip())

    price = None
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        price = price_match.group(1)

    service_type = None
    service_keywords = {
        "contractor": ["contractor", "builder", "renovation", "remodel", "hdb", "bto"],
        "interior_design": ["interior", "design", "decor", "makeover", "id"],
        "furniture": ["furniture", "sofa", "table", "chair", "cabinet", "wardrobe"],
        "kitchen": ["kitchen", "cabinet", "countertop", "appliance", "stove"],
        "bathroom": ["bathroom", "shower", "toilet", "vanity", "basin"],
        "flooring": ["floor", "tile", "wood", "laminate", "vinyl", "parquet"],
        "lighting": ["light", "lighting", "lamp", "chandelier", "led"],
        "painting": ["paint", "painting", "wallpaper", "wall paint"],
        "plumbing": ["plumber", "plumbing", "pipe", "leak", "water heater"],
        "electrical": ["electrician", "electrical", "wiring", "switch", "socket"],
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
        "vendor_name": None,
        "description": caption[:200] if caption else None,
        "highlights": [],
        "address": locations[0] if locations else None,
    }


def format_renovation_message(extracted, url, platform):
    """Format a Telegram message for a renovation service."""
    prompt = f"""Format this renovation service as a Telegram message. Return ONLY the message text.

Renovation Service: {json.dumps(extracted)}
URL: {url}

Format:
🏠 House Renovation

**vendor name**

📍 address

🔧 Service: type
📝 Description

💰 Price Range: price

✨ Highlights:
- highlight1

🔗 [View on TikTok](url)"""

    response = _call_opencode(prompt)
    if response:
        return response

    # Fallback formatting
    name = extracted.get("vendor_name") or "Renovation Service"
    address = extracted.get("address")
    service = extracted.get("subcategory")
    description = extracted.get("description")
    price = extracted.get("price")
    highlights = extracted.get("highlights", [])

    lines = ["🏠 House Renovation\n"]
    lines.append(f"**{name}**\n")

    if address:
        lines.append(f"📍 {address}\n")

    if service:
        lines.append(f"🔧 Service: {service.title()}")

    if description:
        lines.append(f"📝 {description}\n")

    if price:
        lines.append(f"💰 Price Range: {price}")

    if highlights:
        lines.append("\n✨ Highlights:")
        for h in highlights[:3]:
            lines.append(f"- {h}")

    lines.append(f"\n🔗 [View on TikTok]({url})")

    return "\n".join(lines)
