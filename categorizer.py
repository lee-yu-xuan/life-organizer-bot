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
    "anniversary", "valentine", "情侣", "约会",
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


def categorize(caption, hashtags=None):
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


import re
