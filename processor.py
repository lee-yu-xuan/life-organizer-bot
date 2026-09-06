import json
import re
import subprocess
import logging
import urllib.parse

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
    info = _extract_info(caption, hashtags, category)
    post_text = _format_message(category, info, url, platform)

    return {"category": category, "info": info, "post_text": post_text}


def _extract_info(caption, hashtags, category):
    """Extract info using regex based on category."""
    from extractor import _regex_extract_food, _regex_extract_date, _regex_extract_wedding, _regex_extract_renovation

    if category == "food":
        return _regex_extract_food(caption, hashtags)
    elif category == "dates":
        return _regex_extract_date(caption, hashtags)
    elif category == "wedding":
        return _regex_extract_wedding(caption, hashtags)
    elif category == "renovation":
        return _regex_extract_renovation(caption, hashtags)
    return {"hashtags": hashtags}


def _format_message(category, info, url, platform):
    """Format Telegram message based on category."""
    if category == "food":
        name = info.get("restaurant_name", "Unknown Place")
        address = info.get("address", "")
        cuisine = info.get("cuisine", "")
        dishes = info.get("famous_dishes", [])
        price = info.get("price_range", "")
        hashtags = " ".join(f"#{h}" for h in info.get("hashtags", []))

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
            maps_url = f"https://maps.google.com/?q={urllib.parse.quote(address)}"
            lines.append(f"🗺️ [Open in Google Maps]({maps_url})")
        if hashtags:
            lines.append(f"\n{hashtags}")
        return "\n".join(lines)

    elif category == "wedding":
        name = info.get("vendor_name", "Wedding Vendor")
        address = info.get("address", "")
        service = info.get("service_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")
        highlights = info.get("highlights", [])

        lines = ["💒 Wedding\n"]
        lines.append(f"**{name}**\n")
        if address:
            lines.append(f"📍 {address}\n")
        if service:
            lines.append(f"💍 Service: {service.replace('_', ' ').title()}")
        if description:
            lines.append(f"📝 {description}")
        if price:
            lines.append(f"💰 Price Range: {price}")
        if highlights:
            lines.append("\n✨ Highlights:")
            for h in highlights[:3]:
                lines.append(f"- {h}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "dates":
        name = info.get("venue_name", "Date Spot")
        address = info.get("address", "")
        activity = info.get("activity_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")
        highlights = info.get("highlights", [])

        lines = ["💕 Date Ideas\n"]
        lines.append(f"**{name}**\n")
        if address:
            lines.append(f"📍 {address}\n")
        if activity:
            lines.append(f"🎭 Activity: {activity.title()}")
        if description:
            lines.append(f"📝 {description}")
        if price:
            lines.append(f"💰 Price Range: {price}")
        if highlights:
            lines.append("\n✨ Highlights:")
            for h in highlights[:3]:
                lines.append(f"- {h}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "renovation":
        name = info.get("vendor_name", "Renovation Service")
        address = info.get("address", "")
        service = info.get("service_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")
        highlights = info.get("highlights", [])

        lines = ["🏠 House Renovation\n"]
        lines.append(f"**{name}**\n")
        if address:
            lines.append(f"📍 {address}\n")
        if service:
            lines.append(f"🔧 Service: {service.replace('_', ' ').title()}")
        if description:
            lines.append(f"📝 {description}")
        if price:
            lines.append(f"💰 Price Range: {price}")
        if highlights:
            lines.append("\n✨ Highlights:")
            for h in highlights[:3]:
                lines.append(f"- {h}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    return info.get("description", "")[:200]
