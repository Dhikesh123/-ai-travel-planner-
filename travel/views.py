"""
Views = the Python functions that build each web page.

A view receives a request, does some work, and returns a rendered HTML page.
"""
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
    TouristPlace,
    Transportation,
    Trip,
    UploadedImage,
)
from .services import ai_service
from .utils import recalculate_trip


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
            "places": TouristPlace.objects.select_related("destination")[:8],
            "transports": Transportation.objects.filter(is_active=True),
            "ai_ready": ai_service.is_configured(),
        },
    )


def destination_list(request):
    """Browse and search destinations."""
    query = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()

    destinations = Destination.objects.annotate(place_count=Count("places"))
    if query:
        destinations = destinations.filter(
            Q(name__icontains=query)
            | Q(state__icontains=query)
            | Q(description__icontains=query)
        )
    if category:
        destinations = destinations.filter(places__category=category).distinct()

    return render(
        request,
        "destinations.html",
        {
            "destinations": destinations,
            "query": query,
            "category": category,
            "categories": TouristPlace.CATEGORY_CHOICES,
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
        form = TripForm(initial={"travel_date": timezone.localdate(), "travelers": 2, "days": 3})

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

    return render(
        request,
        "trip_detail.html",
        {
            "trip": trip,
            "trip_places": trip_places,
            "itinerary_days": sorted(itinerary.items()),
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
