"""
Views = the Python functions that build each web page.

A view receives a request, does some work, and returns a rendered HTML page.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from itertools import chain, zip_longest

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ImageUploadForm, ProfileForm, RegisterForm, TripForm
from .models import (
    ChatMessage,
    Destination,
    Theme,
    TouristPlace,
    Transportation,
    Trip,
    UploadedImage,
)
from .services import ai_service, geo_service, travel_service
from .utils import recalculate_trip

# How many "you could also visit" places the trip page offers alongside the
# itinerary. Fourteen fills the sidebar on a tall screen without turning it
# into a second list to read.
SUGGESTION_LIMIT = 24

# Categories a family with young children can take on without planning the day
# around it. "adventure" is the deliberate omission - rafting and trekking are
# not the same kind of afternoon - and so is "shopping", which is an errand.
FAMILY_CATEGORIES = {"temple", "nature", "beach", "museum", "food"}

# How many of the suggestions carry the "Recommended" badge. Four is about one
# screenful at the top of the sidebar; badging more of them makes the word stop
# meaning anything.
RECOMMENDED_COUNT = 4


# When a sightseeing day is assumed to start. Nine is early enough for a full
# day and late enough to have had breakfast.
DAY_STARTS_AT = time(9, 0)

# Allowed between one place and the next. It is a flat allowance, NOT a routed
# journey time: the database holds distances between cities, never between two
# places inside one. The template says so rather than letting it read as a
# calculated figure.
LOCAL_HOP_MINUTES = 30

# Where the morning ends and the evening begins, for grouping the day.
MORNING_ENDS_AT = time(12, 0)
AFTERNOON_ENDS_AT = time(17, 0)

# Past this, the day has more in it than a day holds. Rather than silently
# laying out a schedule that runs to midnight, the page says so - the
# schedule is honest arithmetic on the durations, and the arithmetic is the
# useful warning.
LONG_DAY_ENDS_AFTER = time(20, 0)


def _slot_for(moment):
    """Morning, Afternoon or Evening for a time of day."""
    if moment < MORNING_ENDS_AT:
        return "Morning"
    if moment < AFTERNOON_ENDS_AT:
        return "Afternoon"
    return "Evening"


def _build_day_plan(itinerary_days, trip):
    """
    Turn "these places on day 2" into an hour-by-hour day.

    Clock times are laid out from DAY_STARTS_AT, each place taking its own
    visit_duration_minutes with LOCAL_HOP_MINUTES between one and the next.
    Everything here is derived from data already on the place - nothing about
    the schedule is invented beyond the two constants above, both of which the
    page states openly.
    """
    plan = []
    for day_number, places in itinerary_days:
        cursor = datetime.combine(date.today(), DAY_STARTS_AT)
        slots, day_cost, day_minutes = {}, Decimal("0"), 0

        for index, place in enumerate(places):
            minutes = place.visit_duration_minutes or 60
            starts = cursor
            ends = starts + timedelta(minutes=minutes)

            slot = _slot_for(starts.time())
            slots.setdefault(slot, []).append(
                {
                    "place": place,
                    "starts": starts,
                    "ends": ends,
                    "minutes": minutes,
                    # Only shown between places, so the last of the day does
                    # not claim a journey to nowhere.
                    "hop_next": LOCAL_HOP_MINUTES if index < len(places) - 1 else 0,
                }
            )

            day_cost += place.entry_fee or Decimal("0")
            day_minutes += minutes
            cursor = ends + timedelta(minutes=LOCAL_HOP_MINUTES)

        # The trip's own dates, when it has them, so "Day 2" carries a date.
        day_date = None
        if trip.travel_date:
            day_date = trip.travel_date + timedelta(days=day_number - 1)

        plan.append(
            {
                "day_number": day_number,
                "date": day_date,
                # Fixed order: a day always reads morning to evening, even if
                # only the afternoon has anything in it.
                "slots": [
                    {"name": name, "items": slots[name]}
                    for name in ("Morning", "Afternoon", "Evening")
                    if name in slots
                ],
                "place_count": len(places),
                "cost": day_cost,
                "minutes": day_minutes,
                "ends_at": cursor - timedelta(minutes=LOCAL_HOP_MINUTES),
                "is_packed": (
                    (cursor - timedelta(minutes=LOCAL_HOP_MINUTES)).time()
                    > LONG_DAY_ENDS_AFTER
                ),
            }
        )
    return plan


def _positive_int(raw, fallback):
    """A whole number above zero from the query string, or the fallback."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def _destinations_by_relevance(trip):
    """
    Every other destination, in the order this particular traveller would
    consider it.

    The trip already knows both ends of the journey, so the same grouping the
    planner uses answers this too - read back to front, because someone who
    has arrived cares first about what is around them, then about what they
    passed, and last about what was near home.

    Whatever is left over is sorted by how far it is from the destination.
    That matters more than it sounds: the old code finished the list with
    "anywhere else, alphabetically", which is how a trip to Ayodhya ended up
    suggesting Agnitheertham in Tamil Nadu, 2,000 km away, because it starts
    with an A.
    """
    ordered, seen = [], {trip.destination_id}

    for _heading, _note, rows in reversed(
        geo_service.journey_groups(trip.source or "", trip.destination)
    ):
        # Each group runs start-first, because that is the order they would be
        # reached. Reading it backwards puts the end of the road first, so
        # Varanasi - three hours from Ayodhya - is offered before
        # Visakhapatnam, which was a thousand kilometres ago.
        for destination in reversed(rows):
            if destination.pk not in seen:
                ordered.append(destination)
                seen.add(destination.pk)

    rest = list(Destination.objects.exclude(pk__in=seen))
    end = (trip.destination.latitude, trip.destination.longitude)
    if end[0] is not None:
        def how_far(destination):
            km = geo_service.distance_km(
                (destination.latitude, destination.longitude), end
            )
            # a destination with no coordinates sorts last rather than crashing
            return km if km is not None else float("inf")

        rest.sort(key=how_far)
    ordered.extend(rest)
    return ordered


def _spread_by_category(queryset, limit):
    """
    Take places one category at a time instead of cheapest-first.

    Ordering purely by price buries whole categories. The sample data is seven
    historical sites against three temples, so a straight cheapest-first list
    runs historical almost the whole way down and the temples never surface.
    Round-robin puts a temple, a beach and a museum near the top where someone
    reading the sidebar will actually see them.
    """
    buckets = {}
    # Capped rather than unbounded: the spread only needs enough candidates to
    # fill the sidebar, not the whole table.
    for place in queryset[: limit * 3]:
        buckets.setdefault(place.category, []).append(place)

    # The cheapest place in a category decides how early that category starts,
    # so a free temple still outranks a paid museum.
    ordered = sorted(
        buckets.values(), key=lambda bucket: (bucket[0].entry_fee, bucket[0].name)
    )
    spread = chain.from_iterable(zip_longest(*ordered))
    return [place for place in spread if place is not None][:limit]


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
def home(request):
    """The landing page everyone sees."""
    return render(
        request,
        "home.html",
        {
            "destinations": Destination.objects.filter(is_popular=True)[:6],
            # The hero's trip search offers every destination, not just the six
            # featured as cards further down the page.
            "all_destinations": Destination.objects.only("pk", "name", "state"),
            "places": TouristPlace.objects.select_related("destination")[:8],
            "transports": Transportation.objects.filter(is_active=True),
            # The round category chips under the search panel. Trip themes
            # only: the pilgrimage circuits have their own row on the
            # destinations page and would double the length of this one.
            "themes": Theme.objects.filter(kind=Theme.KIND_TRIP).order_by("display_order"),
            "ai_ready": ai_service.is_configured(),
        },
    )


# The ceiling on the per-day slider. Nothing in the catalogue costs near this
# much a day - the dearest is 3,500 - but a slider is not a fixed band: values
# above the top of the data simply include everything, which is a truthful
# answer rather than a dead option. The headroom is there so the control still
# makes sense as more expensive destinations are added.
BUDGET_PER_DAY_MAX = 10000
BUDGET_PER_DAY_STEP = 250

# Trip lengths, matched against recommended_days. The boundaries follow the
# data rather than round numbers: the seeded destinations only recommend 2, 3
# or 4 days, so a "5+" band would be an option that can never match.
DURATION_BANDS = {
    "short": (None, 2),
    "medium": (3, 3),
    "long": (4, None),
}


def destination_list(request, preset_theme=None, heading=None, intro=None):
    """
    Browse, search and filter destinations.

    The Family and Temple sections are this same page with a theme already
    chosen and its own heading, rather than two more views that would drift
    apart from this one as the filters change.
    """
    query = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    theme = (request.GET.get("theme") or preset_theme or "").strip()
    circuit = (request.GET.get("circuit") or "").strip()
    # A ceiling in rupees per person per day, not one of three bands.
    budget_day = _positive_int(request.GET.get("budget_day"), 0)
    duration = (request.GET.get("duration") or "").strip()
    region = (request.GET.get("region") or "").strip()

    # "What can I do with X?" - a whole-trip budget rather than a per-day
    # band. Party size and length are part of the question: 10,000 is a
    # comfortable three days for two and an impossible week for four.
    max_total = _positive_int(request.GET.get("max_total"), 0)
    party = _positive_int(request.GET.get("travellers"), 2)
    trip_days = _positive_int(request.GET.get("trip_days"), 3)

    # Annotated rather than worked out per row in Python, so the budget
    # filter runs in the database and the cards can show the figure they
    # were filtered on.
    destinations = Destination.objects.annotate(
        place_count=Count("places"),
        trip_total=ExpressionWrapper(
            F("estimated_cost_per_day") * party * trip_days,
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    if query:
        destinations = destinations.filter(
            Q(name__icontains=query)
            | Q(state__icontains=query)
            | Q(description__icontains=query)
        )
    if category:
        destinations = destinations.filter(places__category=category)
    if theme:
        destinations = destinations.filter(themes__slug=theme)
    # Circuit is a second, narrower theme. Filtering both means a
    # destination must carry each, which is the useful reading of
    # "temples" plus "Jyotirlinga".
    if circuit:
        destinations = destinations.filter(themes__slug=circuit)

    if budget_day:
        destinations = destinations.filter(estimated_cost_per_day__lte=budget_day)

    if duration in DURATION_BANDS:
        low, high = DURATION_BANDS[duration]
        if low is not None:
            destinations = destinations.filter(recommended_days__gte=low)
        if high is not None:
            destinations = destinations.filter(recommended_days__lte=high)

    # Everything seeded is in India, so "international" correctly returns
    # nothing rather than pretending otherwise.
    if max_total:
        destinations = destinations.filter(trip_total__lte=max_total)

    if region == "domestic":
        destinations = destinations.filter(country__iexact="India")
    elif region == "international":
        destinations = destinations.exclude(country__iexact="India")

    # One distinct() at the end. Both the category and theme filters join to a
    # multi-valued relation, so a destination with four beaches would otherwise
    # come back four times - and twice over if both filters are on.
    destinations = destinations.prefetch_related("themes").distinct()

    heading = heading or "Destinations"
    intro = intro or "Search by name, or filter by theme, budget and trip length."

    return render(
        request,
        "destinations.html",
        {
            "destinations": destinations,
            "query": query,
            "category": category,
            "theme": theme,
            "circuit": circuit,
            "budget_day": budget_day or "",
            "budget_day_max": BUDGET_PER_DAY_MAX,
            "budget_day_step": BUDGET_PER_DAY_STEP,
            # The dearest destination, so the page can say when the slider has
            # gone past the point where it filters anything at all.
            "dearest_per_day": (
                Destination.objects.order_by("-estimated_cost_per_day")
                .values_list("estimated_cost_per_day", flat=True)
                .first()
                or 0
            ),
            "duration": duration,
            "region": region,
            "max_total": max_total or "",
            # Quoted in the empty state so "nothing fits" comes with the
            # number that would.
            "cheapest_total": (
                Destination.objects.order_by("estimated_cost_per_day")
                .values_list("estimated_cost_per_day", flat=True)
                .first()
                or 0
            )
            * party
            * trip_days,
            "party": party,
            "trip_days": trip_days,
            "categories": TouristPlace.CATEGORY_CHOICES,
            "themes": Theme.objects.filter(kind=Theme.KIND_TRIP),
            "circuits": Theme.objects.filter(kind=Theme.KIND_PILGRIMAGE),
            "heading": heading,
            "intro": intro,
            "result_count": destinations.count(),
            "any_filter": any(
                [
                    query,
                    category,
                    theme,
                    circuit,
                    budget_day,
                    duration,
                    region,
                    max_total,
                ]
            ),
        },
    )


def family_travel(request):
    """Destinations that suit a trip with children."""
    return destination_list(
        request,
        preset_theme="family",
        heading="Family Travel",
        intro=(
            "Places that work with children along: shorter days, calmer "
            "sights and somewhere to eat nearby."
        ),
    )


def spiritual_travel(request):
    """Temple towns and the pilgrimage circuits."""
    return destination_list(
        request,
        preset_theme="temple",
        heading="Temple & Spiritual Travel",
        intro=(
            "Temple towns across India, filterable by circuit - Jyotirlinga, "
            "Char Dham, Shakti Peetha - or by what suits a family."
        ),
    )


def destination_detail(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    return render(
        request,
        "destination_detail.html",
        {"destination": destination, "places": destination.places.all()},
    )


# ---------------------------------------------------------------------------
# Register / login / logout
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account is ready.")
            return redirect("dashboard")
        messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


class CustomerLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True
    authentication_form = AuthenticationForm

    def form_invalid(self, form):
        messages.error(self.request, "Wrong username or password. Please try again.")
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# ---------------------------------------------------------------------------
# Customer dashboard and profile
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    trips = Trip.objects.filter(user=request.user).select_related("destination", "cost")
    total_value = (
        Trip.objects.filter(user=request.user).aggregate(total=Sum("cost__total_cost"))["total"]
        or 0
    )
    return render(
        request,
        "dashboard.html",
        {
            "recent_trips": trips[:4],
            "trip_count": trips.count(),
            "upcoming_count": trips.filter(travel_date__gte=timezone.localdate()).count(),
            "total_value": total_value,
            "ai_ready": ai_service.is_configured(),
        },
    )


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
        messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "profile.html", {"form": form, "profile": profile})


# ---------------------------------------------------------------------------
# Travel planner
# ---------------------------------------------------------------------------
def _place_groups_for(form):
    """
    The places worth offering, grouped by where they fall on the journey.

    Read from whatever the form is holding - the values the customer brought
    from the home page, or the ones already saved on a trip being edited - so
    the first paint of the page is already the right list rather than all 193
    places waiting for JavaScript to hide most of them.

    JavaScript takes over from here: /api/journey-places/ returns the same
    groups whenever either address changes.
    """
    data = form.initial or {}
    source = (form.data.get("source") if form.data else None) or data.get("source") or ""

    destination = data.get("destination") or (form.data.get("destination") if form.data else None)
    if hasattr(destination, "pk"):
        destination_id = destination.pk
    elif str(destination or "").isdigit():
        destination_id = int(destination)
    else:
        return []

    chosen = Destination.objects.filter(pk=destination_id).first()
    if chosen is None:
        return []
    return geo_service.journey_groups(str(source), chosen)


@login_required
def planner(request):
    """Create a new trip."""
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.user = request.user
            trip.save()

            place_ids = [int(i) for i in request.POST.getlist("places") if i.isdigit()]
            recalculate_trip(trip, place_ids)

            messages.success(request, "Your trip has been planned and saved.")
            return redirect("trip_detail", pk=trip.pk)
        messages.error(request, "Please fix the errors below.")
    else:
        # The home page's trip search posts here by GET, so whatever the
        # customer already typed on the hero card arrives filled in rather
        # than being asked for a second time. Anything absent or unparseable
        # falls back to the same defaults the page has always opened with.
        initial = {
            "travel_date": request.GET.get("travel_date") or timezone.localdate(),
            "travelers": _positive_int(request.GET.get("travelers"), 2),
            "days": _positive_int(request.GET.get("days"), 3),
        }
        if request.GET.get("source"):
            initial["source"] = request.GET["source"].strip()
        if (request.GET.get("destination") or "").isdigit():
            initial["destination"] = request.GET["destination"]
        # The home page's transport chips arrive here as a pk.
        if (request.GET.get("transportation") or "").isdigit():
            initial["transportation"] = request.GET["transportation"]
        form = TripForm(initial=initial)

    return render(
        request,
        "planner.html",
        {
            "form": form,
            "place_groups": _place_groups_for(form),
            "transports": Transportation.objects.filter(is_active=True),
        },
    )


@login_required
def trip_list(request):
    trips = Trip.objects.filter(user=request.user).select_related("destination", "cost")
    return render(request, "trips.html", {"trips": trips})


@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(
        Trip.objects.select_related("destination", "transportation", "cost"),
        pk=pk,
        user=request.user,
    )
    trip_places = trip.trip_places.select_related("place").all()

    # Rebuild the itinerary list for display from the saved day numbers
    itinerary = {}
    for tp in trip_places:
        itinerary.setdefault(tp.day_number, []).append(tp.place)

    # Places worth adding: everything at this destination that is not already
    # in the plan, then - if that runs thin - places from other destinations in
    # the same state, which are the realistic "while you are there" additions.
    chosen_ids = [tp.place_id for tp in trip_places]

    suggested_places = _spread_by_category(
        TouristPlace.objects.filter(destination=trip.destination)
        .select_related("destination")
        .exclude(pk__in=chosen_ids)
        .order_by("entry_fee", "name"),
        SUGGESTION_LIMIT,
    )

    # Top up from other destinations until the sidebar is full, taking them in
    # the order this journey makes them worth considering - around where you
    # are going, then what the road passed, then near where you set off, and
    # only after all of that the rest of the country by distance.
    #
    # One city at a time rather than one big query, so the list stays grouped
    # by place instead of interleaving six cities by entry fee.
    for other in _destinations_by_relevance(trip):
        if len(suggested_places) >= SUGGESTION_LIMIT:
            break
        already = chosen_ids + [p.pk for p in suggested_places]
        for place in _spread_by_category(
            TouristPlace.objects.filter(destination=other)
            .exclude(pk__in=already)
            .select_related("destination")
            .order_by("entry_fee", "name"),
            SUGGESTION_LIMIT - len(suggested_places),
        ):
            # Read in the template to label these with their own city.
            place.is_nearby = True
            suggested_places.append(place)

    # Badges the template reads. "Recommended" goes to the head of the spread,
    # which is where the cheapest place of each category has surfaced, so the
    # badged four are already a mixed set rather than four of one kind.
    for position, place in enumerate(suggested_places):
        place.is_recommended = position < RECOMMENDED_COUNT
        place.is_family = place.category in FAMILY_CATEGORIES

    # What the same trip would cost under every other transport option and
    # room class. Priced by the same calculator that produced the saved
    # figures, so the comparison and the total can never drift apart.
    chosen_places = [tp.place for tp in trip_places]
    shared = {
        "distance_km": trip.distance_km,
        "travelers": trip.travelers,
        "days": trip.days,
        "food_budget": trip.food_budget,
        "activity_budget": trip.activity_budget,
        "places": chosen_places,
    }
    transport_options = travel_service.compare_transport(
        chosen=trip.transportation, hotel_category=trip.hotel_category, **shared
    )
    room_options = travel_service.compare_rooms(
        transportation=trip.transportation,
        chosen_category=trip.hotel_category,
        # The destination's own published per-day estimate is the yardstick.
        benchmark_per_day=trip.destination.estimated_cost_per_day,
        **shared,
    )

    return render(
        request,
        "trip_detail.html",
        {
            "trip": trip,
            "trip_places": trip_places,
            "transport_options": transport_options,
            "room_options": room_options,
            "cost_benchmark": trip.destination.estimated_cost_per_day,
            "itinerary_days": sorted(itinerary.items()),
            "day_plan": _build_day_plan(sorted(itinerary.items()), trip),
            "day_starts_at": DAY_STARTS_AT,
            "local_hop_minutes": LOCAL_HOP_MINUTES,
            "suggested_places": suggested_places,
            "ai_ready": ai_service.is_configured(),
        },
    )


@login_required
def trip_edit(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    selected_ids = list(trip.trip_places.values_list("place_id", flat=True))

    if request.method == "POST":
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            trip = form.save()
            place_ids = [int(i) for i in request.POST.getlist("places") if i.isdigit()]
            recalculate_trip(trip, place_ids)
            messages.success(request, "Your trip has been updated.")
            return redirect("trip_detail", pk=trip.pk)
        messages.error(request, "Please fix the errors below.")
    else:
        form = TripForm(instance=trip)

    return render(
        request,
        "planner.html",
        {
            "form": form,
            "trip": trip,
            "selected_ids": selected_ids,
            "place_groups": _place_groups_for(form),
            "transports": Transportation.objects.filter(is_active=True),
            "editing": True,
        },
    )


@login_required
@require_POST
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    trip.delete()
    messages.success(request, "Trip deleted.")
    return redirect("trip_list")


# ---------------------------------------------------------------------------
# Cost calculator (standalone page)
# ---------------------------------------------------------------------------
@login_required
def calculator(request):
    return render(
        request,
        "calculator.html",
        {
            "destinations": Destination.objects.all(),
            "transports": Transportation.objects.filter(is_active=True),
        },
    )


# ---------------------------------------------------------------------------
# AI features
# ---------------------------------------------------------------------------
@login_required
def chatbot(request):
    history = ChatMessage.objects.filter(user=request.user).order_by("created_at")[:100]
    return render(
        request,
        "chatbot.html",
        {"history": history, "ai_ready": ai_service.is_configured()},
    )


@login_required
def image_recognition(request):
    form = ImageUploadForm()
    return render(
        request,
        "image_recognition.html",
        {
            "form": form,
            "uploads": UploadedImage.objects.filter(user=request.user)[:6],
            "ai_ready": ai_service.is_configured(),
        },
    )


@login_required
def voice_assistant(request):
    return render(
        request,
        "voice.html",
        {"ai_ready": ai_service.is_configured()},
    )


# ---------------------------------------------------------------------------
# Admin (staff only) dashboard
# ---------------------------------------------------------------------------
def staff_required(view_func):
    """Only staff members may open these pages."""
    from django.contrib.admin.views.decorators import staff_member_required

    return staff_member_required(view_func, login_url="login")


@staff_required
def admin_dashboard(request):
    from django.contrib.auth.models import User

    trips = Trip.objects.select_related("user", "destination", "cost")

    popular = (
        Destination.objects.annotate(trip_count=Count("trips"))
        .filter(trip_count__gt=0)
        .order_by("-trip_count")[:5]
    )

    total_value = trips.aggregate(total=Sum("cost__total_cost"))["total"] or 0

    return render(
        request,
        "admin_dashboard.html",
        {
            "total_customers": User.objects.filter(is_staff=False).count(),
            "total_trips": trips.count(),
            "total_destinations": Destination.objects.count(),
            "total_places": TouristPlace.objects.count(),
            "total_chats": ChatMessage.objects.count(),
            "total_images": UploadedImage.objects.count(),
            "total_value": total_value,
            "recent_customers": User.objects.filter(is_staff=False).order_by("-date_joined")[:6],
            "recent_trips": trips.order_by("-created_at")[:8],
            "popular_destinations": popular,
            "most_visited": popular[0] if popular else None,
        },
    )
