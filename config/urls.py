"""Main URL router. It sends every web address to the right place."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django's built-in admin site (database management)
    path("django-admin/", admin.site.urls),
    # Everything else lives in the travel app
    path("", include("travel.urls")),
]

# During development, let Django serve uploaded images from /media/
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
