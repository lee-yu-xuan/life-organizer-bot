FOOD_KEYWORDS = [
    "restaurant", "cafe", "coffee", "tea", "bar", "pub", "bistro", "diner",
    "noodle", "ramen", "sushi", "pizza", "burger", "taco", "curry",
    "bakery", "dessert", "ice cream", "cake", "brunch", "food", "eat",
    "drinks", "yummy", "delicious", "must try", "hidden gem", "foodie",
    "chef", "menu", "taste", "flavor", "spicy", "sweet",
]

DATE_KEYWORDS = [
    "date", "couple", "romantic", "sunset", "scenic", "view",
    "rooftop", "lakeside", "beach", "park", "garden", "museum",
    "gallery", "cinema", "movie", "concert", "live music", "karaoke",
    "bowling", "ice skating", "hiking", "boat", "cruise", "spa",
    "date night", "couple goals",
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
    "paint", "floor", "tile", "lighting", "plumbing", "architect",
    "builder", "home improvement", "diy", "makeover", "decor",
    "minimalist", "modern", "scandinavian", "industrial",
]


def categorize(caption, hashtags=None):
    if not caption:
        return "food"

    text = caption.lower()
    if hashtags:
        text += " " + " ".join(h.lower() for h in hashtags)

    scores = {
        "food": sum(1 for kw in FOOD_KEYWORDS if kw in text),
        "dates": sum(1 for kw in DATE_KEYWORDS if kw in text),
        "wedding": sum(1 for kw in WEDDING_KEYWORDS if kw in text),
        "renovation": sum(1 for kw in RENOVATION_KEYWORDS if kw in text),
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "food"
    return best
