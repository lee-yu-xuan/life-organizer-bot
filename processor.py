import json
import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str, timeout: int = 300) -> str:
    """Call OpenCode CLI with tiktok-processor agent."""
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
    Main agent: tiktok-processor fetches content, categorizes, calls subagents
    """
    if not url:
        return {"category": "food", "post_text": "No URL provided", "info": {}}

    # Call main agent with the TikTok URL
    prompt = f"""Process this TikTok link.

URL: {url}

Fetch the content using oEmbed, categorize it, and call the appropriate subagent to format the message."""

    response = _call_opencode(prompt, timeout=300)

    if response and len(response) > 50:
        # Extract category from response
        category = "food"
        if "💒 Wedding" in response or "wedding" in response.lower():
            category = "wedding"
        elif "💕 Date" in response or "dates" in response.lower():
            category = "dates"
        elif "🏠 Renovation" in response or "renovation" in response.lower():
            category = "renovation"
        elif "🍔 Food" in response or "food" in response.lower():
            category = "food"

        return {"category": category, "info": {}, "post_text": response}

    # Fallback: keyword categorization
    from categorizer import _keyword_categorize
    category = _keyword_categorize(caption or "", hashtags or [])

    from extractor import _regex_extract_food, _regex_extract_date, _regex_extract_wedding, _regex_extract_renovation

    if category == "food":
        info = _regex_extract_food(caption or "", hashtags or [])
    elif category == "dates":
        info = _regex_extract_date(caption or "", hashtags or [])
    elif category == "wedding":
        info = _regex_extract_wedding(caption or "", hashtags or [])
    elif category == "renovation":
        info = _regex_extract_renovation(caption or "", hashtags or [])
    else:
        info = {"hashtags": hashtags or []}

    post_text = _format_message(category, info, url, platform)
    return {"category": category, "info": info, "post_text": post_text}


def _format_message(category, info, url, platform):
    """Format Telegram message based on category (fallback)."""
    if category == "food":
        name = info.get("restaurant_name", "Unknown Place")
        address = info.get("address", "Singapore")
        cuisine = info.get("cuisine", "")
        dishes = info.get("famous_dishes", [])

        lines = ["🍔 Food Places\n"]
        lines.append(f"**{name}**\n")
        lines.append(f"📍 {address}\n")
        if cuisine:
            lines.append(f"🍽️ Cuisine: {cuisine}")
        if dishes:
            lines.append(f"🍜 Famous Dishes: {', '.join(dishes)}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "wedding":
        name = info.get("vendor_name", "Wedding Vendor")
        service = info.get("service_type", "")

        lines = ["💒 Wedding\n"]
        lines.append(f"**{name}**\n")
        lines.append(f"📍 Singapore\n")
        if service:
            lines.append(f"💍 Service: {service.replace('_', ' ').title()}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "dates":
        name = info.get("venue_name", "Date Spot")
        activity = info.get("activity_type", "")

        lines = ["💕 Date Ideas\n"]
        lines.append(f"**{name}**\n")
        lines.append(f"📍 Singapore\n")
        if activity:
            lines.append(f"🎭 Activity: {activity.title()}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    elif category == "renovation":
        name = info.get("vendor_name", "Renovation Service")
        service = info.get("service_type", "")

        lines = ["🏠 House Renovation\n"]
        lines.append(f"**{name}**\n")
        lines.append(f"📍 Singapore\n")
        if service:
            lines.append(f"🔧 Service: {service.replace('_', ' ').title()}")
        lines.append(f"\n🔗 [View on {platform.title()}]({url})")
        return "\n".join(lines)

    return info.get("description", "")[:200]
