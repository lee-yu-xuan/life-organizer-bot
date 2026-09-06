import logging
import json
import re
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, CHANNEL_ID, TOPICS
from database import init_db, save_place, search_places, get_places_by_category, get_all_places
from scraper import scrape_url, detect_platform, INSTAGRAM_PATTERN, TIKTOK_PATTERN, YOUTUBE_PATTERN
from extractor import extract_food_info, extract_date_info, extract_wedding_info, extract_renovation_info, format_food_message
from categorizer import categorize
from geocoder import geocode_location, format_maps_url, format_maps_link_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORY_NAMES = {
    "food": "Food Places",
    "dates": "Date Ideas",
    "wedding": "Wedding",
    "renovation": "House Renovation",
}

CATEGORY_EMOJIS = {
    "food": "🍔",
    "dates": "💕",
    "wedding": "💒",
    "renovation": "🏠",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Life Organizer Bot!\n\n"
        "Send me an Instagram Reel or TikTok link and I'll:\n"
        "1. Extract the place info\n"
        "2. Auto-categorize it\n"
        "3. Pin the location on a map\n"
        "4. Post it to your channel\n\n"
        "Commands:\n"
        "/search <keyword> - Search saved places\n"
        "/food - List food places\n"
        "/dates - List date ideas\n"
        "/wedding - List wedding items\n"
        "/renovation - List renovation items\n"
        "/list - List all saved places"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    urls = re.findall(
        r'https?://(?:www\.)?(?:instagram\.com|instagr\.am|tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|youtube\.com/shorts|youtu\.be)/\S+',
        text
    )

    if not urls:
        return

    url = urls[0]
    platform = detect_platform(url)

    if not platform:
        await update.message.reply_text("❌ Unsupported link. Please send a TikTok link.")
        return

    if platform == "instagram":
        await update.message.reply_text("❌ Instagram is not supported yet. Please send a TikTok link.")
        return

    status_msg = await update.message.reply_text(f"⏳ Processing {platform.title()} link...")

    try:
        data = scrape_url(url)
        if not data:
            await status_msg.edit_text("❌ Failed to scrape the link. It might be private or unavailable.")
            return

        caption = data.get("caption", "")
        hashtags = data.get("hashtags", [])

        category = categorize(caption, hashtags)

        if category == "food":
            info = extract_food_info(caption, hashtags)
            post_text = format_food_message(info, url, platform)
            if not info.get("restaurant_name") and not info.get("address"):
                logger.warning("Food extraction returned no data, using caption as title")
                title = title or caption[:100] if caption else ""
        elif category == "dates":
            info = extract_date_info(caption, hashtags)
        elif category == "wedding":
            info = extract_wedding_info(caption, hashtags)
        elif category == "renovation":
            info = extract_renovation_info(caption, hashtags)
        else:
            info = {"locations": [], "price": None, "tags": [], "subcategory": None}

        title = data.get("title") or data.get("username") or ""
        location_name = data.get("location_name") or (info.get("locations", [None])[0] if info.get("locations") else None)
        latitude = data.get("location_lat")
        longitude = data.get("location_lon")

        if not latitude and location_name:
            latitude, longitude = geocode_location(location_name)

        tags = info.get("tags", [])
        if hashtags:
            tags = list(set(tags + [h.lower() for h in hashtags]))

        save_place(
            category=category,
            platform=platform,
            url=url,
            title=title,
            location=location_name,
            latitude=latitude,
            longitude=longitude,
            subcategory=info.get("subcategory"),
            price_range=info.get("price"),
            tags=json.dumps(tags) if tags else None,
            description=caption[:500] if caption else None,
            hashtags=json.dumps(hashtags) if hashtags else None,
        )

        topic_id = TOPICS.get(category)
        emoji = CATEGORY_EMOJIS.get(category, "📌")
        cat_name = CATEGORY_NAMES.get(category, "Unknown")

        if category != "food":
            post_text = f"{emoji} *{cat_name}*\n\n"

            if title:
                post_text += f"*{title}*\n"

            if location_name:
                post_text += f"📍 {location_name}\n"

            if info.get("subcategory"):
                post_text += f"🏷️ {info['subcategory'].title()}\n"

            if info.get("price"):
                post_text += f"💰 {info['price']}\n"

            post_text += f"\n🔗 [View on {platform.title()}]({url})\n"

            if latitude and longitude:
                maps_url = format_maps_url(latitude, longitude, title)
                post_text += f"🗺️ [Open in Google Maps]({maps_url})\n"

            if caption:
                short_caption = caption[:300] + ("..." if len(caption) > 300 else "")
                post_text += f"\n📝 {short_caption}\n"

            if tags:
                tag_str = " ".join(f"#{t}" for t in tags[:10])
                post_text += f"\n{tag_str}"
            elif hashtags:
                tag_str = " ".join(f"#{h.lower()}" for h in hashtags[:10])
                post_text += f"\n{tag_str}"

        bot = context.bot
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=post_text,
            message_thread_id=topic_id,
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )

        if latitude and longitude:
            await bot.send_location(
                chat_id=CHANNEL_ID,
                latitude=latitude,
                longitude=longitude,
                message_thread_id=topic_id,
            )

        await status_msg.edit_text(
            f"✅ Posted to *{cat_name}* topic!\n\n"
            f"Title: {title}\n"
            f"Location: {location_name or 'Not found'}\n"
            f"Category: {cat_name}",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await status_msg.edit_text(f"❌ Error processing link: {str(e)[:200]}")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>")
        return

    keyword = " ".join(context.args)
    places = search_places(keyword)

    if not places:
        await update.message.reply_text(f"No results found for '{keyword}'")
        return

    text = f"🔍 Search results for '{keyword}':\n\n"
    for place in places[:10]:
        emoji = CATEGORY_EMOJIS.get(place["category"], "📌")
        text += f"{emoji} *{place['title'] or 'Unknown'}*\n"
        if place["location"]:
            text += f"📍 {place['location']}\n"
        text += f"🔗 [View]({place['url']})\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def list_places(update: Update, context: ContextTypes.DEFAULT_TYPE):
    places = get_all_places()

    if not places:
        await update.message.reply_text("No places saved yet.")
        return

    text = f"📋 All saved places ({len(places)} total):\n\n"
    for place in places[:10]:
        emoji = CATEGORY_EMOJIS.get(place["category"], "📌")
        text += f"{emoji} *{place['title'] or 'Unknown'}*\n"
        if place["location"]:
            text += f"📍 {place['location']}\n"
        text += f"🔗 [View]({place['url']})\n\n"

    if len(places) > 10:
        text += f"... and {len(places) - 10} more"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def list_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category):
    places = get_places_by_category(category)

    if not places:
        await update.message.reply_text(f"No {CATEGORY_NAMES.get(category, category)} saved yet.")
        return

    emoji = CATEGORY_EMOJIS.get(category, "📌")
    text = f"{emoji} {CATEGORY_NAMES.get(category, category)} ({len(places)} total):\n\n"
    for place in places[:10]:
        text += f"*{place['title'] or 'Unknown'}*\n"
        if place["location"]:
            text += f"📍 {place['location']}\n"
        text += f"🔗 [View]({place['url']})\n\n"

    if len(places) > 10:
        text += f"... and {len(places) - 10} more"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_by_category(update, context, "food")


async def dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_by_category(update, context, "dates")


async def wedding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_by_category(update, context, "wedding")


async def renovation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_by_category(update, context, "renovation")


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("list", list_places))
    app.add_handler(CommandHandler("food", food))
    app.add_handler(CommandHandler("dates", dates))
    app.add_handler(CommandHandler("wedding", wedding))
    app.add_handler(CommandHandler("renovation", renovation))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
