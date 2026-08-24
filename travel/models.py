"""
Database models for the AI Travel Planner.

A "model" is one Python class = one database table.
Each attribute on the class = one column in that table.

Relationships (read the arrows as "has many"):

    User -> Profile              (one-to-one:  each user has exactly 1 profile)
    User -> Trip                 (one-to-many: a user can save many trips)
    User -> ChatMessage          (one-to-many: a user has many chat messages)
    User -> UploadedImage        (one-to-many: a user uploads many images)

    Destination -> TouristPlace  (one-to-many: Mumbai has many places)
    Destination -> Trip          (one-to-many: many trips go to Mumbai)

    Trip -> TripPlace -> TouristPlace   (many-to-many "through" table:
                                         a trip visits many places, and a
                                         place appears in many trips; the
                                         TripPlace row also stores the day)
    Trip -> TripCost             (one-to-one:  each trip has 1 cost breakdown)
    Transportation -> Trip       (one-to-many: many trips use "Car")
"""
from decimal import Decimal

from django.conf import settings

from . import languages
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# 1. Customer profile
# ---------------------------------------------------------------------------
class Profile(models.Model):
    """Extra information about a customer, on top of Django's built-in User."""

    # The one list of languages lives in travel/languages.py, so the profile
    # form, the chatbot's dropdown and the AI prompts can never disagree
    # about what the site speaks.
    LANGUAGE_CHOICES = languages.CHOICES

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=80, blank=True)
    preferred_language = models.CharField(
        max_length=5, choices=LANGUAGE_CHOICES, default="en"
    )
    avatar = models.ImageField(upload_to="uploads/avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


# ---------------------------------------------------------------------------
# 2. Destination (a city you can travel to)
# ---------------------------------------------------------------------------
class Theme(models.Model):
    """
    A way of travelling rather than a kind of place.

    "Temple" exists on TouristPlace already, but that answers "what is this
    building"; a theme answers "who is this trip for". Udaipur is historical by
    category and honeymoon by theme, and the explorer needs to filter on the
    second without redefining the first.

    A table rather than a column because a destination belongs to several -
    Goa is beach, family and weekend at once - and a many-to-many filters in
    SQL without the leading-comma tricks a packed CharField would need.
    """

    # A pilgrimage circuit is still a theme - it answers the same "who is this
    # trip for" question - but it belongs in its own row of chips. Kind keeps
    # both in one table and one relation instead of a second model and a
    # second many-to-many that would have to be joined separately.
    KIND_TRIP = "trip"
    KIND_PILGRIMAGE = "pilgrimage"
    KIND_CHOICES = [
        (KIND_TRIP, "Trip theme"),
        (KIND_PILGRIMAGE, "Pilgrimage circuit"),
    ]

    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_TRIP)
    # Lower sorts first, so the explorer's chips open on the broad themes
    # rather than alphabetically on "Adventure".
    display_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class Destination(models.Model):
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, default="India")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="uploads/destinations/", blank=True, null=True)
    # A plain CharField rather than a URLField, because the photographs now
    # live inside the project: the usual value is a path like
    # "/static/images/destinations/goa.jpg", which a URLField would reject in
    # the admin. A full web address still works if you paste one in.
    #
    # 500 characters, not the default 200: a Wikimedia Commons thumbnail URL
    # reaches 217 because the file name appears twice in the path. SQLite
    # ignores max_length, so a short field only fails once it reaches
    # Postgres, with "value too long for type character varying(200)".
    image_url = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Optional picture, used when no file is uploaded. Either a path "
            "like /static/images/destinations/goa.jpg or a full web address."
        ),
    )
    estimated_cost_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("2500.00"),
        help_text="SAMPLE estimate per person per day, in rupees.",
    )
    recommended_days = models.PositiveSmallIntegerField(default=3)
    is_popular = models.BooleanField(default=True)

    themes = models.ManyToManyField(
        Theme,
        blank=True,
        related_name="destinations",
        help_text="Who the trip suits: family, honeymoon, weekend and so on.",
    )
    best_time = models.CharField(
        max_length=90,
        blank=True,
        help_text="e.g. 'October to March'. Free text, shown on the card.",
    )
    sample_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=Decimal("4.0"),
        help_text=(
            "ILLUSTRATIVE score for the demo, in the same spirit as the sample "
            "prices. It is NOT an average of real visitor reviews, and the "
            "template labels it so - never present it as one."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.state}" if self.state else self.name

    @property
    def display_image(self):
        """Give the template one single place to ask for a picture."""
        if self.image:
            return self.image.url
        return self.image_url or ""


# ---------------------------------------------------------------------------
# 3. Tourist place (a spot inside a destination)
# ---------------------------------------------------------------------------
class TouristPlace(models.Model):
    CATEGORY_CHOICES = [
        ("beach", "Beach"),
        ("temple", "Temple"),
        ("historical", "Historical"),
        ("nature", "Nature"),
        ("shopping", "Shopping"),
        ("museum", "Museum"),
        ("adventure", "Adventure"),
        ("food", "Food"),
    ]

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="places"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="uploads/places/", blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True)  # see Destination
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="historical")
    opening_info = models.CharField(
        max_length=200, blank=True, help_text="e.g. 'Open 9 AM - 6 PM, closed Monday'"
    )
    entry_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="SAMPLE entry fee per person, in rupees.",
    )
    visit_duration_minutes = models.PositiveSmallIntegerField(
        default=90, help_text="Roughly how long a visit takes."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["destination__name", "name"]
        unique_together = [("destination", "name")]

    def __str__(self):
        return f"{self.name} ({self.destination.name})"

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


# ---------------------------------------------------------------------------
# 4. Transportation option
# ---------------------------------------------------------------------------
class Transportation(models.Model):
    """Car / Bike / Bus / Train and their SAMPLE rates."""

    code = models.SlugField(max_length=20, unique=True)  # car, bike, bus, train
    name = models.CharField(max_length=40)
    cost_per_km = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="SAMPLE rupees per kilometre."
    )
    average_speed_kmph = models.PositiveSmallIntegerField(default=50)
    seats_per_unit = models.PositiveSmallIntegerField(
        default=1,
        help_text="How many people share one vehicle (Car=4, Bike=2). "
        "Use 1 for per-person tickets like bus/train.",
    )
    charged_per_person = models.BooleanField(
        default=False, help_text="True for bus/train (ticket per person)."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Transportation options"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 5. Route distance (so admin can manage sample distances)
# ---------------------------------------------------------------------------
class RouteDistance(models.Model):
    """A SAMPLE distance between two cities. Admin can add more."""

    from_city = models.CharField(max_length=100)
    to_city = models.CharField(max_length=100)
    distance_km = models.PositiveIntegerField()

    class Meta:
        unique_together = [("from_city", "to_city")]
        ordering = ["from_city", "to_city"]

    def __str__(self):
        return f"{self.from_city} to {self.to_city}: {self.distance_km} km"


# ---------------------------------------------------------------------------
# 6. Trip (the plan a customer creates)
# ---------------------------------------------------------------------------
class Trip(models.Model):
    HOTEL_CHOICES = [
        ("budget", "Budget"),
        ("standard", "Standard"),
        ("deluxe", "Deluxe"),
        ("luxury", "Luxury"),
    ]
    FOOD_CHOICES = [
        ("budget", "Budget"),
        ("standard", "Standard"),
        ("premium", "Premium"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("saved", "Saved"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips"
    )
    title = models.CharField(max_length=140, blank=True)
    source = models.CharField(max_length=100, help_text="Starting city, e.g. Pune")
    destination = models.ForeignKey(
        Destination, on_delete=models.PROTECT, related_name="trips"
    )
    travel_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    travelers = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    days = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    transportation = models.ForeignKey(
        Transportation, on_delete=models.PROTECT, related_name="trips"
    )
    hotel_category = models.CharField(max_length=20, choices=HOTEL_CHOICES, default="standard")
    food_budget = models.CharField(max_length=20, choices=FOOD_CHOICES, default="standard")
    activity_budget = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    distance_km = models.PositiveIntegerField(default=0)
    travel_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    itinerary_text = models.TextField(blank=True, help_text="Generated day-by-day plan.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="saved")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # A trip visits many places; a place belongs to many trips.
    places = models.ManyToManyField(
        TouristPlace, through="TripPlace", related_name="trips", blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"{self.source} to {self.destination.name}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.source} to {self.destination.name}"
        super().save(*args, **kwargs)

    @property
    def nights(self):
        """3 days usually means 2 hotel nights."""
        return max(self.days - 1, 0)

    @property
    def is_upcoming(self):
        return self.travel_date >= timezone.localdate()


# ---------------------------------------------------------------------------
# 7. TripPlace (which place, on which day of which trip)
# ---------------------------------------------------------------------------
class TripPlace(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="trip_places")
    place = models.ForeignKey(TouristPlace, on_delete=models.CASCADE)
    day_number = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["day_number", "order"]
        unique_together = [("trip", "place")]

    def __str__(self):
        return f"Day {self.day_number}: {self.place.name}"


# ---------------------------------------------------------------------------
# 8. TripCost (the money breakdown for one trip)
# ---------------------------------------------------------------------------
class TripCost(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name="cost")
    travel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hotel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    local_transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activity_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cost for {self.trip} = Rs {self.total_cost}"

    # The order here is the order the dashboard draws, largest first in the
    # sample data. Slugs drive the bar colours in CSS.
    COMPONENTS = [
        ("travel", "Transport", "travel_cost"),
        ("hotel", "Hotels", "hotel_cost"),
        ("food", "Food", "food_cost"),
        ("local", "Local transport", "local_transport_cost"),
        ("activity", "Activities", "activity_cost"),
        # travel_service builds this as 8% of everything above, for shopping,
        # tips and anything unplanned. It is one line because it is calculated
        # as one number - splitting it into "shopping" and "emergency" on the
        # page would invent a division the figure does not have.
        ("buffer", "Shopping & buffer", "other_cost"),
    ]

    def breakdown(self):
        """
        Rows for the cost dashboard: label, amount and share of the total.

        Percentages are worked out here rather than in the template because
        Django templates cannot divide, and doing it in the view would mean
        repeating it for the trip page and the calculator both.
        """
        total = self.total_cost or 0
        rows = []
        for slug, label, field in self.COMPONENTS:
            amount = getattr(self, field) or Decimal("0")
            # Against a zero total every share is zero, not a division error.
            share = float(amount) / float(total) * 100 if total else 0.0
            rows.append(
                {
                    "slug": slug,
                    "label": label,
                    "amount": amount,
                    "percent": round(share, 1),
                }
            )
        return rows

    @property
    def per_person(self):
        """Total split across the party, or the whole total for a party of one."""
        travellers = self.trip.travelers or 1
        return (self.total_cost or Decimal("0")) / travellers

    @property
    def per_day(self):
        """What the trip averages a day - the number people compare against."""
        days = self.trip.days or 1
        return (self.total_cost or Decimal("0")) / days


# ---------------------------------------------------------------------------
# 9. ChatMessage (history of the AI assistant)
# ---------------------------------------------------------------------------
class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "Customer"),
        ("assistant", "AI Assistant"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    language = models.CharField(max_length=5, default="en")
    image = models.ForeignKey(
        "UploadedImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} [{self.role}]: {self.content[:40]}"


# ---------------------------------------------------------------------------
# 10. UploadedImage (photo the customer sends for recognition)
# ---------------------------------------------------------------------------
class UploadedImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_images"
    )
    image = models.ImageField(upload_to="uploads/recognition/")
    caption = models.CharField(max_length=200, blank=True)
    recognition_result = models.TextField(blank=True)
    is_confident = models.BooleanField(
        default=False, help_text="False means the AI was not sure about the place."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Image by {self.user.username} on {self.created_at:%Y-%m-%d}"
