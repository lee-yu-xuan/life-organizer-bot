import re
import spacy

nlp = spacy.load("en_core_web_sm")

FOOD_KEYWORDS = [
    "restaurant", "cafe", "coffee", "tea", "bar", "pub", "bistro", "diner",
    "noodle", "ramen", "sushi", "pizza", "burger", "taco", "curry",
    "bakery", "dessert", "ice cream", "cake", "brunch", "breakfast",
    "lunch", "dinner", "food", "eat", "drinks", "yummy", "delicious",
    "must try", "hidden gem", "best", "must-try", "foodie", "meal",
    "chef", "menu", "taste", "flavor", "spicy", "sweet", "savory",
]

DATE_KEYWORDS = [
    "date", "couple", "romantic", "sunset", "scenic", "view",
    "rooftop", "lakeside", "beach", "park", "garden", "museum",
    "gallery", "cinema", "movie", "concert", "live music", "karaoke",
    "bowling", "ice skating", "hiking", "boat", "cruise", "spa",
    "night out", "date night", "together", "couple goals",
]

WEDDING_KEYWORDS = [
    "wedding", "bride", "groom", "ceremony", "reception", "venue",
    "dress", "gown", "suit", "florist", "bouquet", "decoration",
    "catering", "photographer", "videographer", "invitation",
    "honeymoon", "engagement", "ring", "vow", "banquet",
]

RENOVATION_KEYWORDS = [
    "renovation", "remodel", "contractor", "interior", "design",
    "furniture", "kitchen", "bathroom", "bedroom", "living room",
    "paint", "floor", "tile", "lighting", "plumbing", "electrical",
    "architect", "builder", "home improvement", "diy", "makeover",
    "decor", "minimalist", "modern", "scandinavian", "industrial",
]


def extract_location_from_caption(caption):
    if not caption:
        return None

    pin_match = re.search(r'📍\s*(.+?)(?:\n|#|$)', caption)
    if pin_match:
        return pin_match.group(1).strip()

    at_match = re.search(r'(?:at|@)\s+([A-Z][A-Za-z\s&\'-]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Dr|Lane|Way|Pl|Place|Ct|Court|Sq|Square)\b[^,]*(?:,\s*[^,]+)*)', caption)
    if at_match:
        return at_match.group(1).strip()

    address_match = re.search(r'(\d+[\w\s]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Dr|Lane|Way|Pl|Place|Ct|Court|Sq|Square)[^,]*(?:,\s*[A-Za-z\s]+(?:\d{6})?)?)', caption)
    if address_match:
        return address_match.group(1).strip()

    return None


def extract_info(caption, hashtags=None):
    if not caption:
        return {}

    doc = nlp(caption)

    locations = []

    pin_location = extract_location_from_caption(caption)
    if pin_location:
        locations.append(pin_location)

    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC"):
            if ent.text not in [l for l in locations]:
                locations.append(ent.text)

    price = None
    price_patterns = [
        r'\$\$+', r'cheap', r'affordable', r'budget', r'expensive',
        r'pricey', r'luxury', r'mid-range', r'free', r'\d+\s*-\s*\d+\s*(?:k|rm|myr|usd|sgd|\$)',
        r'(?:rm|myr|usd|sgd|\$)\s*\d+',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            price = match.group(0)
            break

    tags = []
    if hashtags:
        tags = [h.lower() for h in hashtags]

    return {
        "locations": locations,
        "price": price,
        "tags": tags,
    }


def extract_food_info(caption, hashtags=None):
    info = extract_info(caption, hashtags)

    cuisine = None
    cuisine_keywords = [
        "japanese", "chinese", "korean", "thai", "vietnamese", "indian",
        "italian", "french", "mexican", "american", "mediterranean",
        "ramen", "sushi", "pizza", "pasta", "curry", "nasi", "mee",
        "dim sum", "bbq", "hotpot", "teppanyaki", "izakaya",
    ]
    lower_caption = caption.lower() if caption else ""
    for c in cuisine_keywords:
        if c in lower_caption:
            cuisine = c
            break

    info["subcategory"] = cuisine
    return info


def extract_date_info(caption, hashtags=None):
    info = extract_info(caption, hashtags)

    activity_type = None
    activity_keywords = {
        "outdoor": ["park", "garden", "hiking", "beach", "lake", "sunset", "scenic"],
        "indoor": ["museum", "gallery", "cinema", "karaoke", "bowling", "spa"],
        "dining": ["restaurant", "cafe", "rooftop", "bar", "dinner"],
        "entertainment": ["concert", "live music", "movie", "theatre"],
    }
    lower_caption = caption.lower() if caption else ""
    for act_type, keywords in activity_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                activity_type = act_type
                break
        if activity_type:
            break

    info["subcategory"] = activity_type
    return info


def extract_wedding_info(caption, hashtags=None):
    info = extract_info(caption, hashtags)

    service_type = None
    service_keywords = {
        "venue": ["venue", "banquet", "hall", "garden", "chapel"],
        "dress": ["dress", "gown", "suit", "attire"],
        "decoration": ["decoration", "florist", "bouquet", "flower"],
        "photography": ["photographer", "videographer", "photo", "video"],
        "catering": ["catering", "food", "menu", "buffet"],
    }
    lower_caption = caption.lower() if caption else ""
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                service_type = svc_type
                break
        if service_type:
            break

    info["subcategory"] = service_type
    return info


def extract_renovation_info(caption, hashtags=None):
    info = extract_info(caption, hashtags)

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
    lower_caption = caption.lower() if caption else ""
    for svc_type, keywords in service_keywords.items():
        for kw in keywords:
            if kw in lower_caption:
                service_type = svc_type
                break
        if service_type:
            break

    info["subcategory"] = service_type
    return info
