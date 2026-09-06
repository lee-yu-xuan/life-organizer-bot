import json
import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _call_opencode(prompt: str, timeout: int = 60) -> str:
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
    Process a TikTok link:
    1. Categorize using LLM
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

    # Try LLM categorization first
    prompt = f"""Categorize this TikTok caption into ONE category: food, dates, wedding, or renovation.

Caption: {caption}
Hashtags: {hashtag_text}

Return ONLY: {{"category": "..."}}"""

    response = _call_opencode(prompt, timeout=30)
    category = None

    if response:
        data = _extract_json_from_text(response)
        if data and data.get("category") in ["food", "dates", "wedding", "renovation"]:
            category = data["category"]
            logger.info(f"LLM categorized as: {category}")

    # Fallback to keyword categorization
    if not category:
        from categorizer import _keyword_categorize
        category = _keyword_categorize(caption, hashtags)
        logger.info(f"Keyword categorized as: {category}")

    # Extract and format based on category
    from extractor import (
        extract_food_info, extract_date_info, extract_wedding_info, extract_renovation_info,
        format_food_message, format_date_message, format_wedding_message, format_renovation_message
    )

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
