import re
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="life-organizer-bot")


def clean_address(location_text):
    text = re.sub(r'#[A-Z0-9-]+', '', location_text)
    text = re.sub(r',\s*,', ',', text)
    text = text.strip().strip(',').strip()
    return text


def extract_address_parts(location_text):
    parts = []

    street_match = re.search(r'(\d+[^,]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Dr|Lane|Way|Pl|Place|Ct|Court)[^,]*(?:,\s*[A-Za-z\s]+(?:\d{6})?)?)', location_text)
    if street_match:
        parts.append(street_match.group(1).strip())

    city_match = re.search(r'(?:,\s*)([A-Za-z\s]+(?:\d{6})?)\s*$', location_text)
    if city_match:
        parts.append(city_match.group(1).strip())

    country_match = re.search(r'(Singapore|Malaysia|Thailand|Japan|Korea|USA|UK|Australia)', location_text, re.IGNORECASE)
    if country_match:
        parts.append(country_match.group(1))

    return parts


def geocode_location(location_text):
    if not location_text:
        return None, None

    cleaned = clean_address(location_text)

    try:
        location = geolocator.geocode(cleaned, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Geocoding error (full): {e}")

    parts = extract_address_parts(location_text)
    for part in parts:
        try:
            location = geolocator.geocode(part, timeout=10)
            if location:
                return location.latitude, location.longitude
        except Exception as e:
            print(f"Geocoding error ({part}): {e}")

    return None, None


def format_maps_url(latitude, longitude, title=None):
    if latitude and longitude:
        url = f"https://www.google.com/maps?q={latitude},{longitude}"
        if title:
            url = f"https://www.google.com/maps/search/{title.replace(' ', '+')}/@{latitude},{longitude},15z"
        return url
    return None


def format_maps_link_text(title, location):
    if title and location:
        query = f"{title} {location}"
        return f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    elif location:
        return f"https://www.google.com/maps/search/{location.replace(' ', '+')}"
    return None
