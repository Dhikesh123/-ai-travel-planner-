"""
The JSON API. The JavaScript in the browser calls these URLs with fetch().

Every endpoint returns JSON, never HTML. Login is required except where
noted. The Groq API key is used only here on the server - it is never
sent to the browser.
"""
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.db import DatabaseError
from django.db.models import Count, Sum
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import languages
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

    # The session cookie above is enough for the Django site itself. A browser
    # on another domain cannot rely on it - see the authentication note in
    # settings - so a token goes back as well, for callers that need one.
    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {"ok": True, "user": UserSerializer(user).data, "token": token.key}
    )


@api_view(["POST"])
def api_logout(request):
    """POST /api/logout/  - end the session and invalidate the token."""
    # Dropping the token matters: signing out has to revoke the credential the
    # caller actually holds, and for the Vercel frontend that is the token,
    # not the cookie. Leaving it alive would keep the account reachable.
    Token.objects.filter(user=request.user).delete()
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def api_me(request):
    """GET /api/me/  - who is logged in right now."""
    return Response({"ok": True, "user": UserSerializer(request.user).data})


@api_view(["POST"])
@permission_classes([AllowAny])
def api_password_reset(request):
    """
    POST /api/password-reset/  - email a reset link. Body: {"email": "..."}

    This lets the portals on Vercel start a reset without sending the person
    off to the Django site first. The link in the mail still points at the
    Django site, because that is where the form that actually sets the new
    password lives - and it is a real server-rendered form with CSRF, which is
    the right place for it.

    The reply is deliberately the same whether or not the address belongs to an
    account. Saying "no such user" would turn this endpoint into a way to test
    which email addresses are registered, which is worth more to an attacker
    than the convenience is worth to anyone else.
    """
    email = str(request.data.get("email", "")).strip()
    if not email:
        return error("Enter the email address on your account.")

    form = PasswordResetForm(data={"email": email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            subject_template_name="password_reset_subject.txt",
            email_template_name="password_reset_email.html",
        )
    else:
        # A malformed address gets the same answer as a valid one, for the
        # reason above. It is logged so a typo is still diagnosable.
        logger.info("Password reset asked for with an unusable address.")

    return Response(
        {
            "ok": True,
            "message": (
                "If that address belongs to an account, a reset link is on its "
                "way. It is valid for 3 hours."
            ),
            # Tells the portal to warn that mail is not actually being sent, so
            # a demo deployment does not look like it silently swallowed it.
            "delivered_by_email": settings.EMAIL_IS_CONFIGURED,
        }
    )


# ===========================================================================
# Admin portal
# ===========================================================================
@api_view(["GET"])
def api_admin_stats(request):
    """
    GET /api/admin/stats/  - the numbers behind the admin portal.

    Staff only. A normal customer asking for this gets 403, not a redirect,
    because the caller is JavaScript and would not follow one.
    """
    if not request.user.is_staff:
        return error("You need a staff account to view this.", status.HTTP_403_FORBIDDEN)

    trips = Trip.objects.select_related("user", "destination", "cost")

    popular = (
        Destination.objects.annotate(trip_count=Count("trips"))
        .filter(trip_count__gt=0)
        .order_by("-trip_count")[:5]
    )

    return Response(
        {
            "ok": True,
            "totals": {
                "customers": User.objects.filter(is_staff=False).count(),
                "trips": trips.count(),
                "destinations": Destination.objects.count(),
                "places": TouristPlace.objects.count(),
                "chats": ChatMessage.objects.count(),
                "images": UploadedImage.objects.count(),
                "value": str(trips.aggregate(total=Sum("cost__total_cost"))["total"] or 0),
            },
            "popular_destinations": [
                {"id": d.id, "name": d.name, "trip_count": d.trip_count} for d in popular
            ],
            "recent_customers": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "date_joined": u.date_joined,
                }
                for u in User.objects.filter(is_staff=False).order_by("-date_joined")[:8]
            ],
            "recent_trips": [
                {
                    "id": t.id,
                    "title": t.title,
                    "username": t.user.username,
                    "destination": t.destination.name,
                    "travel_date": t.travel_date,
                    "travelers": t.travelers,
                    "days": t.days,
                    "total_cost": str(getattr(t.cost, "total_cost", "0")),
                }
                for t in trips.order_by("-created_at")[:10]
            ],
        }
    )


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

    history, trip_context, language = _chat_turn_context(request, message)

    try:
        reply = ai_service.chat(message, history=history, trip_context=trip_context)
    except ai_service.AIError as exc:
        return error(str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)

    ChatMessage.objects.create(
        user=request.user, role="assistant", content=reply, language=language
    )

    return Response({"ok": True, "reply": reply, "language": language})


def _chat_turn_context(request, message):
    """
    The work both chat endpoints do before the AI is asked anything: the trip
    being viewed, the recent conversation, and saving what the customer said.

    Returns (history, trip_context, language).
    """
    trip_context = ""
    trip_id = request.data.get("trip_id")
    if trip_id:
        trip = Trip.objects.filter(pk=trip_id, user=request.user).first()
        if trip:
            trip_context = trip_summary_text(trip)

    language = speech_service.detect_language(message)

    recent = ChatMessage.objects.filter(user=request.user).order_by("-created_at")[:10]
    history = [{"role": m.role, "content": m.content} for m in reversed(list(recent))]

    ChatMessage.objects.create(
        user=request.user, role="user", content=message, language=language
    )
    return history, trip_context, language


@api_view(["POST"])
def api_chat_stream(request):
    """
    POST /api/chat/stream/ - the same answer as /api/chat/, sent as it is
    written instead of all at once.

    The reply is a stream of server-sent events, one JSON object per event:

        data: {"delta": "Day 1: "}
        data: {"done": true}
        data: {"error": "..."}

    An itinerary takes the model a couple of seconds to write out. Holding it
    back until the final word is what made the assistant feel slow, so the
    words go to the page as they arrive. /api/chat/ stays as it is for
    anything that cannot read a stream.
    """
    message = (request.data.get("message") or "").strip()
    if not message:
        return error("Please type a message first.")
    if len(message) > 4000:
        return error("That message is too long. Please keep it under 4000 characters.")

    if not ai_service.is_configured():
        return error(ai_service.NO_KEY_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    history, trip_context, language = _chat_turn_context(request, message)
    user = request.user

    def events():
        def event(payload):
            return "data: " + json.dumps(payload) + "\n\n"

        pieces = []
        try:
            for piece in ai_service.chat_stream(
                message, history=history, trip_context=trip_context
            ):
                pieces.append(piece)
                yield event({"delta": piece})
        except ai_service.AIError as exc:
            yield event({"error": str(exc)})
            return
        except Exception:  # noqa: BLE001 - the browser must hear something
            logger.exception("Chat stream failed")
            yield event({"error": "The assistant could not finish that answer. Please try again."})
            return

        reply = "".join(pieces).strip()
        if not reply:
            yield event({"error": "The AI service sent an empty reply. Please try again."})
            return

        # Only a finished answer is worth remembering.
        ChatMessage.objects.create(
            user=user, role="assistant", content=reply, language=language
        )
        yield event({"done": True})

    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    # Tells nginx and friends not to hold the pieces back until the end, which
    # would undo the whole point of streaming.
    response["X-Accel-Buffering"] = "no"
    return response


@api_view(["GET", "DELETE"])
def api_chat_history(request):
    """GET /api/chat/history/ - past messages. DELETE - clear them."""
    if request.method == "DELETE":
        ChatMessage.objects.filter(user=request.user).delete()
        return Response({"ok": True, "message": "Chat history cleared."})

    messages_qs = ChatMessage.objects.filter(user=request.user).order_by("created_at")
    return Response({"ok": True, "results": ChatMessageSerializer(messages_qs, many=True).data})


# ===========================================================================
# Translation (between any two supported languages)
# ===========================================================================
@api_view(["POST"])
def api_translate(request):
    """
    POST /api/translate/
    Body: text, source (any supported code, or "auto"), target
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
    if not languages.is_supported(source) or not languages.is_supported(target):
        return error(
            "That language is not supported. Choose one of: "
            + ", ".join(language.name for language in languages.LANGUAGES)
            + "."
        )

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

    # An empty language means "let Whisper work it out", which is a fair
    # answer when the customer has not said what they are about to speak.
    language = request.data.get("language") or None
    if language and not languages.is_supported(languages.clean_code(language, default="")):
        return error(
            "That language is not supported. Choose one of: "
            + ", ".join(item.name for item in languages.LANGUAGES)
            + "."
        )
    language = languages.clean_code(language, default="") or None

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
