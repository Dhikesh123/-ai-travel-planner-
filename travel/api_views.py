"""
The JSON API. The JavaScript in the browser calls these URLs with fetch().

Every endpoint returns JSON, never HTML. Login is required except where
noted. The Groq API key is used only here on the server - it is never
sent to the browser.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .forms import ImageUploadForm, RegisterForm
from .models import (
    ChatMessage,
    Destination,
    TouristPlace,
    Transportation,
    Trip,
    UploadedImage,
)
from .serializers import (
    ChatMessageSerializer,
    DestinationDetailSerializer,
    DestinationSerializer,
    TransportationSerializer,
    TripSerializer,
    UploadedImageSerializer,
    UserSerializer,
)
from .services import ai_service, speech_service, travel_service
from .utils import recalculate_trip, trip_summary_text

logger = logging.getLogger(__name__)


def error(message, code=status.HTTP_400_BAD_REQUEST):
    """One consistent error shape for the whole API."""
    return Response({"ok": False, "error": message}, status=code)


# ===========================================================================
# Accounts
# ===========================================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def api_register(request):
    """POST /api/register/  - create a new customer account."""
    form = RegisterForm(request.data)
    if not form.is_valid():
        return Response(
            {"ok": False, "errors": form.errors}, status=status.HTTP_400_BAD_REQUEST
        )
    user = form.save()
    login(request, user)
    return Response(
        {"ok": True, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    """POST /api/login/  - sign in and start a session."""
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return error("Please enter both username and password.")

    user = authenticate(request, username=username, password=password)
    if user is None:
        return error("Wrong username or password.", status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response({"ok": True, "user": UserSerializer(user).data})


@api_view(["POST"])
def api_logout(request):
    """POST /api/logout/  - end the session."""
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def api_me(request):
    """GET /api/me/  - who is logged in right now."""
    return Response({"ok": True, "user": UserSerializer(request.user).data})


# ===========================================================================
# Destinations and places (readable without login)
# ===========================================================================
@api_view(["GET"])
@permission_classes([AllowAny])
def api_destinations(request):
    """GET /api/destinations/  - list, with optional ?q= search."""
    query = (request.GET.get("q") or "").strip()
    destinations = Destination.objects.all()
    if query:
        destinations = destinations.filter(name__icontains=query)
    return Response(
        {"ok": True, "results": DestinationSerializer(destinations, many=True).data}
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_destination_detail(request, pk):
    """GET /api/destinations/<id>/  - one destination plus its tourist places."""
    try:
        destination = Destination.objects.prefetch_related("places").get(pk=pk)
    except Destination.DoesNotExist:
        return error("That destination does not exist.", status.HTTP_404_NOT_FOUND)
    return Response({"ok": True, "destination": DestinationDetailSerializer(destination).data})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_transportation(request):
    """GET /api/transportation/  - the car/bike/bus/train options and rates."""
    options = Transportation.objects.filter(is_active=True)
    return Response({"ok": True, "results": TransportationSerializer(options, many=True).data})


# ===========================================================================
# Trips (full create / read / update / delete)
# ===========================================================================
@api_view(["GET", "POST"])
def api_trips(request):
    """
    GET  /api/trips/  - list my saved trips
    POST /api/trips/  - create a new trip (and calculate cost + itinerary)
    """
    if request.method == "GET":
        trips = Trip.objects.filter(user=request.user).select_related(
            "destination", "transportation", "cost"
        )
        return Response({"ok": True, "results": TripSerializer(trips, many=True).data})

    serializer = TripSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    place_ids = serializer.validated_data.pop("place_ids", [])
    try:
        trip = serializer.save(user=request.user)
        recalculate_trip(trip, place_ids)
    except DatabaseError as exc:
        logger.exception("Could not save trip")
        return error("Could not save the trip. Please try again.", status.HTTP_500_INTERNAL_SERVER_ERROR)

    trip.refresh_from_db()
    return Response(
        {"ok": True, "trip": TripSerializer(trip).data}, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def api_trip_detail(request, pk):
    """
    GET    /api/trips/<id>/  - read one trip
    PUT    /api/trips/<id>/  - update it
    DELETE /api/trips/<id>/  - delete it
    """
    try:
        trip = Trip.objects.select_related("destination", "transportation", "cost").get(
            pk=pk, user=request.user
        )
    except Trip.DoesNotExist:
        return error("Trip not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({"ok": True, "trip": TripSerializer(trip).data})

    if request.method == "DELETE":
        trip.delete()
        return Response({"ok": True, "message": "Trip deleted."})

    partial = request.method == "PATCH"
    serializer = TripSerializer(trip, data=request.data, partial=partial)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    place_ids = serializer.validated_data.pop("place_ids", None)
    trip = serializer.save()
    recalculate_trip(trip, place_ids)
    trip.refresh_from_db()
    return Response({"ok": True, "trip": TripSerializer(trip).data})


# ===========================================================================
# Live cost calculator
# ===========================================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def api_calculate_cost(request):
    """
    POST /api/calculate-cost/

    Body: source, destination_id, travelers, days, transportation_id,
          hotel_category, food_budget, activity_budget, place_ids[]

    Returns the full cost breakdown AND the day-by-day itinerary, without
    saving anything. This is what makes the calculator update live.
    """
    data = request.data

    # --- read and check every input ---------------------------------------
    # Careful: "or 1" would turn a real 0 into 1 and hide the mistake, so we
    # only fall back to the default when the value is genuinely missing.
    raw_travelers = data.get("travelers", 1)
    raw_days = data.get("days", 1)
    if raw_travelers in (None, ""):
        raw_travelers = 1
    if raw_days in (None, ""):
        raw_days = 1

    try:
        travelers = int(raw_travelers)
        days = int(raw_days)
    except (TypeError, ValueError):
        return error("Travellers and days must be whole numbers.")

    if travelers < 1 or travelers > 50:
        return error("Number of travellers must be between 1 and 50.")
    if days < 1 or days > 60:
        return error("Number of days must be between 1 and 60.")

    try:
        activity_budget = Decimal(str(data.get("activity_budget") or "0"))
        if activity_budget < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return error("Activity budget must be a positive number.")

    destination_id = data.get("destination_id")
    try:
        destination = Destination.objects.get(pk=destination_id)
    except (Destination.DoesNotExist, ValueError, TypeError):
        return error("Please choose a valid destination.")

    transportation_id = data.get("transportation_id")
    try:
        transportation = Transportation.objects.get(pk=transportation_id, is_active=True)
    except (Transportation.DoesNotExist, ValueError, TypeError):
        return error("Please choose a valid transportation option.")

    source = (data.get("source") or "").strip()
    if len(source) < 2:
        return error("Please enter your starting city.")

    place_ids = data.get("place_ids") or []
    if isinstance(place_ids, str):
        place_ids = [p for p in place_ids.split(",") if p.strip().isdigit()]
    places = list(TouristPlace.objects.filter(id__in=place_ids, destination=destination))

    # --- do the maths -----------------------------------------------------
    distance_km, distance_known = travel_service.estimate_distance(source, destination.name)
    travel_hours = travel_service.estimate_travel_hours(distance_km, transportation)

    costs = travel_service.calculate_costs(
        distance_km=distance_km,
        travelers=travelers,
        days=days,
        transportation=transportation,
        hotel_category=data.get("hotel_category") or "standard",
        food_budget=data.get("food_budget") or "standard",
        activity_budget=activity_budget,
        places=places,
    )

    itinerary = travel_service.build_itinerary(
        source=source,
        destination_name=destination.name,
        days=days,
        places=places,
        travelers=travelers,
        transport_name=transportation.name,
    )

    return Response(
        {
            "ok": True,
            "distance_km": distance_km,
            "distance_is_known": distance_known,
            "travel_hours": str(travel_hours),
            "costs": {k: str(v) for k, v in costs.items() if k != "details"},
            "details": {k: str(v) for k, v in costs["details"].items()},
            "itinerary": itinerary,
            "disclaimer": (
                "All prices, distances and travel times shown are DEMONSTRATION "
                "ESTIMATES calculated from sample rates. They are not live "
                "market prices or live availability."
            ),
        }
    )


# ===========================================================================
# AI chat
# ===========================================================================
@api_view(["POST"])
def api_chat(request):
    """
    POST /api/chat/
    Body: message, trip_id (optional), language (optional)
    """
    message = (request.data.get("message") or "").strip()
    if not message:
        return error("Please type a message first.")
    if len(message) > 4000:
        return error("That message is too long. Please keep it under 4000 characters.")

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    # Optional: give the AI the trip the customer is looking at
    trip_context = ""
    trip_id = request.data.get("trip_id")
    if trip_id:
        trip = Trip.objects.filter(pk=trip_id, user=request.user).first()
        if trip:
            trip_context = trip_summary_text(trip)

    language = speech_service.detect_language(message)

    # Recent conversation so the AI remembers the topic
    recent = ChatMessage.objects.filter(user=request.user).order_by("-created_at")[:10]
    history = [{"role": m.role, "content": m.content} for m in reversed(list(recent))]

    ChatMessage.objects.create(
        user=request.user, role="user", content=message, language=language
    )

    try:
        reply = ai_service.chat(message, history=history, trip_context=trip_context)
    except ai_service.AIError as exc:
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    ChatMessage.objects.create(
        user=request.user, role="assistant", content=reply, language=language
    )

    return Response({"ok": True, "reply": reply, "language": language})


@api_view(["GET", "DELETE"])
def api_chat_history(request):
    """GET /api/chat/history/ - past messages. DELETE - clear them."""
    if request.method == "DELETE":
        ChatMessage.objects.filter(user=request.user).delete()
        return Response({"ok": True, "message": "Chat history cleared."})

    messages_qs = ChatMessage.objects.filter(user=request.user).order_by("created_at")
    return Response({"ok": True, "results": ChatMessageSerializer(messages_qs, many=True).data})


# ===========================================================================
# Translation (Telugu <-> English)
# ===========================================================================
@api_view(["POST"])
def api_translate(request):
    """
    POST /api/translate/
    Body: text, source (te/en), target (te/en)
    """
    text = (request.data.get("text") or "").strip()
    if not text:
        return error("Please enter some text to translate.")
    if len(text) > 4000:
        return error("That text is too long. Please keep it under 4000 characters.")

    source = request.data.get("source") or "auto"
    target = request.data.get("target") or "en"

    if source == "auto":
        source = speech_service.detect_language(text)
    if source not in ("te", "en") or target not in ("te", "en"):
        return error("Only Telugu and English are supported right now.")

    if source == target:
        return Response({"ok": True, "translation": text, "source": source, "target": target})

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        translation = ai_service.translate(text, source_lang=source, target_lang=target)
    except ai_service.AIError as exc:
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(
        {"ok": True, "translation": translation, "source": source, "target": target}
    )


# ===========================================================================
# Image recognition
# ===========================================================================
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def api_image_recognition(request):
    """
    POST /api/image-recognition/  (multipart form with an "image" file)
    """
    form = ImageUploadForm(request.POST or request.data, request.FILES)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return error(first_error)

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    upload = form.cleaned_data["image"]
    question = form.cleaned_data.get("question", "")

    # Work out the correct media type for the API call
    media_type = getattr(upload, "content_type", "") or "image/jpeg"
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/jpeg"

    upload.seek(0)
    image_bytes = upload.read()
    upload.seek(0)

    record = UploadedImage.objects.create(
        user=request.user, image=upload, caption=question
    )

    try:
        text, is_confident = ai_service.analyse_image(
            image_bytes, media_type=media_type, question=question
        )
    except ai_service.AIError as exc:
        record.recognition_result = f"Failed: {exc}"
        record.save(update_fields=["recognition_result"])
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    record.recognition_result = text
    record.is_confident = is_confident
    record.save(update_fields=["recognition_result", "is_confident"])

    # Keep the picture in the chat history too, so the assistant remembers it
    ChatMessage.objects.create(
        user=request.user,
        role="assistant",
        content=text,
        image=record,
    )

    return Response(
        {
            "ok": True,
            "result": text,
            "is_confident": is_confident,
            "upload": UploadedImageSerializer(record).data,
            "note": (
                "" if is_confident else
                "The AI was NOT confident about this image. Treat the answer as a guess."
            ),
        }
    )


# ===========================================================================
# Speech to text (Whisper, on the server)
# ===========================================================================
MAX_AUDIO_MB = 20


@api_view(["POST"])
def api_transcribe(request):
    """
    POST /api/transcribe/  (multipart form with an "audio" file)

    Most browsers turn speech into text themselves, which is instant and
    free. This endpoint is the backup for browsers that cannot (Safari,
    Firefox, some phones): the recording is sent here and Whisper writes it
    out as text.
    """
    audio = request.FILES.get("audio")
    if not audio:
        return error("No audio file was sent.")

    if audio.size > MAX_AUDIO_MB * 1024 * 1024:
        return error(f"That recording is too long. Please keep it under {MAX_AUDIO_MB} MB.")

    language = request.data.get("language") or None
    if language not in (None, "", "en", "te"):
        return error("Only Telugu and English are supported right now.")

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        text = speech_service.transcribe_audio(
            audio.read(),
            language=language or None,
            filename=getattr(audio, "name", "recording.webm"),
        )
    except ai_service.AIError as exc:
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"ok": True, "text": text, "language": speech_service.detect_language(text)})


# ===========================================================================
# AI itinerary suggestions for a saved trip
# ===========================================================================
@api_view(["POST"])
def api_trip_suggestions(request, pk):
    """POST /api/trips/<id>/suggestions/ - ask the AI to review a saved trip."""
    try:
        trip = Trip.objects.select_related("destination", "transportation", "cost").get(
            pk=pk, user=request.user
        )
    except Trip.DoesNotExist:
        return error("Trip not found.", status.HTTP_404_NOT_FOUND)

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        suggestion = ai_service.suggest_itinerary(trip_summary_text(trip))
    except ai_service.AIError as exc:
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"ok": True, "suggestion": suggestion})
