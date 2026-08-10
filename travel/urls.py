"""
Every web address in the app, and the view that answers it.
"""
from django.urls import path

from . import api_views, views

urlpatterns = [
    # ---------------- Public pages ----------------
    path("", views.home, name="home"),
    path("destinations/", views.destination_list, name="destination_list"),
    path("destinations/<int:pk>/", views.destination_detail, name="destination_detail"),
    # ---------------- Accounts --------------------
    path("register/", views.register, name="register"),
    path("login/", views.CustomerLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    # ---------------- Customer portal -------------
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("planner/", views.planner, name="planner"),
    path("calculator/", views.calculator, name="calculator"),
    path("trips/", views.trip_list, name="trip_list"),
    path("trips/<int:pk>/", views.trip_detail, name="trip_detail"),
    path("trips/<int:pk>/edit/", views.trip_edit, name="trip_edit"),
    path("trips/<int:pk>/delete/", views.trip_delete, name="trip_delete"),
    path("assistant/", views.chatbot, name="chatbot"),
    path("image-recognition/", views.image_recognition, name="image_recognition"),
    path("voice/", views.voice_assistant, name="voice_assistant"),
    # ---------------- Admin portal ----------------
    path("manage/", views.admin_dashboard, name="admin_dashboard"),
    # ================ JSON API ====================
    path("api/register/", api_views.api_register, name="api_register"),
    path("api/login/", api_views.api_login, name="api_login"),
    path("api/logout/", api_views.api_logout, name="api_logout"),
    path("api/me/", api_views.api_me, name="api_me"),
    path("api/destinations/", api_views.api_destinations, name="api_destinations"),
    path(
        "api/destinations/<int:pk>/",
        api_views.api_destination_detail,
        name="api_destination_detail",
    ),
    path("api/transportation/", api_views.api_transportation, name="api_transportation"),
    path("api/trips/", api_views.api_trips, name="api_trips"),
    path("api/trips/<int:pk>/", api_views.api_trip_detail, name="api_trip_detail"),
    path(
        "api/trips/<int:pk>/suggestions/",
        api_views.api_trip_suggestions,
        name="api_trip_suggestions",
    ),
    path("api/calculate-cost/", api_views.api_calculate_cost, name="api_calculate_cost"),
    path("api/chat/", api_views.api_chat, name="api_chat"),
    path("api/chat/history/", api_views.api_chat_history, name="api_chat_history"),
    path("api/translate/", api_views.api_translate, name="api_translate"),
    path(
        "api/image-recognition/",
        api_views.api_image_recognition,
        name="api_image_recognition",
    ),
    path("api/transcribe/", api_views.api_transcribe, name="api_transcribe"),
]
