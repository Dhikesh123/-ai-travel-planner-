"""
Serializers turn database objects into JSON (for the API) and back again.

Notice there is NO password field anywhere here - passwords never leave
the server.
"""
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    ChatMessage,
    Destination,
    TouristPlace,
    Transportation,
    Trip,
    TripCost,
    TripPlace,
    UploadedImage,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]
        read_only_fields = fields


class TouristPlaceSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="display_image", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = TouristPlace
        fields = [
            "id",
            "name",
            "description",
            "image",
            "category",
            "category_label",
            "opening_info",
            "entry_fee",
            "visit_duration_minutes",
            "destination",
            "destination_name",
        ]


class DestinationSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="display_image", read_only=True)
    place_count = serializers.IntegerField(source="places.count", read_only=True)

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "state",
            "country",
            "description",
            "image",
            "estimated_cost_per_day",
            "recommended_days",
            "is_popular",
            "place_count",
        ]


class DestinationDetailSerializer(DestinationSerializer):
    places = TouristPlaceSerializer(many=True, read_only=True)

    class Meta(DestinationSerializer.Meta):
        fields = DestinationSerializer.Meta.fields + ["places"]


class TransportationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportation
        fields = [
            "id",
            "code",
            "name",
            "cost_per_km",
            "average_speed_kmph",
            "seats_per_unit",
            "charged_per_person",
        ]


class TripCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripCost
        fields = [
            "travel_cost",
            "hotel_cost",
            "food_cost",
            "local_transport_cost",
            "activity_cost",
            "other_cost",
            "total_cost",
            "calculated_at",
        ]


class TripPlaceSerializer(serializers.ModelSerializer):
    place = TouristPlaceSerializer(read_only=True)

    class Meta:
        model = TripPlace
        fields = ["id", "place", "day_number", "order"]


class TripSerializer(serializers.ModelSerializer):
    """Used for reading a trip and for creating/updating one."""

    destination_name = serializers.CharField(source="destination.name", read_only=True)
    transportation_name = serializers.CharField(source="transportation.name", read_only=True)
    cost = TripCostSerializer(read_only=True)
    trip_places = TripPlaceSerializer(many=True, read_only=True)

    # Write-only: the list of tourist place ids the customer ticked
    place_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = Trip
        fields = [
            "id",
            "title",
            "source",
            "destination",
            "destination_name",
            "travel_date",
            "return_date",
            "travelers",
            "days",
            "transportation",
            "transportation_name",
            "hotel_category",
            "food_budget",
            "activity_budget",
            "distance_km",
            "travel_hours",
            "notes",
            "itinerary_text",
            "status",
            "created_at",
            "updated_at",
            "cost",
            "trip_places",
            "place_ids",
        ]
        read_only_fields = [
            "distance_km",
            "travel_hours",
            "itinerary_text",
            "created_at",
            "updated_at",
        ]

    def validate_travelers(self, value):
        if value < 1:
            raise serializers.ValidationError("There must be at least 1 traveller.")
        if value > 50:
            raise serializers.ValidationError("Maximum 50 travellers per trip.")
        return value

    def validate_days(self, value):
        if value < 1:
            raise serializers.ValidationError("A trip must be at least 1 day long.")
        if value > 60:
            raise serializers.ValidationError("Maximum 60 days per trip.")
        return value

    def validate(self, attrs):
        travel_date = attrs.get("travel_date")
        return_date = attrs.get("return_date")
        if travel_date and return_date and return_date < travel_date:
            raise serializers.ValidationError(
                {"return_date": "The return date must be on or after the travel date."}
            )
        return attrs


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "language", "created_at"]
        read_only_fields = fields


class UploadedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedImage
        fields = [
            "id",
            "image_url",
            "caption",
            "recognition_result",
            "is_confident",
            "created_at",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ""
