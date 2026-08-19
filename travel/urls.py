"""
Every web address in the app, and the view that answers it.
"""
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

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
    # ---------------- Forgot password -------------
    # Django's own four-step flow: ask for the address, confirm it was sent,
    # follow the emailed link, confirm the new password took. Both portals use
    # these same pages - a customer and a staff member reset a password the
    # same way, because they are the same kind of account underneath.
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset.html",
            email_template_name="password_reset_email.html",
            subject_template_name="password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset_sent.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
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
    path(
        "api/password-reset/",
        api_views.api_password_reset,
        name="api_password_reset",
    ),
    path("api/admin/stats/", api_views.api_admin_stats, name="api_admin_stats"),
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
    path("api/chat/stream/", api_views.api_chat_stream, name="api_chat_stream"),
    path("api/chat/history/", api_views.api_chat_history, name="api_chat_history"),
    path("api/translate/", api_views.api_translate, name="api_translate"),
    path(
        "api/image-recognition/",
        api_views.api_image_recognition,
        name="api_image_recognition",
    ),
    path("api/transcribe/", api_views.api_transcribe, name="api_transcribe"),
]
