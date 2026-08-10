"""
The admin portal.

Django builds a full management screen for every model we register here.
Passwords are never shown - Django only ever stores a one-way hash.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ChatMessage,
    Destination,
    Profile,
    RouteDistance,
    TouristPlace,
    Transportation,
    Trip,
    TripCost,
    TripPlace,
    UploadedImage,
)

admin.site.site_header = "AI Travel Planner - Management Portal"
admin.site.site_title = "Travel Planner Admin"
admin.site.index_title = "Manage destinations, places, trips and customers"


class TouristPlaceInline(admin.TabularInline):
    model = TouristPlace
    extra = 1
    fields = ["name", "category", "entry_fee", "visit_duration_minutes"]


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ["name", "state", "country", "place_count", "estimated_cost_per_day",
                    "recommended_days", "is_popular"]
    list_filter = ["country", "state", "is_popular"]
    search_fields = ["name", "state", "description"]
    list_editable = ["is_popular", "estimated_cost_per_day"]
    inlines = [TouristPlaceInline]

    @admin.display(description="Places")
    def place_count(self, obj):
        return obj.places.count()


@admin.register(TouristPlace)
class TouristPlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "destination", "category", "entry_fee", "visit_duration_minutes"]
    list_filter = ["category", "destination"]
    search_fields = ["name", "description", "destination__name"]
    list_editable = ["category", "entry_fee"]
    autocomplete_fields = ["destination"]


@admin.register(Transportation)
class TransportationAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "cost_per_km", "average_speed_kmph",
                    "seats_per_unit", "charged_per_person", "is_active"]
    list_editable = ["cost_per_km", "average_speed_kmph", "is_active"]


@admin.register(RouteDistance)
class RouteDistanceAdmin(admin.ModelAdmin):
    list_display = ["from_city", "to_city", "distance_km"]
    search_fields = ["from_city", "to_city"]
    list_editable = ["distance_km"]


class TripPlaceInline(admin.TabularInline):
    model = TripPlace
    extra = 0
    autocomplete_fields = ["place"]


class TripCostInline(admin.StackedInline):
    model = TripCost
    extra = 0
    readonly_fields = ["calculated_at"]
    can_delete = False


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "destination", "travel_date", "travelers",
                    "days", "transportation", "total_cost", "status"]
    list_filter = ["status", "destination", "transportation", "hotel_category", "travel_date"]
    search_fields = ["title", "source", "user__username", "destination__name"]
    date_hierarchy = "travel_date"
    autocomplete_fields = ["destination"]
    readonly_fields = ["distance_km", "travel_hours", "itinerary_text",
                       "created_at", "updated_at"]
    inlines = [TripPlaceInline, TripCostInline]

    @admin.display(description="Estimated total")
    def total_cost(self, obj):
        cost = getattr(obj, "cost", None)
        return f"Rs {cost.total_cost:,.2f}" if cost else "-"


@admin.register(TripCost)
class TripCostAdmin(admin.ModelAdmin):
    list_display = ["trip", "travel_cost", "hotel_cost", "food_cost",
                    "local_transport_cost", "activity_cost", "other_cost", "total_cost"]
    search_fields = ["trip__title", "trip__user__username"]
    readonly_fields = ["calculated_at"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Customer profiles. No password information is shown here."""

    list_display = ["user", "email", "phone", "city", "preferred_language",
                    "trip_count", "created_at"]
    list_filter = ["preferred_language", "city"]
    search_fields = ["user__username", "user__email", "phone", "city"]
    readonly_fields = ["user", "created_at"]

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

    @admin.display(description="Trips")
    def trip_count(self, obj):
        return obj.user.trips.count()


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "short_content", "language", "created_at"]
    list_filter = ["role", "language", "created_at"]
    search_fields = ["content", "user__username"]
    readonly_fields = ["user", "role", "content", "language", "image", "created_at"]

    @admin.display(description="Message")
    def short_content(self, obj):
        return obj.content[:70] + ("..." if len(obj.content) > 70 else "")

    def has_add_permission(self, request):
        return False


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ["user", "preview", "caption", "is_confident", "created_at"]
    list_filter = ["is_confident", "created_at"]
    search_fields = ["caption", "recognition_result", "user__username"]
    readonly_fields = ["user", "image", "recognition_result", "is_confident",
                       "created_at", "preview"]

    @admin.display(description="Image")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:6px;" />', obj.image.url
            )
        return "-"

    def has_add_permission(self, request):
        return False
