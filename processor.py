import json
import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str, timeout: int = 30) -> str:
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
            return ""
    except Exception as e:
        logger.error(f"OpenCode error: {e}")
        return ""


def _extract_json_from_text(text: str) -> dict:
    """Try to extract JSON from text."""
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def process_link(caption: str, hashtags: list, url: str, platform: str) -> dict:
    """
    Main agent: categorize using LLM
    Subagents: format using Python (regex + templates)
    """
    if not caption:
        return {"category": "food", "post_text": "No caption found", "info": {}}

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    # Main agent: categorize
    prompt = f"""Categorize this TikTok caption. Return ONLY JSON: {{"category": "food/dates/wedding/renovation"}}

Caption: {caption}
Hashtags: {hashtag_text}"""

    response = _call_opencode(prompt, timeout=30)
    category = None

    if response:
        data = _extract_json_from_text(response)
        if data and data.get("category") in ["food", "dates", "wedding", "renovation"]:
            category = data["category"]
            logger.info(f"LLM categorized: {category}")

    if not category:
        from categorizer import _keyword_categorize
        category = _keyword_categorize(caption, hashtags)

    # Subagent: format based on category
    info = _extract_info(caption, hashtags)
    post_text = _format_message(category, info, url, platform)

    return {"category": category, "info": info, "post_text": post_text}


def _extract_info(caption, hashtags):
    """Extract info using regex."""
    info = {"hashtags": hashtags}

    # Address
    addr = re.search(r'(\d+[\w\s,]+(?:Singapore|SG|KL|Kuala Lumpur|Malaysia))', caption, re.IGNORECASE)
    if addr:
        info["address"] = addr.group(1).strip()

    # Price
    price = re.search(r'(\${1,4})', caption)
    if price:
        info["price"] = price.group(1)

    # Name
    name = re.search(r'([A-Z][\w\s]+?)(?:\s+at\s+|\s*,)', caption)
    if name:
        info["name"] = name.group(1).strip()

    # Cuisine (food only)
    cuisines = ['Japanese', 'Chinese', 'Korean', 'Thai', 'Vietnamese', 'Italian', 'French', 'Indian', 'Mexican']
    for c in cuisines:
        if c.lower() in caption.lower():
            info["cuisine"] = c
            break

    # Dishes (food only)
    dishes = []
    for d in ['ramen', 'sushi', 'tempura', 'udon', 'pizza', 'pasta', 'steak', 'burger']:
        if d in caption.lower():
            dishes.append(d.title())
    info["dishes"] = dishes

    # Description
    info["description"] = caption[:200]

    # Highlights
    info["highlights"] = [w for w in caption.split() if len(w) > 3 and w.isalpha()][:5]

    return info


def _format_message(category, info, url, platform):
    """Format Telegram message based on category."""
    name = info.get("name", "Unknown")
    address = info.get("address", "Not provided")
    price = info.get("price", "N/A")

    if category == "food":
        cuisine = info.get("cuisine", "")
        dishes = info.get("dishes", [])
        hashtags = " ".join(f"#{h}" for h in info.get("hashtags", []))

        lines = ["🍔 Food Places\n"]
        lines.append(f"**{name}**\n")
        if address != "Not provided":
            lines.append(f"📍 {address}\n")
        if cuisine:
            lines.append(f"🍽️ Cuisine: {cuisine}")
        if dishes:
            lines.append(f"🍜 Famous Dishes: {', '.join(dishes)}")
        if price != "N/A":
            lines.append(f"💰 Price Range: {price}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        if address != "Not provided":
            import urllib.parse
            maps_url = f"https://maps.google.com/?q={urllib.parse.quote(address)}"
            lines.append(f"🗺️ [Open in Google Maps]({maps_url})")
        if hashtags:
            lines.append(f"\n{hashtags}")
        return "\n".join(lines)

    elif category == "wedding":
        lines = ["💒 Wedding\n"]
        lines.append(f"**{name}**\n")
        if address != "Not provided":
            lines.append(f"📍 {address}\n")
        lines.append(f"📝 {info.get('description', '')[:150]}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "dates":
        lines = ["💕 Date Ideas\n"]
        lines.append(f"**{name}**\n")
        if address != "Not provided":
            lines.append(f"📍 {address}\n")
        lines.append(f"📝 {info.get('description', '')[:150]}")
        if price != "N/A":
            lines.append(f"💰 Price Range: {price}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "renovation":
        lines = ["🏠 House Renovation\n"]
        lines.append(f"**{name}**\n")
        if address != "Not provided":
            lines.append(f"📍 {address}\n")
        lines.append(f"📝 {info.get('description', '')[:150]}")
        if price != "N/A":
            lines.append(f"💰 Price Range: {price}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    return caption[:200]
