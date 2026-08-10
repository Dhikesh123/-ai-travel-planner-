from django.apps import AppConfig


class TravelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "travel"
    verbose_name = "Travel Planner"

    def ready(self):
        # Import signals so a Profile is auto-created for every new user
        from . import signals  # noqa: F401
