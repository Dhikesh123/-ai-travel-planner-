"""
Views = the Python functions that build each web page.

A view receives a request, does some work, and returns a rendered HTML page.
"""
from itertools import chain, zip_longest

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q, Sum
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
from .services import ai_service
from .utils import recalculate_trip

# How many "you could also visit" places the trip page offers alongside the
# itinerary. Fourteen fills the sidebar on a tall screen without turning it
# into a second list to read.
SUGGESTION_LIMIT = 14

# Categories a family with young children can take on without planning the day
# around it. "adventure" is the deliberate omission - rafting and trekking are
# not the same kind of afternoon - and so is "shopping", which is an errand.
FAMILY_CATEGORIES = {"temple", "nature", "beach", "museum", "food"}

# How many of the suggestions carry the "Recommended" badge. Four is about one
# screenful at the top of the sidebar; badging more of them makes the word stop
# meaning anything.
RECOMMENDED_COUNT = 4


def _positive_int(raw, fallback):
    """A whole number above zero from the query string, or the fallback."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


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
            "ai_ready": ai_service.is_configured(),
        },
    )


# Budget bands for the explorer, in rupees per person per day. The boundaries
# sit between the clusters in the sample data rather than on round numbers, so
# each band actually returns something.
BUDGET_BANDS = {
    "low": (None, 2000),
    "mid": (2000, 2800),
    "high": (2800, None),
}

# Trip lengths, matched against recommended_days. The boundaries follow the
# data rather than round numbers: the seeded destinations only recommend 2, 3
# or 4 days, so a "5+" band would be an option that can never match.
DURATION_BANDS = {
    "short": (None, 2),
    "medium": (3, 3),
    "long": (4, None),
}


def destination_list(request):
    """Browse, search and filter destinations."""
    query = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    theme = (request.GET.get("theme") or "").strip()
    budget = (request.GET.get("budget") or "").strip()
    duration = (request.GET.get("duration") or "").strip()
    region = (request.GET.get("region") or "").strip()

    destinations = Destination.objects.annotate(place_count=Count("places"))

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

    if budget in BUDGET_BANDS:
        low, high = BUDGET_BANDS[budget]
        if low is not None:
            destinations = destinations.filter(estimated_cost_per_day__gte=low)
        if high is not None:
            destinations = destinations.filter(estimated_cost_per_day__lt=high)

    if duration in DURATION_BANDS:
        low, high = DURATION_BANDS[duration]
        if low is not None:
            destinations = destinations.filter(recommended_days__gte=low)
        if high is not None:
            destinations = destinations.filter(recommended_days__lte=high)

    # Everything seeded is in India, so "international" correctly returns
    # nothing rather than pretending otherwise.
    if region == "domestic":
        destinations = destinations.filter(country__iexact="India")
    elif region == "international":
        destinations = destinations.exclude(country__iexact="India")

    # One distinct() at the end. Both the category and theme filters join to a
    # multi-valued relation, so a destination with four beaches would otherwise
    # come back four times - and twice over if both filters are on.
    destinations = destinations.prefetch_related("themes").distinct()

    return render(
        request,
        "destinations.html",
        {
            "destinations": destinations,
            "query": query,
            "category": category,
            "theme": theme,
            "budget": budget,
            "duration": duration,
            "region": region,
            "categories": TouristPlace.CATEGORY_CHOICES,
            "themes": Theme.objects.all(),
            "result_count": destinations.count(),
            "any_filter": any([query, category, theme, budget, duration, region]),
        },
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
        form = TripForm(initial=initial)

    return render(
        request,
        "planner.html",
        {
            "form": form,
            "destinations": Destination.objects.prefetch_related("places"),
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

    # Top up from further afield until the sidebar is full: first the same
    # state, which is the realistic "while you are there" add-on, then anywhere
    # else. Without the second pass a destination that is the only one in its
    # state - Goa, in the sample data - offers almost nothing.
    for extra in (
        TouristPlace.objects.filter(destination__state=trip.destination.state).exclude(
            destination=trip.destination
        ),
        TouristPlace.objects.exclude(destination__state=trip.destination.state),
    ):
        if len(suggested_places) >= SUGGESTION_LIMIT:
            break
        already = chosen_ids + [p.pk for p in suggested_places]
        for place in _spread_by_category(
            extra.exclude(pk__in=already)
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

    return render(
        request,
        "trip_detail.html",
        {
            "trip": trip,
            "trip_places": trip_places,
            "itinerary_days": sorted(itinerary.items()),
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
            "destinations": Destination.objects.prefetch_related("places"),
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
