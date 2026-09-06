import json
import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str, timeout: int = 60) -> str:
    """Call OpenCode CLI headlessly with tiktok-processor agent."""
    try:
        result = subprocess.run(
            ["opencode", "run", "--agent", "tiktok-processor", "--model", "opencode/big-pickle", prompt],
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
        logger.error(f"OpenCode error: {e}")
        return ""


def process_link(caption: str, hashtags: list, url: str, platform: str) -> dict:
    """
    Main agent: tiktok-processor categorizes and calls subagents to format
    """
    if not caption:
        return {"category": "food", "post_text": "No caption found", "info": {}}

    hashtag_text = " ".join(f"#{h}" for h in (hashtags or []))

    # Call main agent with the TikTok link
    prompt = f"""Process this TikTok link. Categorize it and format the message.

Caption: {caption}
Hashtags: {hashtag_text}
URL: {url}
Platform: {platform}

Return the formatted Telegram message."""

    response = _call_opencode(prompt, timeout=120)

    if response:
        return {"category": "processed", "info": {}, "post_text": response}

    # Fallback to keyword categorization
    from categorizer import _keyword_categorize
    category = _keyword_categorize(caption, hashtags)

    # Extract and format locally
    from extractor import _regex_extract_food, _regex_extract_date, _regex_extract_wedding, _regex_extract_renovation

    if category == "food":
        info = _regex_extract_food(caption, hashtags)
    elif category == "dates":
        info = _regex_extract_date(caption, hashtags)
    elif category == "wedding":
        info = _regex_extract_wedding(caption, hashtags)
    elif category == "renovation":
        info = _regex_extract_renovation(caption, hashtags)
    else:
        info = {"hashtags": hashtags}

    post_text = _format_message(category, info, url, platform)
    return {"category": category, "info": info, "post_text": post_text}


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
        if hashtags:
            lines.append(f"\n{hashtags}")
        return "\n".join(lines)

    elif category == "wedding":
        name = info.get("vendor_name", "Wedding Vendor")
        address = info.get("address", "")
        service = info.get("service_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")

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
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "dates":
        name = info.get("venue_name", "Date Spot")
        address = info.get("address", "")
        activity = info.get("activity_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")

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
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "renovation":
        name = info.get("vendor_name", "Renovation Service")
        address = info.get("address", "")
        service = info.get("service_type", "")
        description = info.get("description", "")[:150]
        price = info.get("price_range", "")

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
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    return info.get("description", "")[:200]
