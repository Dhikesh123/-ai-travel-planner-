"""
Forms = the rules for data coming from the browser.

Django checks every form before we touch the database, which stops bad or
dangerous data from getting in.
"""
import os

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Destination, Profile, Trip


class RegisterForm(UserCreationForm):
    """Sign-up form. Django hashes the password for us - we never store it."""

    email = forms.EmailField(required=True, help_text="We use this to identify your account.")
    first_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Lets a customer edit their own details."""

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = Profile
        fields = ["phone", "city", "preferred_language", "avatar"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not phone.replace("+", "").replace(" ", "").isdigit():
            raise forms.ValidationError("Phone number can only contain digits, spaces and +.")
        return phone

    def clean_avatar(self):
        return validate_image(self.cleaned_data.get("avatar"))

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        email = self.cleaned_data.get("email", "")
        if email:
            user.email = email
        if commit:
            user.save()
            profile.save()
        return profile


class TripForm(forms.ModelForm):
    """The main travel planner form."""

    class Meta:
        model = Trip
        fields = [
            "source",
            "destination",
            "travel_date",
            "return_date",
            "travelers",
            "days",
            "transportation",
            "hotel_category",
            "food_budget",
            "activity_budget",
            "notes",
        ]
        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"}),
            "return_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            # data-city-search turns the box into a combobox - see city_search.js
            "source": forms.TextInput(
                attrs={"placeholder": "e.g. Pune", "data-city-search": ""}
            ),
        }

    def clean_source(self):
        source = (self.cleaned_data.get("source") or "").strip()
        if len(source) < 2:
            raise forms.ValidationError("Please enter a valid starting city.")
        return source

    def clean_travelers(self):
        travelers = self.cleaned_data.get("travelers")
        if travelers is None or travelers < 1:
            raise forms.ValidationError("There must be at least 1 traveller.")
        if travelers > 50:
            raise forms.ValidationError("Please contact us directly for groups above 50.")
        return travelers

    def clean_days(self):
        days = self.cleaned_data.get("days")
        if days is None or days < 1:
            raise forms.ValidationError("A trip must be at least 1 day long.")
        if days > 60:
            raise forms.ValidationError("Please plan trips of 60 days or fewer.")
        return days

    def clean(self):
        """Checks that need more than one field at a time."""
        cleaned = super().clean()
        travel_date = cleaned.get("travel_date")
        return_date = cleaned.get("return_date")
        days = cleaned.get("days")

        if travel_date and travel_date < timezone.localdate():
            self.add_error("travel_date", "The travel date cannot be in the past.")

        if travel_date and return_date:
            if return_date < travel_date:
                self.add_error("return_date", "The return date must be on or after the travel date.")
            elif days:
                actual_days = (return_date - travel_date).days + 1
                if actual_days != days:
                    # Trust the dates and fix the day count for the customer
                    cleaned["days"] = actual_days

        source = (cleaned.get("source") or "").strip().lower()
        destination = cleaned.get("destination")
        if destination and source and source == destination.name.strip().lower():
            self.add_error("destination", "The starting city and destination cannot be the same.")

        return cleaned


class ImageUploadForm(forms.Form):
    """Upload a photo for AI recognition."""

    image = forms.ImageField()
    question = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Optional: What is this place and how can I visit it?"}
        ),
    )

    def clean_image(self):
        return validate_image(self.cleaned_data.get("image"), required=True)


def validate_image(uploaded, required=False):
    """
    Shared image checks:
      * file is actually there (when required)
      * file size is under the limit from settings
      * file extension is one we allow
    """
    if not uploaded:
        if required:
            raise forms.ValidationError("Please choose an image file.")
        return uploaded

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise forms.ValidationError(
            f"That image is too large. Please use a file under {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    extension = os.path.splitext(uploaded.name)[1].lower()
    if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)
        raise forms.ValidationError(f"Unsupported image type. Please use: {allowed}")

    return uploaded


class DestinationSearchForm(forms.Form):
    """The small search box on the destinations page."""

    q = forms.CharField(
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search destinations..."}),
    )
    category = forms.ChoiceField(required=False, choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import TouristPlace

        self.fields["category"].choices = [("", "All categories")] + list(
            TouristPlace.CATEGORY_CHOICES
        )
