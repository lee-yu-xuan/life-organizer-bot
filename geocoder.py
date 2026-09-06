from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="life-organizer-bot")


def geocode_location(location_text):
    if not location_text:
        return None, None

    try:
        location = geolocator.geocode(location_text, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Geocoding error: {e}")

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
