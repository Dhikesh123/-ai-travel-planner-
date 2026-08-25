"""
Where things are, and what a journey passes.

The site used to know a destination's name and nothing about where it sat.
That was enough to price a trip - the distance table did that - but not to
answer the question a traveller actually asks: I am going from Bhimavaram to
Ayodhya, what can I see on the way?

This file answers it in three steps:

1. locate()          - turn a city name into coordinates, asking
                       OpenStreetMap once and remembering the answer.
2. distance_km()     - straight-line distance between two points.
3. journey_groups()  - sort every destination into "near your start",
                       "along the way" and "in and around where you are
                       going", given the two ends of the journey.

Straight-line distance, not road distance. A road is always longer than the
line, and by a fairly steady ratio in the plains, so a detour budget applied
to straight lines picks out the same towns a road would - and it needs no
routing service, no API key, and no network call once a city is known.
"""
import json
import math
import urllib.parse
import urllib.request

from django.utils.text import slugify

# OpenStreetMap's free geocoder. Their usage policy asks for an identifying
# User-Agent and no more than one request a second; this file makes one
# request per city ever, and only for a city nobody has typed before.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    "AITravelPlanner/1.0 (student project; yerradhikesh@gmail.com) Python-urllib"
)
GEOCODE_TIMEOUT = 8          # a traveller is waiting; do not hang the page

EARTH_RADIUS_KM = 6371.0

# How far from either end still counts as "around here". Two hours on an
# Indian highway is roughly this, and it is the distance at which a place
# stops being a side trip and becomes a journey of its own.
NEAR_KM = 150

# How much longer than the direct line a stop may make the trip before it
# stops being "on the way". At 1.25, going 1,600 km from Bhimavaram to
# Ayodhya buys a 400 km detour budget spread across the whole route, which
# is generous enough to catch a town an hour off the highway and mean
# enough to exclude one in a different part of the country.
DETOUR_FACTOR = 1.25
DETOUR_SLACK_KM = 60         # keeps short journeys from having no room at all

# The two fixed group headings. Named rather than written inline because
# callers match on them to tell one group from another - views.py labels a
# suggestion "On the way" or "Near your start" off these - and a heading
# quietly reworded in one place and not the other would silently mislabel
# every card.
NEAR_START_HEADING = "Near your starting point"
ON_ROUTE_HEADING = "On the way"


def distance_km(first, second):
    """
    Straight-line distance in kilometres between two (latitude, longitude)
    pairs, by the haversine formula.
    """
    if not first or not second:
        return None
    lat1, lon1 = float(first[0]), float(first[1])
    lat2, lon2 = float(second[0]), float(second[1])

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _ask_openstreetmap(name):
    """One geocoding request. Returns (lat, lon, display_name) or None."""
    query = urllib.parse.urlencode(
        {
            "q": name,
            "format": "json",
            "limit": 1,
            # Every destination on this site is in India, and restricting the
            # search stops "Hyderabad" landing in Pakistan.
            "countrycodes": "in",
        }
    )
    request = urllib.request.Request(
        NOMINATIM_URL + "?" + query, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=GEOCODE_TIMEOUT) as response:
        results = json.load(response)
    if not results:
        return None
    top = results[0]
    return float(top["lat"]), float(top["lon"]), _tidy_name(top.get("display_name", ""))


def _tidy_name(display_name):
    """
    Shorten OpenStreetMap's answer to something a dropdown can show.

    They return the whole administrative chain - "Bhimavaram, West Godavari,
    Andhra Pradesh, India" - and all a traveller needs is the town and the
    state, which are the first part and the one before the country.
    """
    parts = [part.strip() for part in (display_name or "").split(",") if part.strip()]
    if not parts:
        return ""
    if parts[-1].lower() in ("india", "bharat") and len(parts) > 1:
        parts = parts[:-1]
    # a postcode is not a place name
    parts = [part for part in parts if not part.replace(" ", "").isdigit()]
    if len(parts) <= 2:
        return ", ".join(parts)[:250]
    return "%s, %s" % (parts[0], parts[-1])


def locate(name):
    """
    Coordinates for a city name, as a (latitude, longitude) pair, or None.

    Looked for in this order:

    1. The destinations table - a destination is a city, and its coordinates
       are already seeded.
    2. The CityLocation cache - somebody has typed this town before.
    3. OpenStreetMap - asked once, then written into the cache. A failure is
       cached too, so a misspelling is not looked up again and again.

    Never raises. A city that cannot be placed returns None, and the caller
    falls back to showing the destination's own places.
    """
    from ..models import CityLocation, Destination     # avoids a circular import

    key = (name or "").strip().lower()
    if not key:
        return None

    # 1. one of our own destinations
    destination = (
        Destination.objects.filter(name__iexact=key)
        .exclude(latitude__isnull=True)
        .first()
    )
    if destination:
        return (destination.latitude, destination.longitude)

    # 2. remembered from an earlier traveller
    cached = CityLocation.objects.filter(name=key).first()
    if cached:
        return (cached.latitude, cached.longitude) if cached.found else None

    # 3. ask, once
    try:
        found = _ask_openstreetmap(name.strip() + ", India")
    except Exception:
        # No internet, a timeout, a rate limit: not knowing is a normal
        # outcome here, and the planner still works without it.
        return None

    if found:
        latitude, longitude, display = found
        CityLocation.objects.update_or_create(
            name=key,
            defaults={
                "latitude": latitude,
                "longitude": longitude,
                "display_name": display,
            },
        )
        return (latitude, longitude)

    # remember the failure so the next keystroke does not ask again
    CityLocation.objects.update_or_create(
        name=key, defaults={"latitude": None, "longitude": None, "display_name": ""}
    )
    return None


def is_on_the_way(start, stop, end, direct=None):
    """
    Would stopping here be a detour worth calling "on the way"?

    Going start -> stop -> end always costs at least as much as going
    start -> end. How much more is the detour, and a stop is on the way when
    that extra is inside the budget.
    """
    direct = direct if direct is not None else distance_km(start, end)
    if direct is None:
        return False
    through = distance_km(start, stop)
    onward = distance_km(stop, end)
    if through is None or onward is None:
        return False
    return (through + onward) <= (direct * DETOUR_FACTOR) + DETOUR_SLACK_KM


def journey_groups(source_name, destination):
    """
    Sort the destinations into the three groups a traveller thinks in.

    Returns a list of (heading, note, [destination, ...]) with the empty
    groups left out, and every destination in exactly one group. The chosen
    destination always leads the last group, because that is what the trip
    is for.

    When the starting city cannot be placed - no internet, or a town
    OpenStreetMap does not know - the route half is simply skipped and the
    traveller still gets where they are going and its neighbours. Degrading
    is better than an empty page.
    """
    from ..models import Destination

    if destination is None:
        return []

    end = (
        (destination.latitude, destination.longitude)
        if destination.latitude is not None
        else None
    )
    start = locate(source_name)
    direct = distance_km(start, end)

    others = (
        Destination.objects.exclude(pk=destination.pk)
        .exclude(latitude__isnull=True)
        .prefetch_related("places")
    )

    near_start, on_route, near_end = [], [], []
    for other in others:
        here = (other.latitude, other.longitude)

        # Nearest the far end wins: somewhere an hour from Ayodhya belongs
        # under Ayodhya, not in a list of things passed on the motorway.
        to_end = distance_km(here, end)
        if to_end is not None and to_end <= NEAR_KM:
            near_end.append((to_end, other))
            continue

        if start is not None:
            from_start = distance_km(here, start)
            if from_start is not None and from_start <= NEAR_KM:
                near_start.append((from_start, other))
                continue
            if direct is not None and is_on_the_way(start, here, end, direct):
                # ordered by how far along the journey they fall, so the list
                # reads in the order they would actually be reached
                on_route.append((from_start, other))
                continue

    def ordered(rows):
        return [row[1] for row in sorted(rows, key=lambda row: row[0])]

    groups = []
    if near_start:
        groups.append((
            NEAR_START_HEADING,
            "Within %d km of %s." % (NEAR_KM, source_name.strip().title()),
            ordered(near_start),
        ))
    if on_route:
        groups.append((
            ON_ROUTE_HEADING,
            "Roughly along the road, in the order you would reach them.",
            ordered(on_route),
        ))

    # The destination itself always leads its own group.
    groups.append((
        "In and around %s" % destination.name,
        "Where you are going, and what is close to it.",
        [destination] + ordered(near_end),
    ))
    return groups


def slug_for(destination):
    """A stable id for a group heading, for the template's checkbox groups."""
    return slugify(destination.name)
