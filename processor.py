import json
import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str, timeout: int = 90) -> str:
    """Call OpenCode CLI headlessly."""
    try:
        result = subprocess.run(
            ["opencode", "run", prompt],
            capture_output=True,
            text=True,
            timeout=timeout
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


def process_link(caption: str, hashtags: list, url: str, platform: str) -> dict:
    """
    Single OpenCode call to:
    1. Categorize the caption
    2. Extract info based on category
    3. Format the Telegram message
    """
    if not caption:
        return {
            "category": "food",
            "post_text": "No caption found",
            "info": {}
        }

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    prompt = f"""You are a social media content processor. Process this TikTok link and return a JSON object.

Caption: {caption}
Hashtags: {hashtag_text}
URL: {url}
Platform: {platform}

STEP 1: Categorize into ONE of these:
- food (restaurants, cafes, dishes, cooking)
- dates (date ideas, romantic spots, couples activities)
- wedding (wedding services, venues, vendors, bridal)
- renovation (home renovation, interior design, furniture)

STEP 2: Extract info based on category:

For food: extract restaurant_name, cuisine, famous_dishes, price_range, address
For dates: extract venue_name, activity_type, description, price_range, address, highlights
For wedding: extract vendor_name, service_type, description, price_range, address, highlights
For renovation: extract vendor_name, service_type, description, price_range, address, highlights

STEP 3: Format a Telegram message based on category.

Food format:
🍔 Food Places

**restaurant_name**

📍 address

🍽️ Cuisine: cuisine
🍜 Famous Dishes: dishes

💰 Price Range: price

🔗 [View on TikTok](url)

🗺️ [Open in Google Maps](maps_url)

#tags

Date format:
💕 Date Ideas

**venue_name**

📍 address

🎭 Activity: type
📝 description

💰 Price Range: price

✨ Highlights:
- highlight

🔗 [View on TikTok](url)

🗺️ [Open in Google Maps](maps_url)

Wedding format:
💒 Wedding

**vendor_name**

📍 address

💍 Service: type
📝 description

💰 Price Range: price

✨ Highlights:
- highlight

🔗 [View on TikTok](url)

🗺️ [Open in Google Maps](maps_url)

Renovation format:
🏠 House Renovation

**vendor_name**

📍 address

🔧 Service: type
📝 description

💰 Price Range: price

✨ Highlights:
- highlight

🔗 [View on TikTok](url)

Return ONLY a JSON object with these fields:
{{"category": "food/dates/wedding/renovation", "info": {{extracted fields}}, "post_text": "formatted telegram message"}}"""

    response = _call_opencode(prompt, timeout=90)

    if response:
        data = _extract_json_from_text(response)
        if data and data.get("category") and data.get("post_text"):
            logger.info(f"Processed as: {data['category']}")
            return data

    logger.warning("LLM processing failed, using fallback")
    return _fallback_process(caption, hashtags, url, platform)


def _fallback_process(caption, hashtags, url, platform):
    """Fallback processing using keyword matching."""
    from categorizer import _keyword_categorize
    from extractor import (
        extract_food_info, extract_date_info, extract_wedding_info, extract_renovation_info,
        format_food_message, format_date_message, format_wedding_message, format_renovation_message
    )

    category = _keyword_categorize(caption, hashtags)

    if category == "food":
        info = extract_food_info(caption, hashtags)
        post_text = format_food_message(info, url, platform)
    elif category == "dates":
        info = extract_date_info(caption, hashtags)
        post_text = format_date_message(info, url, platform)
    elif category == "wedding":
        info = extract_wedding_info(caption, hashtags)
        post_text = format_wedding_message(info, url, platform)
    elif category == "renovation":
        info = extract_renovation_info(caption, hashtags)
        post_text = format_renovation_message(info, url, platform)
    else:
        info = {}
        post_text = caption[:200] if caption else "No content"

    return {
        "category": category,
        "info": info,
        "post_text": post_text
    }
