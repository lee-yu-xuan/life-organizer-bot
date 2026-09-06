import re
import json
import subprocess
import logging

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


FOOD_KEYWORDS = [
    "restaurant", "cafe", "coffee", "tea", "bar", "pub", "bistro", "diner",
    "noodle", "ramen", "sushi", "pizza", "burger", "taco", "curry",
    "bakery", "dessert", "ice cream", "cake", "brunch", "food", "eat",
    "drinks", "yummy", "delicious", "must try", "hidden gem", "foodie",
    "chef", "menu", "taste", "flavor", "spicy", "sweet", "savory",
    "tsukemen", "udon", "soba", "tempura", "yakitori", "tonkatsu",
    "pad thai", "pho", "bun", "bibimbap", "tteokbokki", "kimbap",
    "pasta", "risotto", "lasagna", "gnocchi", "tiramisu",
    "tacos", "burrito", "quesadilla", "nachos", "guacamole",
    "steak", "bbq", "grill", "fried", "crispy", "juicy",
    "matcha", "boba", "milk tea", "bubble tea", "croissant", "waffle",
    "pancake", "omelette", "eggs benedict", "french toast",
    "dim sum", "bak kut teh", "laksa", "char kway teow", "hokkien mee",
    "nasi lemak", "roti prata", "satay", "rendang", "ayam penyet",
    "hotpot", "mala", "sichuan", "cantonese", "hainanese",
    "izakaya", "teppanyaki", "yakiniku", "omakase", "kaiseki",
]

DATE_KEYWORDS = [
    "date", "couple", "romantic", "sunset", "scenic", "view",
    "rooftop", "lakeside", "beach", "park", "garden", "museum",
    "gallery", "cinema", "movie", "concert", "live music", "karaoke",
    "bowling", "ice skating", "hiking", "boat", "cruise", "spa",
    "date night", "couple goals", "together", "romantic dinner",
    "anniversary", "valentine",
]

WEDDING_KEYWORDS = [
    "wedding", "bride", "groom", "ceremony", "reception", "venue",
    "dress", "gown", "suit", "florist", "bouquet", "decoration",
    "catering", "photographer", "videographer", "invitation",
    "honeymoon", "engagement", "ring", "vow", "banquet",
    "pre-wedding", "wedding dress", "wedding venue", "wedding cake",
]

RENOVATION_KEYWORDS = [
    "renovation", "remodel", "contractor", "interior", "design",
    "furniture", "kitchen", "bathroom", "bedroom", "living room",
    "paint", "floor", "tile", "lighting", "plumbing", "architect",
    "builder", "home improvement", "diy", "makeover", "decor",
    "minimalist", "modern", "scandinavian", "industrial",
    "ikea", "carpenter", "woodwork", "hdb", "condo", "bto",
]

FOOD_WEIGHTS = {
    "restaurant": 3, "cafe": 3, "ramen": 4, "sushi": 4, "pizza": 3,
    "burger": 3, "noodle": 3, "food": 2, "eat": 2, "menu": 2,
    "delicious": 2, "yummy": 2, "must try": 3, "foodie": 2,
    "📍": 3, "location": 2,
}


def _keyword_categorize(caption, hashtags=None):
    """Fallback keyword-based categorization."""
    if not caption:
        return "food"

    text = caption.lower()
    hashtag_text = ""
    if hashtags:
        hashtag_text = " ".join(h.lower() for h in hashtags)
        text += " " + hashtag_text

    scores = {
        "food": 0,
        "dates": 0,
        "wedding": 0,
        "renovation": 0,
    }

    for kw in FOOD_KEYWORDS:
        weight = FOOD_WEIGHTS.get(kw, 1)
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            scores["food"] += weight
        elif hashtag_text and kw in hashtag_text:
            scores["food"] += weight

    for kw in DATE_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            scores["dates"] += 2
        elif hashtag_text and kw in hashtag_text:
            scores["dates"] += 2

    for kw in WEDDING_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            scores["wedding"] += 2
        elif hashtag_text and kw in hashtag_text:
            scores["wedding"] += 2

    for kw in RENOVATION_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            scores["renovation"] += 2
        elif hashtag_text and kw in hashtag_text:
            scores["renovation"] += 2

    if "📍" in caption:
        scores["food"] += 2

    address_pattern = r'\d+\s+\w+\s+(?:rd|road|st|street|ave|avenue|blvd|dr|lane|way|pl|place)'
    if re.search(address_pattern, text):
        scores["food"] += 3

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "food"
    return best


def categorize(caption, hashtags=None):
    """Categorize caption using OpenCode LLM, with keyword fallback."""
    if not caption:
        return "food"

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    prompt = f"""Categorize this TikTok caption into ONE of these categories:
- food (restaurants, cafes, dishes, cooking, recipes)
- dates (date ideas, romantic spots, activities for couples)
- wedding (wedding services, venues, vendors, bridal)
- renovation (home renovation, interior design, furniture, contractors)

Caption: {caption}
Hashtags: {hashtag_text}

Return ONLY a JSON object: {{"category": "one of the categories above"}}"""

    response = _call_opencode(prompt)

    if response:
        data = _extract_json_from_text(response)
        if data and data.get("category") in ["food", "dates", "wedding", "renovation"]:
            logger.info(f"LLM categorized as: {data['category']}")
            return data["category"]

    logger.warning("LLM categorization failed, using keyword fallback")
    return _keyword_categorize(caption, hashtags)
