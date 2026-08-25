"""
Automated tests (Phase 15).

Run them with:   python manage.py test

Tests protect you: if you change the cost formula later and break something,
these will tell you immediately instead of a customer finding out.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
import json

from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import TripForm
from .models import (
    CityLocation,
    Destination,
    Profile,
    RouteDistance,
    TouristPlace,
    Transportation,
    Trip,
    TripCost,
)
from . import languages
from .services import travel_service
from .services.speech_service import detect_language
from .services import geo_service
from .utils import recalculate_trip


class BaseData(TestCase):
    """Shared sample data for all the tests below."""

    def setUp(self):
        self.user = User.objects.create_user(username="asha", password="TestPass!234")

        self.mumbai = Destination.objects.create(
            name="Mumbai", state="Maharashtra", estimated_cost_per_day=Decimal("3000")
        )
        self.gateway = TouristPlace.objects.create(
            destination=self.mumbai, name="Gateway of India",
            category="historical", entry_fee=Decimal("0"),
        )
        self.elephanta = TouristPlace.objects.create(
            destination=self.mumbai, name="Elephanta Caves",
            category="historical", entry_fee=Decimal("40"),
        )
        self.car = Transportation.objects.create(
            code="car", name="Car", cost_per_km=Decimal("12.00"),
            average_speed_kmph=55, seats_per_unit=4, charged_per_person=False,
        )
        self.train = Transportation.objects.create(
            code="train", name="Train", cost_per_km=Decimal("1.20"),
            average_speed_kmph=65, seats_per_unit=1, charged_per_person=True,
        )
        RouteDistance.objects.create(from_city="Pune", to_city="Mumbai", distance_km=150)


class ProfileSignalTests(BaseData):
    def test_profile_is_created_automatically(self):
        """Every new user must get a Profile without us doing anything."""
        self.assertTrue(Profile.objects.filter(user=self.user).exists())


class DistanceTests(BaseData):
    def test_known_route_from_database(self):
        distance, known = travel_service.estimate_distance("Pune", "Mumbai")
        self.assertEqual(distance, 150)
        self.assertTrue(known)

    def test_route_works_in_reverse(self):
        distance, known = travel_service.estimate_distance("Mumbai", "Pune")
        self.assertEqual(distance, 150)
        self.assertTrue(known)

    def test_unknown_route_uses_default_and_says_so(self):
        distance, known = travel_service.estimate_distance("Nowhere", "Elsewhere")
        self.assertEqual(distance, travel_service.DEFAULT_DISTANCE_KM)
        self.assertFalse(known)

    def test_same_city_is_zero(self):
        distance, known = travel_service.estimate_distance("Pune", "Pune")
        self.assertEqual(distance, 0)


class CostCalculatorTests(BaseData):
    def test_pune_to_mumbai_car_two_people_three_days(self):
        """The demo trip from the project brief."""
        costs = travel_service.calculate_costs(
            distance_km=150, travelers=2, days=3, transportation=self.car,
            hotel_category="standard", food_budget="standard",
            activity_budget=Decimal("0"), places=[self.gateway, self.elephanta],
        )
        # Travel: 150 km x 2 (round trip) x Rs 12 x 1 car = 3600
        self.assertEqual(costs["travel_cost"], Decimal("3600.00"))
        # Hotel: 1 room x 2 nights x Rs 2200 = 4400
        self.assertEqual(costs["hotel_cost"], Decimal("4400.00"))
        # Food: 2 people x 3 days x Rs 650 = 3900
        self.assertEqual(costs["food_cost"], Decimal("3900.00"))
        # Local transport: 1 group x 3 days x Rs 500 = 1500
        self.assertEqual(costs["local_transport_cost"], Decimal("1500.00"))
        # Activities: Rs 40 entry x 2 people = 80
        self.assertEqual(costs["activity_cost"], Decimal("80.00"))
        # Total must equal the sum of all the parts
        parts = (
            costs["travel_cost"] + costs["hotel_cost"] + costs["food_cost"]
            + costs["local_transport_cost"] + costs["activity_cost"] + costs["other_cost"]
        )
        self.assertEqual(costs["total_cost"], parts)

    def test_more_travellers_costs_more(self):
        small = travel_service.calculate_costs(
            distance_km=150, travelers=2, days=3, transportation=self.car,
        )
        large = travel_service.calculate_costs(
            distance_km=150, travelers=6, days=3, transportation=self.car,
        )
        self.assertGreater(large["total_cost"], small["total_cost"])

    def test_car_needs_two_vehicles_for_six_people(self):
        costs = travel_service.calculate_costs(
            distance_km=100, travelers=6, days=2, transportation=self.car,
        )
        # 6 people / 4 seats = 2 cars
        self.assertEqual(costs["details"]["vehicles_or_tickets"], 2)

    def test_train_charges_each_person(self):
        costs = travel_service.calculate_costs(
            distance_km=100, travelers=3, days=2, transportation=self.train,
        )
        # 100 x 2 x 1.20 x 3 people = 720
        self.assertEqual(costs["travel_cost"], Decimal("720.00"))
        self.assertEqual(costs["details"]["vehicles_or_tickets"], 3)

    def test_luxury_hotel_costs_more_than_budget(self):
        budget = travel_service.calculate_costs(
            distance_km=100, travelers=2, days=3, transportation=self.car,
            hotel_category="budget",
        )
        luxury = travel_service.calculate_costs(
            distance_km=100, travelers=2, days=3, transportation=self.car,
            hotel_category="luxury",
        )
        self.assertGreater(luxury["hotel_cost"], budget["hotel_cost"])

    def test_one_day_trip_has_no_hotel_cost(self):
        costs = travel_service.calculate_costs(
            distance_km=100, travelers=2, days=1, transportation=self.car,
        )
        self.assertEqual(costs["hotel_cost"], Decimal("0.00"))


class ItineraryTests(BaseData):
    def test_itinerary_has_one_entry_per_day(self):
        itinerary = travel_service.build_itinerary(
            source="Pune", destination_name="Mumbai", days=3,
            places=[self.gateway, self.elephanta],
        )
        self.assertEqual(len(itinerary), 3)
        self.assertEqual(itinerary[0]["day"], 1)

    def test_first_day_includes_the_outward_journey(self):
        itinerary = travel_service.build_itinerary(
            source="Pune", destination_name="Mumbai", days=2, places=[self.gateway],
        )
        self.assertIn("Travel Pune to Mumbai", itinerary[0]["items"][0])

    def test_last_day_includes_the_return_journey(self):
        itinerary = travel_service.build_itinerary(
            source="Pune", destination_name="Mumbai", days=3, places=[self.gateway],
        )
        self.assertIn("Return journey", " ".join(itinerary[-1]["items"]))

    def test_return_journey_is_always_the_last_item(self):
        """Even on a day with no sightseeing, the journey home comes last."""
        itinerary = travel_service.build_itinerary(
            source="Pune", destination_name="Mumbai", days=3,
            places=[self.gateway, self.elephanta],
        )
        self.assertIn("Return journey", itinerary[-1]["items"][-1])

    def test_every_selected_place_appears_somewhere(self):
        places = [self.gateway, self.elephanta]
        itinerary = travel_service.build_itinerary(
            source="Pune", destination_name="Mumbai", days=3, places=places,
        )
        text = " ".join(item for day in itinerary for item in day["items"])
        for place in places:
            self.assertIn(place.name, text)


class TripFormTests(BaseData):
    def base_payload(self, **overrides):
        payload = {
            "source": "Pune",
            "destination": self.mumbai.pk,
            "travel_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
            "return_date": "",
            "travelers": 2,
            "days": 3,
            "transportation": self.car.pk,
            "hotel_category": "standard",
            "food_budget": "standard",
            "activity_budget": "0",
            "notes": "",
        }
        payload.update(overrides)
        return payload

    def test_valid_form_is_accepted(self):
        self.assertTrue(TripForm(data=self.base_payload()).is_valid())

    def test_past_travel_date_is_rejected(self):
        form = TripForm(data=self.base_payload(
            travel_date=(timezone.localdate() - timedelta(days=1)).isoformat()
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("travel_date", form.errors)

    def test_zero_travellers_is_rejected(self):
        form = TripForm(data=self.base_payload(travelers=0))
        self.assertFalse(form.is_valid())
        self.assertIn("travelers", form.errors)

    def test_return_date_before_travel_date_is_rejected(self):
        form = TripForm(data=self.base_payload(
            travel_date=(timezone.localdate() + timedelta(days=10)).isoformat(),
            return_date=(timezone.localdate() + timedelta(days=5)).isoformat(),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("return_date", form.errors)

    def test_same_source_and_destination_is_rejected(self):
        form = TripForm(data=self.base_payload(source="Mumbai"))
        self.assertFalse(form.is_valid())

    def test_empty_source_is_rejected(self):
        form = TripForm(data=self.base_payload(source=""))
        self.assertFalse(form.is_valid())


class TripSavingTests(BaseData):
    def test_recalculate_trip_creates_cost_and_itinerary(self):
        trip = Trip.objects.create(
            user=self.user, source="Pune", destination=self.mumbai,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=2, days=3, transportation=self.car,
        )
        recalculate_trip(trip, [self.gateway.pk, self.elephanta.pk])
        trip.refresh_from_db()

        self.assertEqual(trip.distance_km, 150)
        self.assertTrue(trip.itinerary_text)
        self.assertTrue(TripCost.objects.filter(trip=trip).exists())
        self.assertEqual(trip.trip_places.count(), 2)

    def test_recalculating_replaces_the_old_place_list(self):
        trip = Trip.objects.create(
            user=self.user, source="Pune", destination=self.mumbai,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=2, days=3, transportation=self.car,
        )
        recalculate_trip(trip, [self.gateway.pk, self.elephanta.pk])
        recalculate_trip(trip, [self.gateway.pk])
        self.assertEqual(trip.trip_places.count(), 1)


class SecurityTests(BaseData):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_planner_requires_login(self):
        response = self.client.get(reverse("planner"))
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_blocks_normal_customers(self):
        self.client.login(username="asha", password="TestPass!234")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertNotEqual(response.status_code, 200)

    def test_admin_dashboard_allows_staff(self):
        User.objects.create_user(
            username="boss", password="TestPass!234", is_staff=True
        )
        self.client.login(username="boss", password="TestPass!234")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_a_customer_cannot_open_another_customers_trip(self):
        other = User.objects.create_user(username="ravi", password="TestPass!234")
        trip = Trip.objects.create(
            user=other, source="Pune", destination=self.mumbai,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=1, days=2, transportation=self.car,
        )
        self.client.login(username="asha", password="TestPass!234")
        response = self.client.get(reverse("trip_detail", args=[trip.pk]))
        self.assertEqual(response.status_code, 404)

    def test_password_is_stored_hashed_not_in_plain_text(self):
        self.assertNotEqual(self.user.password, "TestPass!234")
        self.assertTrue(self.user.check_password("TestPass!234"))


class PublicPageTests(BaseData):
    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_destination_list_loads(self):
        response = self.client.get(reverse("destination_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mumbai")

    def test_destination_search_filters_results(self):
        Destination.objects.create(name="Goa", state="Goa")
        response = self.client.get(reverse("destination_list"), {"q": "Goa"})
        self.assertContains(response, "Goa")
        self.assertNotContains(response, "Maharashtra")

    def test_register_page_loads(self):
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)


class ApiTests(BaseData):
    def test_calculate_cost_returns_a_breakdown(self):
        response = self.client.post(
            reverse("api_calculate_cost"),
            {
                "source": "Pune",
                "destination_id": self.mumbai.pk,
                "travelers": 2,
                "days": 3,
                "transportation_id": self.car.pk,
                "hotel_category": "standard",
                "food_budget": "standard",
                "activity_budget": "0",
                "place_ids": [self.gateway.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["distance_km"], 150)
        self.assertIn("total_cost", data["costs"])
        self.assertEqual(len(data["itinerary"]), 3)
        self.assertIn("ESTIMATES", data["disclaimer"].upper())

    def test_calculate_cost_rejects_bad_traveller_count(self):
        response = self.client.post(
            reverse("api_calculate_cost"),
            {
                "source": "Pune",
                "destination_id": self.mumbai.pk,
                "travelers": 0,
                "days": 3,
                "transportation_id": self.car.pk,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_calculate_cost_rejects_missing_destination(self):
        response = self.client.post(
            reverse("api_calculate_cost"),
            {"source": "Pune", "destination_id": 9999, "travelers": 2,
             "days": 3, "transportation_id": self.car.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_destinations_api_is_public(self):
        response = self.client.get(reverse("api_destinations"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_trips_api_requires_login(self):
        response = self.client.get(reverse("api_trips"))
        self.assertIn(response.status_code, (401, 403))

    def test_trip_create_read_update_delete(self):
        self.client.login(username="asha", password="TestPass!234")
        travel_date = (timezone.localdate() + timedelta(days=9)).isoformat()

        # CREATE
        created = self.client.post(
            reverse("api_trips"),
            {
                "source": "Pune", "destination": self.mumbai.pk,
                "travel_date": travel_date, "travelers": 2, "days": 3,
                "transportation": self.car.pk, "hotel_category": "standard",
                "food_budget": "standard", "activity_budget": "0",
                "place_ids": [self.gateway.pk, self.elephanta.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        trip_id = created.json()["trip"]["id"]

        # READ
        read = self.client.get(reverse("api_trip_detail", args=[trip_id]))
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["trip"]["distance_km"], 150)
        self.assertIsNotNone(read.json()["trip"]["cost"])

        # UPDATE
        updated = self.client.patch(
            reverse("api_trip_detail", args=[trip_id]),
            {"travelers": 4},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["trip"]["travelers"], 4)

        # DELETE
        deleted = self.client.delete(reverse("api_trip_detail", args=[trip_id]))
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Trip.objects.filter(pk=trip_id).exists())

    def test_chat_without_api_key_gives_a_clear_message(self):
        """With no API key set, the API must explain that, not crash."""
        self.client.login(username="asha", password="TestPass!234")
        with self.settings(GROQ_API_KEY=""):
            response = self.client.post(
                reverse("api_chat"), {"message": "Plan a trip"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ok"])

    def test_chat_rejects_an_empty_message(self):
        self.client.login(username="asha", password="TestPass!234")
        response = self.client.post(
            reverse("api_chat"), {"message": "   "}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_translate_same_language_returns_the_text_unchanged(self):
        self.client.login(username="asha", password="TestPass!234")
        response = self.client.post(
            reverse("api_translate"),
            {"text": "Hello", "source": "en", "target": "en"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["translation"], "Hello")

    def test_register_through_the_api(self):
        response = self.client.post(
            reverse("api_register"),
            {
                "username": "newcustomer", "email": "new@example.com",
                "password1": "StrongPass!987", "password2": "StrongPass!987",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="newcustomer").exists())

    def test_login_with_the_wrong_password_fails(self):
        response = self.client.post(
            reverse("api_login"),
            {"username": "asha", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


class AIFeatureTests(BaseData):
    """
    Checks around the AI features that do NOT need a real API key.

    We never call Groq in the tests: real API calls would be slow, cost money
    and fail without internet. Instead we check that our own validation and
    our "no key" handling behave correctly.
    """

    def setUp(self):
        super().setUp()
        self.client.login(username="asha", password="TestPass!234")

    @staticmethod
    def tiny_image_bytes():
        """Make a small real JPEG in memory, so ImageField validation passes."""
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), (120, 160, 200)).save(buffer, format="JPEG")
        return buffer.getvalue()

    # --- configuration -----------------------------------------------------
    def test_all_three_ai_models_are_configured(self):
        """A typo in a model setting should not go unnoticed."""
        from django.conf import settings

        self.assertTrue(settings.GROQ_CHAT_MODEL)
        self.assertTrue(settings.GROQ_VISION_MODEL)
        self.assertTrue(settings.GROQ_WHISPER_MODEL)

    # --- speech to text ----------------------------------------------------
    def test_transcribe_needs_an_audio_file(self):
        response = self.client.post(reverse("api_transcribe"), {})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_transcribe_rejects_an_unsupported_language(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        audio = SimpleUploadedFile("clip.webm", b"fake audio", content_type="audio/webm")
        response = self.client.post(
            reverse("api_transcribe"), {"audio": audio, "language": "fr"}
        )
        self.assertEqual(response.status_code, 400)

    def test_transcribe_without_api_key_explains_itself(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        audio = SimpleUploadedFile("clip.webm", b"fake audio", content_type="audio/webm")
        with self.settings(GROQ_API_KEY=""):
            response = self.client.post(
                reverse("api_transcribe"), {"audio": audio, "language": "en"}
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("GROQ_API_KEY", response.json()["error"])

    # --- image recognition -------------------------------------------------
    def test_image_recognition_needs_an_image(self):
        response = self.client.post(reverse("api_image_recognition"), {})
        self.assertEqual(response.status_code, 400)

    def test_image_recognition_without_api_key_explains_itself(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "photo.jpg", self.tiny_image_bytes(), content_type="image/jpeg"
        )
        with self.settings(GROQ_API_KEY=""):
            response = self.client.post(reverse("api_image_recognition"), {"image": image})
        self.assertEqual(response.status_code, 503)

    def test_image_recognition_rejects_a_non_image_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile("virus.exe", b"not an image", content_type="image/jpeg")
        response = self.client.post(reverse("api_image_recognition"), {"image": fake})
        self.assertEqual(response.status_code, 400)

    # --- translation -------------------------------------------------------
    def test_translate_without_api_key_explains_itself(self):
        with self.settings(GROQ_API_KEY=""):
            response = self.client.post(
                reverse("api_translate"),
                {"text": "Hello", "source": "en", "target": "te"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 503)

    def test_translate_rejects_an_unsupported_language(self):
        response = self.client.post(
            reverse("api_translate"),
            {"text": "Hello", "source": "en", "target": "fr"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_translate_rejects_empty_text(self):
        response = self.client.post(
            reverse("api_translate"),
            {"text": "   ", "source": "en", "target": "te"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # --- AI endpoints all require login ------------------------------------
    def test_ai_endpoints_require_login(self):
        self.client.logout()
        for name in ["api_chat", "api_translate", "api_image_recognition", "api_transcribe"]:
            with self.subTest(endpoint=name):
                response = self.client.post(reverse(name), {})
                self.assertIn(response.status_code, (401, 403))


class ReasoningStripTests(TestCase):
    """
    The vision model 'thinks out loud' inside <think> tags before answering.
    The customer must only ever see the final answer.
    """

    def test_think_block_is_removed(self):
        from .services.ai_service import _strip_reasoning

        raw = "<think>Let me look at the picture carefully.</think>CONFIDENCE: HIGH\nPLACE: Gateway of India"
        cleaned = _strip_reasoning(raw)
        self.assertNotIn("<think>", cleaned)
        self.assertNotIn("look at the picture", cleaned)
        self.assertTrue(cleaned.startswith("CONFIDENCE: HIGH"))

    def test_unclosed_think_block_is_removed(self):
        from .services.ai_service import _strip_reasoning

        cleaned = _strip_reasoning("Answer here.<think>ran out of room mid-thought")
        self.assertNotIn("<think>", cleaned)
        self.assertEqual(cleaned, "Answer here.")

    def test_plain_text_is_left_alone(self):
        from .services.ai_service import _strip_reasoning

        self.assertEqual(_strip_reasoning("Just a normal answer."), "Just a normal answer.")

    def test_empty_input_is_safe(self):
        from .services.ai_service import _strip_reasoning

        self.assertEqual(_strip_reasoning(""), "")
        self.assertEqual(_strip_reasoning(None), "")


class LanguageDetectionTests(TestCase):
    def test_telugu_text_is_detected(self):
        self.assertEqual(detect_language("నేను ముంబైకి వెళ్లాలి"), "te")

    def test_english_text_is_detected(self):
        self.assertEqual(detect_language("I want to go to Mumbai"), "en")

    def test_empty_text_defaults_to_english(self):
        self.assertEqual(detect_language(""), "en")

    def test_another_indian_script_reads_as_english(self):
        """
        The site offers English and Telugu. Anything written in a third
        alphabet is not one of them, and English is the honest answer - it
        is the voice that will read the sentence back least badly.

        This is worth a test rather than a shrug: detection drives which
        voice speaks a reply aloud, and it should never claim a language the
        site does not have.
        """
        for sentence in (
            "मुझे गोवा जाना है",           # Hindi
            "மதுரை எவ்வளவு தூரம்",   # Tamil
            "ಮೈಸೂರು ಎಷ್ಟು ದೂರ",         # Kannada
        ):
            with self.subTest(sentence=sentence[:12]):
                self.assertEqual(detect_language(sentence), "en")

    def test_telugu_in_latin_letters_reads_as_english(self):
        """"ela unnaru" is Telugu, but an English voice reads it sensibly."""
        self.assertEqual(detect_language("Hyderabad ela vellali"), "en")

    def test_a_place_name_in_english_does_not_change_the_answer(self):
        """Mixed text is judged by which alphabet has the most letters."""
        self.assertEqual(detect_language("Goa కి ఎలా వెళ్ళాలి"), "te")


class LanguageListTests(TestCase):
    """The one list every part of the site reads its languages from."""

    def test_english_is_the_default_and_comes_first(self):
        self.assertEqual(languages.DEFAULT_CODE, "en")
        self.assertEqual(languages.LANGUAGES[0].code, "en")

    def test_codes_are_unique(self):
        codes = [language.code for language in languages.LANGUAGES]
        self.assertEqual(len(codes), len(set(codes)))

    def test_every_language_has_a_speech_code_and_a_label(self):
        for language in languages.LANGUAGES:
            with self.subTest(language=language.code):
                self.assertTrue(language.speech_code)
                self.assertTrue(language.label)

    def test_clean_code_accepts_what_a_browser_sends(self):
        self.assertEqual(languages.clean_code("te-IN"), "te")
        self.assertEqual(languages.clean_code("TE"), "te")
        self.assertEqual(languages.clean_code("en_US"), "en")

    def test_a_language_the_site_dropped_is_not_accepted(self):
        """
        The site offered eleven Indian languages for a while. A stale code in
        a bookmark or an old session must not slip back through.
        """
        self.assertEqual(languages.clean_code("hi"), "en")
        self.assertFalse(languages.is_supported("ta"))

    def test_clean_code_refuses_anything_unknown(self):
        """A stray code must never reach the AI service or the database."""
        self.assertEqual(languages.clean_code("klingon"), "en")
        self.assertEqual(languages.clean_code(""), "en")
        self.assertEqual(languages.clean_code(None), "en")

    def test_profile_choices_come_from_the_list(self):
        self.assertEqual(len(Profile.LANGUAGE_CHOICES), len(languages.LANGUAGES))
        self.assertIn(("en", "English"), Profile.LANGUAGE_CHOICES)
        self.assertIn(("te", "Telugu (తెలుగు)"), Profile.LANGUAGE_CHOICES)

    def test_the_browser_copy_carries_the_script_ranges(self):
        """speech.js builds its detection from these, so they must be there."""
        telugu = next(item for item in languages.as_dicts() if item["code"] == "te")
        self.assertEqual(telugu["speechCode"], "te-IN")
        self.assertTrue(telugu["scriptStart"] < telugu["scriptEnd"])

class JourneyGeographyTests(TestCase):
    """
    What the planner offers depends on where the two ends of the trip are.

    Every test here works from coordinates written into the database, and
    seeds the location cache for the starting town, so nothing reaches
    OpenStreetMap. A test suite that needs the internet is a test suite that
    fails on a train.
    """

    def setUp(self):
        # A roughly south-to-north line up the east of India, which is the
        # shape of the journey this was built for.
        self.bhimavaram = (16.48181, 81.53294)
        CityLocation.objects.create(
            name="bhimavaram", latitude=self.bhimavaram[0], longitude=self.bhimavaram[1]
        )

        def place(name, state, lat, lon):
            destination = Destination.objects.create(
                name=name, state=state, latitude=lat, longitude=lon
            )
            TouristPlace.objects.create(
                destination=destination, name=name + " temple", category="temple"
            )
            return destination

        self.ayodhya = place("Ayodhya", "Uttar Pradesh", 26.79907, 82.20523)
        self.vijayawada = place("Vijayawada", "Andhra Pradesh", 16.51153, 80.61605)
        self.varanasi = place("Varanasi", "Uttar Pradesh", 25.33565, 83.00763)
        self.goa = place("Goa", "Goa", 15.35000, 74.00000)

    # -- the maths ------------------------------------------------------
    def test_distance_between_two_points(self):
        """Bhimavaram to Ayodhya is a shade over 1,100 km as the crow flies."""
        km = geo_service.distance_km(
            self.bhimavaram, (self.ayodhya.latitude, self.ayodhya.longitude)
        )
        self.assertAlmostEqual(km, 1149, delta=25)

    def test_distance_to_itself_is_zero(self):
        self.assertAlmostEqual(
            geo_service.distance_km(self.bhimavaram, self.bhimavaram), 0, places=5
        )

    def test_distance_needs_both_ends(self):
        self.assertIsNone(geo_service.distance_km(self.bhimavaram, None))
        self.assertIsNone(geo_service.distance_km(None, None))

    def test_a_town_on_the_line_is_on_the_way(self):
        end = (self.ayodhya.latitude, self.ayodhya.longitude)
        here = (self.varanasi.latitude, self.varanasi.longitude)
        self.assertTrue(geo_service.is_on_the_way(self.bhimavaram, here, end))

    def test_a_town_in_the_wrong_direction_is_not(self):
        """Goa is west; Ayodhya is north. Nobody drives one to reach the other."""
        end = (self.ayodhya.latitude, self.ayodhya.longitude)
        here = (self.goa.latitude, self.goa.longitude)
        self.assertFalse(geo_service.is_on_the_way(self.bhimavaram, here, end))

    # -- the grouping ---------------------------------------------------
    def test_the_journey_is_split_into_three_groups(self):
        groups = geo_service.journey_groups("Bhimavaram", self.ayodhya)
        headings = [heading for heading, _, _ in groups]
        self.assertEqual(
            headings,
            ["Near your starting point", "On the way", "In and around Ayodhya"],
        )

    def test_a_town_beside_the_start_is_grouped_with_it(self):
        groups = dict((heading, rows) for heading, _, rows in
                      geo_service.journey_groups("Bhimavaram", self.ayodhya))
        self.assertIn(self.vijayawada, groups["Near your starting point"])

    def test_a_town_along_the_road_is_grouped_as_such(self):
        groups = dict((heading, rows) for heading, _, rows in
                      geo_service.journey_groups("Bhimavaram", self.ayodhya))
        self.assertIn(self.varanasi, groups["On the way"])

    def test_the_destination_leads_its_own_group(self):
        groups = geo_service.journey_groups("Bhimavaram", self.ayodhya)
        _, _, last = groups[-1]
        self.assertEqual(last[0], self.ayodhya)

    def test_somewhere_in_the_wrong_direction_is_offered_at_all(self):
        """Goa belongs to no group on this journey."""
        offered = [
            destination
            for _, _, rows in geo_service.journey_groups("Bhimavaram", self.ayodhya)
            for destination in rows
        ]
        self.assertNotIn(self.goa, offered)

    def test_an_unplaceable_start_still_gives_the_destination(self):
        """
        A town OpenStreetMap could not find is remembered as a failure, and
        the planner falls back to the far end rather than showing nothing.
        """
        CityLocation.objects.create(name="nowhere-at-all", latitude=None, longitude=None)
        groups = geo_service.journey_groups("Nowhere-At-All", self.ayodhya)
        self.assertEqual([heading for heading, _, _ in groups],
                         ["In and around Ayodhya"])

    def test_no_destination_means_no_groups(self):
        self.assertEqual(geo_service.journey_groups("Bhimavaram", None), [])

    # -- the cache ------------------------------------------------------
    def test_a_known_destination_is_located_without_asking_anyone(self):
        # Compared as floats: the column is a DecimalField, so what comes back
        # from the database is a Decimal even though a float went in.
        latitude, longitude = geo_service.locate("varanasi")
        self.assertAlmostEqual(float(latitude), 25.33565, places=5)
        self.assertAlmostEqual(float(longitude), 83.00763, places=5)

    def test_a_remembered_failure_is_not_looked_up_again(self):
        CityLocation.objects.create(name="qqqq", latitude=None, longitude=None)
        self.assertIsNone(geo_service.locate("QQQQ"))

    def test_an_empty_name_is_not_looked_up(self):
        self.assertIsNone(geo_service.locate(""))
        self.assertIsNone(geo_service.locate(None))


class JourneyPlacesApiTests(TestCase):
    """The endpoint the planner calls whenever either address changes."""

    def setUp(self):
        self.client = Client()
        CityLocation.objects.create(name="bhimavaram", latitude=16.48181, longitude=81.53294)
        self.ayodhya = Destination.objects.create(
            name="Ayodhya", state="Uttar Pradesh", latitude=26.79907, longitude=82.20523
        )
        TouristPlace.objects.create(
            destination=self.ayodhya, name="Ram Mandir", category="temple"
        )
        self.vijayawada = Destination.objects.create(
            name="Vijayawada", state="Andhra Pradesh", latitude=16.51153, longitude=80.61605
        )
        TouristPlace.objects.create(
            destination=self.vijayawada, name="Kanaka Durga Temple", category="temple"
        )

    def test_it_returns_the_groups_for_a_journey(self):
        response = self.client.get(
            "/api/journey-places/",
            {"source": "Bhimavaram", "destination": self.ayodhya.pk},
        )
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["source_located"])
        headings = [group["heading"] for group in body["groups"]]
        self.assertIn("Near your starting point", headings)
        self.assertIn("In and around Ayodhya", headings)

    def test_it_says_when_the_starting_town_could_not_be_placed(self):
        CityLocation.objects.create(name="zzzz", latitude=None, longitude=None)
        body = self.client.get(
            "/api/journey-places/", {"source": "Zzzz", "destination": self.ayodhya.pk}
        ).json()
        self.assertFalse(body["source_located"])
        self.assertEqual([g["heading"] for g in body["groups"]], ["In and around Ayodhya"])

    def test_it_needs_a_destination(self):
        body = self.client.get("/api/journey-places/", {"source": "Bhimavaram"}).json()
        self.assertFalse(body["ok"])

    def test_it_refuses_a_destination_that_does_not_exist(self):
        response = self.client.get(
            "/api/journey-places/", {"source": "Bhimavaram", "destination": 99999}
        )
        self.assertEqual(response.status_code, 404)


class PlannerPageTests(TestCase):
    """What the page itself paints before any JavaScript runs."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="ravi", password="TestPass!234")
        self.client.force_login(self.user)
        CityLocation.objects.create(name="bhimavaram", latitude=16.48181, longitude=81.53294)

        self.ayodhya = Destination.objects.create(
            name="Ayodhya", state="Uttar Pradesh", latitude=26.79907, longitude=82.20523
        )
        TouristPlace.objects.create(destination=self.ayodhya, name="Ram Mandir", category="temple")

        self.vijayawada = Destination.objects.create(
            name="Vijayawada", state="Andhra Pradesh", latitude=16.51153, longitude=80.61605
        )
        TouristPlace.objects.create(
            destination=self.vijayawada, name="Kanaka Durga Temple", category="temple"
        )
        # somewhere with no business being on this journey
        self.goa = Destination.objects.create(
            name="Goa", state="Goa", latitude=15.35, longitude=74.0
        )
        TouristPlace.objects.create(destination=self.goa, name="Baga Beach", category="beach")

        Transportation.objects.create(
            code="car", name="Car", cost_per_km=Decimal("12.00"),
            average_speed_kmph=55, seats_per_unit=4, charged_per_person=False,
        )

    def test_the_page_offers_only_places_along_the_journey(self):
        html = self.client.get(
            "/planner/", {"source": "Bhimavaram", "destination": self.ayodhya.pk}
        ).content.decode()
        self.assertIn("Ram Mandir", html)          # the destination
        self.assertIn("Kanaka Durga Temple", html)  # beside the start
        self.assertNotIn("Baga Beach", html)        # the wrong way entirely

    def test_without_a_destination_it_offers_nothing_yet(self):
        html = self.client.get("/planner/").content.decode()
        self.assertNotIn("Ram Mandir", html)
        self.assertNotIn("Baga Beach", html)


class MeasuredDistanceTests(TestCase):
    """
    When neither rate table knows a city pair, the distance is measured from
    the map instead of falling back to a flat guess.

    Bhimavaram to Ayodhya is nobody's sample route. Before this it came back
    as 250 km, and every rupee on the trip page was built on that.
    """

    def setUp(self):
        CityLocation.objects.create(
            name="bhimavaram", latitude=16.48181, longitude=81.53294
        )
        Destination.objects.create(
            name="Ayodhya", state="Uttar Pradesh", latitude=26.79907, longitude=82.20523
        )

    def test_an_unlisted_pair_is_measured_from_the_map(self):
        km, known = travel_service.estimate_distance("Bhimavaram", "Ayodhya")
        self.assertTrue(known)
        # ~1,149 km as the crow flies, plus the allowance for roads winding
        self.assertAlmostEqual(km, 1436, delta=60)

    def test_the_rate_table_still_wins(self):
        """A distance somebody entered by hand beats one worked out here."""
        RouteDistance.objects.create(
            from_city="Bhimavaram", to_city="Ayodhya", distance_km=1600
        )
        km, known = travel_service.estimate_distance("Bhimavaram", "Ayodhya")
        self.assertEqual(km, 1600)
        self.assertTrue(known)

    def test_a_pair_that_cannot_be_placed_still_falls_back(self):
        CityLocation.objects.create(name="nowhere at all", latitude=None, longitude=None)
        km, known = travel_service.estimate_distance("Nowhere At All", "Ayodhya")
        self.assertEqual(km, travel_service.DEFAULT_DISTANCE_KM)
        self.assertFalse(known)


class ChoiceComparisonTests(BaseData):
    """The trip page prices every other option, and says which it would pick."""

    def setUp(self):
        super().setUp()
        self.bus = Transportation.objects.create(
            code="bus", name="Bus", cost_per_km=Decimal("1.80"),
            average_speed_kmph=45, seats_per_unit=1, charged_per_person=True,
        )
        self.flight = Transportation.objects.create(
            code="flight", name="Flight", cost_per_km=Decimal("7.00"),
            average_speed_kmph=300, seats_per_unit=1, charged_per_person=True,
        )

    def _transport(self, distance_km=1450, travelers=2, days=5):
        return travel_service.compare_transport(
            distance_km=distance_km, travelers=travelers, days=days, chosen=self.car
        )

    def test_every_option_is_priced(self):
        names = {row["name"] for row in self._transport()}
        self.assertEqual(names, {"Car", "Train", "Bus", "Flight"})

    def test_the_list_runs_cheapest_first(self):
        totals = [row["total"] for row in self._transport()]
        self.assertEqual(totals, sorted(totals))

    def test_the_cheapest_and_the_fastest_are_labelled(self):
        rows = self._transport()
        cheapest = min(rows, key=lambda row: row["total"])
        fastest = min(rows, key=lambda row: row["hours"])
        self.assertIn("Cheapest", cheapest["labels"])
        self.assertIn("Fastest", fastest["labels"])

    def test_exactly_one_option_is_recommended(self):
        self.assertEqual(sum(1 for row in self._transport() if row["is_recommended"]), 1)

    def test_a_long_haul_does_not_recommend_paying_for_speed(self):
        """
        Flying saves seventeen hours over the train and costs thousands more
        per hour saved. The train stays the recommendation.
        """
        recommended = next(row for row in self._transport() if row["is_recommended"])
        self.assertEqual(recommended["name"], "Train")

    def test_the_chosen_option_is_marked_and_differences_are_from_it(self):
        rows = self._transport()
        chosen = next(row for row in rows if row["is_chosen"])
        self.assertEqual(chosen["name"], "Car")
        self.assertIn("Your choice", chosen["labels"])
        self.assertEqual(chosen["difference"], Decimal("0.00"))
        for row in rows:
            self.assertEqual(row["difference"], row["total"] - chosen["total"])

    # -- rooms ----------------------------------------------------------
    def _rooms(self, benchmark, distance_km=1450, travelers=2, days=5):
        return travel_service.compare_rooms(
            distance_km=distance_km, travelers=travelers, days=days,
            transportation=self.car, chosen_category="standard",
            benchmark_per_day=benchmark,
        )

    def test_all_four_room_classes_are_priced(self):
        rows = self._rooms(Decimal("3000"))
        self.assertEqual([row["label"] for row in rows],
                         ["Budget", "Standard", "Deluxe", "Luxury"])

    def test_a_generous_benchmark_buys_a_better_room(self):
        """The recommendation is the best class that still fits inside it."""
        rows = self._rooms(Decimal("100000"))
        self.assertEqual(next(r for r in rows if r["is_recommended"])["label"], "Luxury")

    def test_a_tight_benchmark_falls_back_to_the_cheapest(self):
        rows = self._rooms(Decimal("1"))
        self.assertEqual(next(r for r in rows if r["is_recommended"])["label"], "Budget")

    def test_the_room_figure_leaves_the_journey_out(self):
        """
        The per-day figure is about being there, so a longer journey must not
        change it - otherwise it is judged against a benchmark that was never
        about travel.
        """
        near = self._rooms(Decimal("3000"), distance_km=100)
        far = self._rooms(Decimal("3000"), distance_km=2000)
        self.assertEqual(
            [row["per_person_per_day"] for row in near],
            [row["per_person_per_day"] for row in far],
        )


class CitySearchTests(TestCase):
    """What the "From" box offers as somebody types."""

    def setUp(self):
        self.client = Client()
        # a destination the site sells
        Destination.objects.create(
            name="Vijayawada", state="Andhra Pradesh",
            latitude=16.51153, longitude=80.61605,
        )
        # towns that are only starting points
        CityLocation.objects.create(
            name="bhimavaram", display_name="Bhimavaram, Andhra Pradesh",
            latitude=16.48181, longitude=81.53294,
        )
        CityLocation.objects.create(
            name="tadepalligudem", display_name="Tadepalligudem, Andhra Pradesh",
            latitude=16.81, longitude=81.52,
        )
        # one we failed to place, which must never be suggested
        CityLocation.objects.create(name="nowhere", display_name="", latitude=None)

    def search(self, query):
        return self.client.get("/api/city-search/", {"q": query}).json()["results"]

    def test_it_finds_a_town_from_the_first_few_letters(self):
        labels = [row["label"] for row in self.search("bhim")]
        self.assertIn("Bhimavaram, Andhra Pradesh", labels)

    def test_a_destination_is_marked_as_one(self):
        rows = self.search("vij")
        self.assertEqual(rows[0]["name"], "Vijayawada")
        self.assertEqual(rows[0]["kind"], "destination")

    def test_destinations_come_before_other_towns(self):
        CityLocation.objects.create(
            name="vijayapura", display_name="Vijayapura, Karnataka",
            latitude=16.83, longitude=75.71,
        )
        self.assertEqual(self.search("vij")[0]["name"], "Vijayawada")

    def test_it_also_matches_inside_a_name(self):
        """"gudem" should still find Tadepalligudem."""
        labels = [row["label"] for row in self.search("gudem")]
        self.assertIn("Tadepalligudem, Andhra Pradesh", labels)

    def test_a_town_we_could_not_place_is_never_offered(self):
        self.assertEqual(self.search("nowhere"), [])

    def test_one_letter_is_not_a_search(self):
        """Too little to go on, and it would match half of India."""
        self.assertEqual(self.search("b"), [])

    def test_nothing_matching_is_an_empty_list_not_an_error(self):
        response = self.client.get("/api/city-search/", {"q": "zzzzzz"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["results"], [])

    def test_the_same_place_is_never_listed_twice(self):
        """A destination that is also in the city table appears once."""
        CityLocation.objects.create(
            name="vijayawada", display_name="Vijayawada, Andhra Pradesh",
            latitude=16.51153, longitude=80.61605,
        )
        names = [row["name"].lower() for row in self.search("vijayawada")]
        self.assertEqual(len(names), len(set(names)))


class TidyPlaceNameTests(TestCase):
    """OpenStreetMap returns the whole administrative chain; a dropdown cannot."""

    def test_the_town_and_its_state_survive(self):
        self.assertEqual(
            geo_service._tidy_name("Bhimavaram, West Godavari, Andhra Pradesh, India"),
            "Bhimavaram, Andhra Pradesh",
        )

    def test_a_postcode_is_dropped(self):
        self.assertEqual(
            geo_service._tidy_name("Ayodhya, Faizabad, Ayodhya, Uttar Pradesh, 224123, India"),
            "Ayodhya, Uttar Pradesh",
        )

    def test_a_short_name_is_left_alone(self):
        self.assertEqual(geo_service._tidy_name("Goa, India"), "Goa")
        self.assertEqual(geo_service._tidy_name("Delhi"), "Delhi")

    def test_nothing_in_nothing_out(self):
        self.assertEqual(geo_service._tidy_name(""), "")
        self.assertEqual(geo_service._tidy_name(None), "")

class ReadAloudTests(TestCase):
    """
    The server speaks when the browser cannot.

    Windows ships no Telugu voice, so on most machines in India the browser
    can only apologise. These tests cover the fallback that replaced the
    apology - with the speech service stubbed out, because a test suite
    should not need the internet.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="meena", password="TestPass!234")
        self.client.force_login(self.user)

    def speak(self, **body):
        return self.client.post(
            "/api/speak/", data=json.dumps(body), content_type="application/json"
        )

    def test_it_returns_audio(self):
        with patch("travel.services.speech_service.synthesize", return_value=b"ID3-pretend-mp3"):
            response = self.speak(text="తిరుపతి", language="te")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response.content, b"ID3-pretend-mp3")

    def test_the_language_reaches_the_speech_service(self):
        with patch("travel.services.speech_service.synthesize", return_value=b"x") as spoken:
            self.speak(text="hello", language="te")
        self.assertEqual(spoken.call_args.args[1], "te")

    def test_an_unsupported_language_becomes_english(self):
        """A stale code must not reach the speech service as-is."""
        with patch("travel.services.speech_service.synthesize", return_value=b"x") as spoken:
            self.speak(text="hello", language="hi")
        self.assertEqual(spoken.call_args.args[1], "en")

    def test_empty_text_is_refused(self):
        response = self.speak(text="   ", language="te")
        self.assertEqual(response.status_code, 400)

    def test_a_speech_failure_is_explained_not_crashed(self):
        from travel.services.ai_service import AIError

        with patch("travel.services.speech_service.synthesize",
                   side_effect=AIError("The speech service could not be reached.")):
            response = self.speak(text="hello", language="te")
        self.assertEqual(response.status_code, 503)
        self.assertIn("could not be reached", response.json()["error"])

    def test_it_needs_a_login(self):
        response = Client().post(
            "/api/speak/", data=json.dumps({"text": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class VoiceChoiceTests(TestCase):
    """Every language the site offers must have a voice to say it in."""

    def test_each_language_has_a_voice(self):
        from travel.services import speech_service

        for language in languages.LANGUAGES:
            with self.subTest(language=language.code):
                self.assertIn(language.code, speech_service.VOICES)

    def test_very_long_text_is_cut_short(self):
        """Nobody gets to use this as a free audiobook service."""
        from travel.services import speech_service

        captured = {}

        class FakeCommunicate:
            def __init__(self, text, voice):
                captured["length"] = len(text)

            async def stream(self):
                yield {"type": "audio", "data": b"x"}

        with patch.dict("sys.modules", {"edge_tts": MagicMock(Communicate=FakeCommunicate)}):
            speech_service.synthesize("a" * 9000, "en")
        self.assertEqual(captured["length"], speech_service.MAX_SPOKEN_CHARACTERS)
