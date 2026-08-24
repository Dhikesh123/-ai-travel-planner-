"""
Automated tests (Phase 15).

Run them with:   python manage.py test

Tests protect you: if you change the cost formula later and break something,
these will tell you immediately instead of a customer finding out.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import TripForm
from .models import (
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

    def test_every_indian_language_is_recognised_by_its_alphabet(self):
        """One real sentence per language, each in its own script."""
        samples = {
            "hi": "मुझे गोवा जाना है",
            "ta": "மதுரை எவ்வளவு தூரம்",
            "kn": "ಮೈಸೂರು ಎಷ್ಟು ದೂರ",
            "ml": "മൂന്നാർ എത്ര ദൂരം",
            "bn": "পুরী কত দূরে",
            "gu": "દ્વારકા કેટલું દૂર છે",
            "pa": "ਅੰਮ੍ਰਿਤਸਰ ਕਿੰਨੀ ਦੂਰ ਹੈ",
            "ur": "اجمیر کتنی دور ہے",
            "or": "ପୁରୀ କେତେ ଦୂର",
        }
        for code, sentence in samples.items():
            with self.subTest(language=code):
                self.assertEqual(detect_language(sentence), code)

    def test_marathi_is_reported_as_hindi(self):
        """
        Hindi and Marathi share the Devanagari alphabet, so no rule over the
        characters can separate them. This test records that deliberate
        choice rather than leaving it to be discovered as a bug.
        """
        self.assertEqual(detect_language("मला गोव्याला जायचे आहे"), "hi")

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
        self.assertEqual(languages.clean_code("HI"), "hi")
        self.assertEqual(languages.clean_code("en_US"), "en")

    def test_clean_code_refuses_anything_unknown(self):
        """A stray code must never reach the AI service or the database."""
        self.assertEqual(languages.clean_code("klingon"), "en")
        self.assertEqual(languages.clean_code(""), "en")
        self.assertEqual(languages.clean_code(None), "en")

    def test_profile_choices_come_from_the_list(self):
        self.assertEqual(len(Profile.LANGUAGE_CHOICES), len(languages.LANGUAGES))
        self.assertIn(("hi", "Hindi (हिन्दी)"), Profile.LANGUAGE_CHOICES)

    def test_the_browser_copy_carries_the_script_ranges(self):
        """speech.js builds its detection from these, so they must be there."""
        telugu = next(item for item in languages.as_dicts() if item["code"] == "te")
        self.assertEqual(telugu["speechCode"], "te-IN")
        self.assertTrue(telugu["scriptStart"] < telugu["scriptEnd"])
