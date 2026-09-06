import re
import tempfile
import os

INSTAGRAM_PATTERN = re.compile(r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|reels)/[A-Za-z0-9_-]+')
TIKTOK_PATTERN = re.compile(r'(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/.+')
YOUTUBE_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com/shorts|youtu\.be)/[A-Za-z0-9_-]+')


def detect_platform(url):
    if INSTAGRAM_PATTERN.search(url):
        return "instagram"
    elif TIKTOK_PATTERN.search(url):
        return "tiktok"
    elif YOUTUBE_PATTERN.search(url):
        return "youtube"
    return None


def extract_instagram(url):
    try:
        import instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
        shortcode = url.split("/p/")[-1].split("/")[0] if "/p/" in url else None
        if not shortcode and "/reel/" in url:
            shortcode = url.split("/reel/")[-1].split("/")[0]
        if not shortcode and "/reels/" in url:
            shortcode = url.split("/reels/")[-1].split("/")[0]

        if not shortcode:
            return None

        post = instaloader.Post.from_shortcode(L.context, shortcode)
        caption = post.caption or ""
        hashtags = list(post.caption_hashtags) if post.caption_hashtags else []
        location_name = post.location.name if post.location else None
        location_lat = post.location.lat if post.location else None
        location_lon = post.location.lng if post.location else None

        return {
            "caption": caption,
            "hashtags": hashtags,
            "location_name": location_name,
            "location_lat": location_lat,
            "location_lon": location_lon,
            "username": post.owner_username,
            "is_video": post.is_video,
        }
    except Exception as e:
        print(f"Instagram scrape error: {e}")
        return None


def extract_tiktok(url):
    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        description = info.get('description', '') or ''
        hashtags = re.findall(r'#(\w+)', description)
        title = info.get('title', '') or info.get('fulltitle', '')

        return {
            "caption": description,
            "hashtags": hashtags,
            "title": title,
            "uploader": info.get('uploader', ''),
            "location_name": None,
            "location_lat": None,
            "location_lon": None,
            "is_video": True,
        }
    except Exception as e:
        print(f"TikTok scrape error: {e}")
        return None


def scrape_url(url):
    platform = detect_platform(url)
    if not platform:
        return None

    if platform == "instagram":
        data = extract_instagram(url)
    elif platform == "tiktok":
        data = extract_tiktok(url)
    else:
        return None

    if data:
        data["platform"] = platform
        data["url"] = url
    return data
