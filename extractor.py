import json
import re
import logging
import urllib.parse

logger = logging.getLogger(__name__)


def _regex_extract_food(caption, hashtags=None):
    """Regex extraction for food places."""
    info = {"hashtags": hashtags or []}

    # Restaurant name
    name_match = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name_match:
        info["restaurant_name"] = name_match.group(1).strip()

    # Address
    addr_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur|Malaysia))', caption, re.IGNORECASE)
    if addr_match:
        info["address"] = addr_match.group(1).strip()

    # Cuisine
    cuisines = ['Japanese', 'Chinese', 'Korean', 'Thai', 'Vietnamese', 'Italian', 'French', 'Indian', 'Mexican', 'American', 'Fusion', 'Peranakan']
    for c in cuisines:
        if c.lower() in caption.lower():
            info["cuisine"] = c
            break

    # Price
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        info["price_range"] = price_match.group(1)

    # Dishes
    dishes = []
    for d in ['ramen', 'sushi', 'tempura', 'udon', 'soba', 'pizza', 'pasta', 'steak', 'burger', 'curry', 'pho', 'pad thai']:
        if d in caption.lower():
            dishes.append(d.title())
    info["famous_dishes"] = dishes

    return info


def _regex_extract_date(caption, hashtags=None):
    """Regex extraction for date ideas."""
    info = {"hashtags": hashtags or []}

    # Venue name
    name_match = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name_match:
        info["venue_name"] = name_match.group(1).strip()

    # Address
    addr_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur|Malaysia))', caption, re.IGNORECASE)
    if addr_match:
        info["address"] = addr_match.group(1).strip()

    # Price
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        info["price_range"] = price_match.group(1)

    # Activity type
    activity_keywords = {
        "outdoor": ["park", "garden", "hiking", "beach", "lake", "sunset", "scenic", "nature"],
        "indoor": ["museum", "gallery", "cinema", "karaoke", "bowling", "spa"],
        "dining": ["restaurant", "cafe", "rooftop", "bar", "dinner", "brunch"],
        "entertainment": ["concert", "live music", "movie", "theatre"],
        "adventure": ["escape room", "climbing", "kayak", "cycling"],
        "relaxation": ["spa", "massage", "hot spring", "yoga"],
    }
    lower_caption = caption.lower()
    for act_type, keywords in activity_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                info["activity_type"] = act_type
                break
        if "activity_type" in info:
            break

    info["description"] = caption[:200]
    info["highlights"] = [w for w in caption.split() if len(w) > 3 and w.isalpha()][:5]

    return info


def _regex_extract_wedding(caption, hashtags=None):
    """Regex extraction for wedding services."""
    info = {"hashtags": hashtags or []}

    # Vendor name
    name_match = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name_match:
        info["vendor_name"] = name_match.group(1).strip()

    # Address
    addr_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur|Malaysia))', caption, re.IGNORECASE)
    if addr_match:
        info["address"] = addr_match.group(1).strip()

    # Price
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        info["price_range"] = price_match.group(1)

    # Service type
    service_keywords = {
        "venue": ["venue", "banquet", "hall", "garden", "chapel"],
        "photography": ["photographer", "photo", "album"],
        "videography": ["videographer", "video", "highlight"],
        "decoration": ["decoration", "florist", "bouquet", "flower"],
        "wedding_favors": ["favour", "favor", "gift", "souvenir", "door gift"],
        "live_station": ["live station", "livestation", "keychain", "customisation"],
        "catering": ["catering", "food", "menu", "buffet", "cake"],
        "dress": ["dress", "gown", "suit", "attire"],
        "emcee": ["emcee", "mc", "host"],
        "music": ["band", "music", "dj", "singer"],
    }
    lower_caption = caption.lower()
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                info["service_type"] = svc_type
                break
        if "service_type" in info:
            break

    info["description"] = caption[:200]
    info["highlights"] = [w for w in caption.split() if len(w) > 3 and w.isalpha()][:5]

    return info


def _regex_extract_renovation(caption, hashtags=None):
    """Regex extraction for renovation services."""
    info = {"hashtags": hashtags or []}

    # Vendor name
    name_match = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name_match:
        info["vendor_name"] = name_match.group(1).strip()

    # Address
    addr_match = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur|Malaysia))', caption, re.IGNORECASE)
    if addr_match:
        info["address"] = addr_match.group(1).strip()

    # Price
    price_match = re.search(r'(\${1,4})', caption)
    if price_match:
        info["price_range"] = price_match.group(1)

    # Service type
    service_keywords = {
        "contractor": ["contractor", "builder", "renovation", "remodel", "hdb", "bto"],
        "interior_design": ["interior", "design", "decor", "makeover"],
        "furniture": ["furniture", "sofa", "table", "chair", "cabinet"],
        "kitchen": ["kitchen", "cabinet", "countertop", "appliance"],
        "bathroom": ["bathroom", "shower", "toilet", "vanity"],
        "flooring": ["floor", "tile", "wood", "laminate", "vinyl"],
        "lighting": ["light", "lighting", "lamp", "chandelier"],
        "painting": ["paint", "painting", "wallpaper"],
        "plumbing": ["plumber", "plumbing", "pipe", "water heater"],
        "electrical": ["electrician", "electrical", "wiring", "switch"],
    }
    lower_caption = caption.lower()
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                info["service_type"] = svc_type
                break
        if "service_type" in info:
            break

    info["description"] = caption[:200]
    info["highlights"] = [w for w in caption.split() if len(w) > 3 and w.isalpha()][:5]

    return info
