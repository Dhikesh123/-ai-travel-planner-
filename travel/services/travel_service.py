"""
The "brain" of the planner that does NOT need the internet:

  * estimate_distance()  - how far apart two cities are
  * calculate_costs()    - the trip cost calculator
  * build_itinerary()    - the day-by-day plan

IMPORTANT: every number produced here is a DEMONSTRATION ESTIMATE built from
sample rates stored in the database. They are not live market prices.
"""
from decimal import ROUND_HALF_UP, Decimal
from math import ceil

from . import geo_service

# ---------------------------------------------------------------------------
# Sample rate cards. Admin can override transport rates in the database;
# these two tables stay in code because they are simple lookup values.
# ---------------------------------------------------------------------------

# Rupees per room per night (a room holds 2 people)
HOTEL_RATES = {
    "budget": Decimal("1200"),
    "standard": Decimal("2200"),
    "deluxe": Decimal("4000"),
    "luxury": Decimal("7500"),
}

# Rupees per person per day for food
FOOD_RATES = {
    "budget": Decimal("350"),
    "standard": Decimal("650"),
    "premium": Decimal("1300"),
}

# Rupees per day for taxis/autos inside the destination city (per group of 4)
LOCAL_TRANSPORT_PER_DAY = Decimal("500")

# Extra buffer for shopping, tips, emergencies: 8% of everything else
OTHER_EXPENSES_PERCENT = Decimal("0.08")

# How much longer a road is than the straight line it follows. Used when a
# distance has to be measured from coordinates rather than read from a table.
# A plain float, because the distance it multiplies is one: haversine works
# in floats and the result is rounded to whole kilometres anyway.
ROAD_WINDS_FACTOR = 1.25

# Fallback distance used when the city pair is unknown and neither end can be
# placed on the map
DEFAULT_DISTANCE_KM = 250

# A few well-known sample distances. The RouteDistance table is checked first,
# so an admin can add more without touching this file.
FALLBACK_DISTANCES = {
    ("pune", "mumbai"): 150,
    ("hyderabad", "bengaluru"): 570,
    ("hyderabad", "chennai"): 630,
    ("hyderabad", "goa"): 660,
    ("hyderabad", "tirupati"): 550,
    ("hyderabad", "vizag"): 620,
    ("hyderabad", "visakhapatnam"): 620,
    ("hyderabad", "araku"): 690,
    ("vijayawada", "hyderabad"): 275,
    ("vijayawada", "visakhapatnam"): 350,
    ("bengaluru", "chennai"): 350,
    ("bengaluru", "goa"): 560,
    ("bengaluru", "mysuru"): 145,
    ("chennai", "pondicherry"): 160,
    ("mumbai", "goa"): 590,
    ("delhi", "jaipur"): 280,
    ("delhi", "agra"): 230,
    ("delhi", "manali"): 540,
    ("kolkata", "darjeeling"): 620,
}


def _money(value):
    """Round any number to 2 decimal places, the way money should look."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Distance and travel time
# ---------------------------------------------------------------------------
def estimate_distance(source, destination_name):
    """
    Return (distance_km, is_known).

    is_known is False when we had to guess, so the page can say
    "rough estimate" instead of pretending it is accurate.
    """
    from ..models import RouteDistance  # imported here to avoid a circular import

    src = (source or "").strip().lower()
    dst = (destination_name or "").strip().lower()

    if not src or not dst:
        return DEFAULT_DISTANCE_KM, False

    if src == dst:
        return 0, True

    # 1. Look in the database (admin-managed), in both directions
    row = RouteDistance.objects.filter(
        from_city__iexact=src, to_city__iexact=dst
    ).first() or RouteDistance.objects.filter(
        from_city__iexact=dst, to_city__iexact=src
    ).first()
    if row:
        return row.distance_km, True

    # 2. Look in the built-in sample table, in both directions
    if (src, dst) in FALLBACK_DISTANCES:
        return FALLBACK_DISTANCES[(src, dst)], True
    if (dst, src) in FALLBACK_DISTANCES:
        return FALLBACK_DISTANCES[(dst, src)], True

    # 3. Neither table knows this pair - but both ends may still be on the
    #    map. Bhimavaram to Ayodhya is nobody's sample route, and answering
    #    "250 km" for a journey of about fourteen hundred put every figure on
    #    the page out by a factor of five.
    kilometres = geo_service.distance_km(
        geo_service.locate(src), geo_service.locate(dst)
    )
    if kilometres:
        # A road is longer than the line it follows - hills, rivers, and the
        # simple fact that towns are not laid out for the convenience of
        # straight lines. A quarter again is the usual allowance in the plains.
        return int(kilometres * ROAD_WINDS_FACTOR), True

    # 4. Give up and use a neutral default
    return DEFAULT_DISTANCE_KM, False


def estimate_travel_hours(distance_km, transportation):
    """Simple time estimate: distance / speed, plus a small break allowance."""
    speed = transportation.average_speed_kmph or 50
    hours = Decimal(distance_km) / Decimal(speed)
    breaks = Decimal("0.5") if distance_km > 200 else Decimal("0")
    return _money(hours + breaks)


# ---------------------------------------------------------------------------
# Cost calculator
# ---------------------------------------------------------------------------
def calculate_costs(
    *,
    distance_km,
    travelers,
    days,
    transportation,
    hotel_category="standard",
    food_budget="standard",
    activity_budget=Decimal("0"),
    places=None,
):
    """
    Work out every part of the trip budget and return a dictionary.

    places = a list/queryset of TouristPlace objects the customer selected.
    """
    travelers = max(int(travelers or 1), 1)
    days = max(int(days or 1), 1)
    nights = max(days - 1, 0)
    distance_km = max(int(distance_km or 0), 0)
    activity_budget = Decimal(activity_budget or 0)

    # --- 1. Travel cost (going there AND coming back = x2) -----------------
    round_trip_km = Decimal(distance_km * 2)
    if transportation.charged_per_person:
        # Bus / train: one ticket for each traveller
        travel_cost = round_trip_km * transportation.cost_per_km * travelers
        units = travelers
    else:
        # Car / bike: pay for the vehicle, people share it
        seats = max(transportation.seats_per_unit or 1, 1)
        units = ceil(travelers / seats)
        travel_cost = round_trip_km * transportation.cost_per_km * units

    # --- 2. Hotel cost (one room holds 2 people) --------------------------
    rooms = ceil(travelers / 2)
    hotel_rate = HOTEL_RATES.get(hotel_category, HOTEL_RATES["standard"])
    hotel_cost = hotel_rate * rooms * nights

    # --- 3. Food cost ------------------------------------------------------
    food_rate = FOOD_RATES.get(food_budget, FOOD_RATES["standard"])
    food_cost = food_rate * travelers * days

    # --- 4. Local transport inside the city -------------------------------
    groups = ceil(travelers / 4)
    local_transport_cost = LOCAL_TRANSPORT_PER_DAY * groups * days

    # --- 5. Activities: entry tickets + whatever extra the customer set ----
    entry_total = Decimal("0")
    for place in places or []:
        entry_total += Decimal(place.entry_fee or 0)
    activity_cost = entry_total * travelers + activity_budget

    # --- 6. Other expenses: a buffer on top of everything above -----------
    subtotal = travel_cost + hotel_cost + food_cost + local_transport_cost + activity_cost
    other_cost = subtotal * OTHER_EXPENSES_PERCENT

    total = subtotal + other_cost

    return {
        "travel_cost": _money(travel_cost),
        "hotel_cost": _money(hotel_cost),
        "food_cost": _money(food_cost),
        "local_transport_cost": _money(local_transport_cost),
        "activity_cost": _money(activity_cost),
        "other_cost": _money(other_cost),
        "total_cost": _money(total),
        # Extra details the page can show to explain the numbers
        "details": {
            "round_trip_km": int(round_trip_km),
            "vehicles_or_tickets": units,
            "rooms": rooms,
            "nights": nights,
            "days": days,
            "travelers": travelers,
            "per_person": _money(total / travelers),
            "entry_fees_total": _money(entry_total * travelers),
            "hotel_rate_per_room_night": _money(hotel_rate),
            "food_rate_per_person_day": _money(food_rate),
        },
    }


# ---------------------------------------------------------------------------
# Comparing the choices
# ---------------------------------------------------------------------------
# Two rules decide what gets called recommended, and both are written down
# rather than felt:
#
#   Transport - start at the cheapest, and only move up to a faster option
#   when the hours it saves are cheap enough to be worth buying. Flying
#   Bhimavaram to Ayodhya saves seventeen hours over the train and costs
#   36,000 rupees more, which is over 2,000 an hour; the train stays the
#   recommendation. On a short hop where a faster option costs a few hundred
#   more, it wins instead.
#
#   Room - the most comfortable class the destination's own published
#   per-person-per-day estimate will carry. That figure covers being there -
#   a bed, meals, getting about town - so it is compared against the same,
#   with the long-distance travel taken out. Leaving it in would judge a
#   1,450 km trip by a number that was never about the journey.
#
# An hour of the whole group's time, in rupees. Above this, a faster option
# is a luxury rather than a saving.
HOUR_WORTH_BUYING = Decimal("500")


def compare_transport(
    *,
    distance_km,
    travelers,
    days,
    chosen,
    hotel_category="standard",
    food_budget="standard",
    activity_budget=Decimal("0"),
    places=None,
):
    """
    The same trip priced under every transport option.

    Returns a list of dicts, cheapest first, each carrying the total, the
    door-to-door travel time, the difference against what was chosen, and
    whatever labels apply to it.
    """
    from ..models import Transportation

    rows = []
    for option in Transportation.objects.filter(is_active=True):
        costs = calculate_costs(
            distance_km=distance_km,
            travelers=travelers,
            days=days,
            transportation=option,
            hotel_category=hotel_category,
            food_budget=food_budget,
            activity_budget=activity_budget,
            places=places,
        )
        rows.append(
            {
                "option": option,
                "name": option.name,
                "is_chosen": chosen is not None and option.pk == chosen.pk,
                "total": costs["total_cost"],
                "per_person": costs["details"]["per_person"],
                "hours": estimate_travel_hours(distance_km, option),
                "labels": [],
            }
        )

    if not rows:
        return rows

    rows.sort(key=lambda row: row["total"])
    cheapest = rows[0]
    quickest = min(rows, key=lambda row: row["hours"])

    # Start at the cheapest and buy speed only where it is cheap. Working up
    # the list one option at a time means the comparison is always against
    # what is currently recommended, not against the bottom of the list.
    recommended = cheapest
    for row in rows[1:]:
        hours_saved = Decimal(str(recommended["hours"])) - Decimal(str(row["hours"]))
        if hours_saved <= 0:
            continue                      # dearer and no quicker: never
        extra = Decimal(row["total"]) - Decimal(recommended["total"])
        if extra / hours_saved <= HOUR_WORTH_BUYING:
            recommended = row

    cheapest["labels"].append("Cheapest")
    quickest["labels"].append("Fastest")
    if recommended is not cheapest and recommended is not quickest:
        recommended["labels"].append("Best balance")
    recommended["is_recommended"] = True

    chosen_row = next((row for row in rows if row["is_chosen"]), None)
    for row in rows:
        row.setdefault("is_recommended", False)
        row["difference"] = (
            _money(row["total"] - chosen_row["total"]) if chosen_row else None
        )
        if row["is_chosen"]:
            row["labels"].append("Your choice")
    return rows


def compare_rooms(
    *,
    distance_km,
    travelers,
    days,
    transportation,
    chosen_category,
    benchmark_per_day=None,
    food_budget="standard",
    activity_budget=Decimal("0"),
    places=None,
):
    """
    The same trip priced under every room class.

    benchmark_per_day is the destination's own published per-person-per-day
    estimate. When it is given, the recommended class is the dearest one that
    still comes in under it - the most comfortable room the destination's own
    figure says the trip can carry.
    """
    rows = []
    for category, label in (
        ("budget", "Budget"),
        ("standard", "Standard"),
        ("deluxe", "Deluxe"),
        ("luxury", "Luxury"),
    ):
        costs = calculate_costs(
            distance_km=distance_km,
            travelers=travelers,
            days=days,
            transportation=transportation,
            hotel_category=category,
            food_budget=food_budget,
            activity_budget=activity_budget,
            places=places,
        )
        details = costs["details"]
        heads = max(int(travelers or 1), 1)
        length = max(int(days or 1), 1)
        # What being there costs: a bed, meals, getting around town, tickets,
        # and their share of the buffer - but not the journey, and not the
        # journey's share of the buffer either. Subtracting travel from the
        # total would leave that second part behind, and a longer road would
        # quietly raise a figure that is supposed to be about the destination.
        on_the_ground = (
            costs["hotel_cost"]
            + costs["food_cost"]
            + costs["local_transport_cost"]
            + costs["activity_cost"]
        ) * (1 + OTHER_EXPENSES_PERCENT)
        rows.append(
            {
                "category": category,
                "label": label,
                "is_chosen": category == chosen_category,
                "rate": details["hotel_rate_per_room_night"],
                "rooms": details["rooms"],
                "nights": details["nights"],
                "total": costs["total_cost"],
                "per_person_per_day": _money(on_the_ground / heads / length),
                "labels": [],
            }
        )

    rows[0]["labels"].append("Cheapest")

    recommended = None
    if benchmark_per_day:
        benchmark = Decimal(benchmark_per_day)
        within = [row for row in rows if row["per_person_per_day"] <= benchmark]
        recommended = within[-1] if within else rows[0]
    for row in rows:
        row["is_recommended"] = recommended is not None and row is recommended
        if row["is_recommended"]:
            row["labels"].append("Recommended")
        if row["is_chosen"]:
            row["labels"].append("Your choice")

    chosen_row = next((row for row in rows if row["is_chosen"]), None)
    for row in rows:
        row["difference"] = (
            _money(row["total"] - chosen_row["total"]) if chosen_row else None
        )
    return rows


# ---------------------------------------------------------------------------
# Day-by-day itinerary
# ---------------------------------------------------------------------------
def build_itinerary(*, source, destination_name, days, places, travelers=1, transport_name="Car"):
    """
    Spread the chosen places across the days and return a list like:

        [{"day": 1, "title": "Day 1", "items": ["Pune to Mumbai", "Gateway of India"]}, ...]
    """
    days = max(int(days or 1), 1)
    places = list(places or [])

    # Put the busiest sightseeing in the middle days when the trip is longer
    plan = [[] for _ in range(days)]

    # Day 1 always starts with the journey
    plan[0].append(f"Travel {source} to {destination_name} by {transport_name}")
    plan[0].append("Hotel check-in and rest")

    # Last day always ends with the return journey
    if days > 1:
        plan[days - 1].append(f"Return journey {destination_name} to {source}")

    # How many sightseeing slots does each day have?
    # Day 1 and the last day are partly used by travel, so they get fewer.
    capacity = []
    for i in range(days):
        if days == 1:
            capacity.append(max(len(places), 1))
        elif i == 0:
            capacity.append(2)
        elif i == days - 1:
            capacity.append(1)
        else:
            capacity.append(3)

    # Fill the days one by one
    index = 0
    for day_index in range(days):
        for _ in range(capacity[day_index]):
            if index >= len(places):
                break
            place = places[index]
            # Insert sightseeing BEFORE the return-journey line on the last day
            if day_index == days - 1 and days > 1:
                plan[day_index].insert(len(plan[day_index]) - 1, place.name)
            else:
                plan[day_index].append(place.name)
            index += 1

    # Anything left over goes on the middle days
    while index < len(places):
        target = min(1, days - 1) if days > 1 else 0
        plan[target].append(places[index].name)
        index += 1

    # Add a friendly filler for empty days. On the last day the filler must go
    # BEFORE the return journey, so the journey home stays the final item.
    filler = "Free time / local sightseeing / shopping"
    for day_index in range(days):
        if len(plan[day_index]) <= 1:
            if day_index == days - 1 and days > 1:
                plan[day_index].insert(len(plan[day_index]) - 1, filler)
            else:
                plan[day_index].append(filler)

    return [
        {"day": i + 1, "title": f"Day {i + 1}", "items": items}
        for i, items in enumerate(plan)
    ]


def itinerary_to_text(itinerary):
    """Turn the itinerary list into plain text we can save in the database."""
    lines = []
    for day in itinerary:
        lines.append(f"{day['title']}:")
        for item in day["items"]:
            lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).strip()
