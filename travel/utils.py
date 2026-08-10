"""
Small shared helpers used by both the web pages and the API, so the two
never disagree about how a trip is calculated.
"""
from .models import TouristPlace, TripCost, TripPlace
from .services import travel_service


def recalculate_trip(trip, place_ids=None):
    """
    Take a saved Trip, work out its distance, costs and itinerary, and store
    everything. Returns the cost dictionary.

    place_ids = list of TouristPlace ids the customer selected. Pass None to
    keep whatever places are already attached to the trip.
    """
    # 1. Which places are we visiting?
    if place_ids is not None:
        places = list(
            TouristPlace.objects.filter(id__in=place_ids, destination=trip.destination)
        )
        # Replace the old selection with the new one
        TripPlace.objects.filter(trip=trip).delete()
    else:
        places = [tp.place for tp in trip.trip_places.select_related("place")]

    # 2. Distance and travel time
    distance_km, is_known = travel_service.estimate_distance(trip.source, trip.destination.name)
    trip.distance_km = distance_km
    trip.travel_hours = travel_service.estimate_travel_hours(distance_km, trip.transportation)

    # 3. Day-by-day itinerary
    itinerary = travel_service.build_itinerary(
        source=trip.source,
        destination_name=trip.destination.name,
        days=trip.days,
        places=places,
        travelers=trip.travelers,
        transport_name=trip.transportation.name,
    )
    trip.itinerary_text = travel_service.itinerary_to_text(itinerary)
    trip.save()

    # 4. Save which place happens on which day
    if place_ids is not None:
        place_by_name = {p.name: p for p in places}
        for day in itinerary:
            for order, item in enumerate(day["items"]):
                place = place_by_name.get(item)
                if place:
                    TripPlace.objects.get_or_create(
                        trip=trip,
                        place=place,
                        defaults={"day_number": day["day"], "order": order},
                    )

    # 5. Costs
    costs = travel_service.calculate_costs(
        distance_km=distance_km,
        travelers=trip.travelers,
        days=trip.days,
        transportation=trip.transportation,
        hotel_category=trip.hotel_category,
        food_budget=trip.food_budget,
        activity_budget=trip.activity_budget,
        places=places,
    )

    TripCost.objects.update_or_create(
        trip=trip,
        defaults={
            "travel_cost": costs["travel_cost"],
            "hotel_cost": costs["hotel_cost"],
            "food_cost": costs["food_cost"],
            "local_transport_cost": costs["local_transport_cost"],
            "activity_cost": costs["activity_cost"],
            "other_cost": costs["other_cost"],
            "total_cost": costs["total_cost"],
        },
    )

    costs["distance_is_known"] = is_known
    costs["itinerary"] = itinerary
    return costs


def trip_summary_text(trip):
    """A short plain-text description of a trip, used as context for the AI."""
    lines = [
        f"From: {trip.source}",
        f"To: {trip.destination.name}",
        f"Travel date: {trip.travel_date}",
        f"Travellers: {trip.travelers}",
        f"Days: {trip.days}",
        f"Transport: {trip.transportation.name}",
        f"Hotel: {trip.get_hotel_category_display()}",
        f"Food budget: {trip.get_food_budget_display()}",
        f"Estimated distance: {trip.distance_km} km (estimate)",
    ]
    cost = getattr(trip, "cost", None)
    if cost:
        lines.append(f"Estimated total cost: Rs {cost.total_cost} (demonstration estimate)")
    places = [tp.place.name for tp in trip.trip_places.select_related("place")]
    if places:
        lines.append("Selected places: " + ", ".join(places))
    return "\n".join(lines)
