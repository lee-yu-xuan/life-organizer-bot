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


def resolve_tiktok_url(url):
    import requests
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, allow_redirects=True, timeout=10)
        return resp.url
    except Exception:
        return url


def extract_tiktok(url):
    import requests
    try:
        resolved_url = resolve_tiktok_url(url)

        oembed_url = f"https://www.tiktok.com/oembed?url={resolved_url}"
        resp = requests.get(oembed_url, timeout=10)

        if resp.status_code != 200:
            print(f"TikTok oEmbed failed: {resp.status_code}")
            return None

        data = resp.json()
        title = data.get("title", "")
        author_name = data.get("author_name", "")
        author_url = data.get("author_url", "")

        caption = title
        hashtags = re.findall(r'#(\w+)', caption)

        return {
            "caption": caption,
            "hashtags": hashtags,
            "title": author_name,
            "uploader": author_name,
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
