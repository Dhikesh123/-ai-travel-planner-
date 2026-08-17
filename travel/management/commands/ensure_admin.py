"""
Create the administrator account, or bring an existing one back into line
with the environment.

Django's own createsuperuser refuses to touch a username that already exists
and exits non-zero. That is exactly what was happening on this deployment:
an "admin" row was already in the database, so every boot logged

    CommandError: Error: That username is already taken.

the `|| true` in the start command swallowed it, and the password held in
DJANGO_SUPERUSER_PASSWORD was never applied - leaving a live admin account
that nobody had the password for. The free plan has no shell and no one-off
jobs, so the boot command is the only place this can be repaired.

This command is idempotent. It creates the account when it is missing, and
otherwise resets the password and re-grants staff/superuser. It does nothing
at all unless DJANGO_SUPERUSER_PASSWORD is set, so a deployment that has not
been given a password is left exactly as it is.

Run it with:   python manage.py ensure_admin
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the superuser named by the DJANGO_SUPERUSER_* variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username or not password:
            # Not an error: a deployment is allowed to have no admin account.
            self.stdout.write(
                "ensure_admin: DJANGO_SUPERUSER_USERNAME or _PASSWORD is not set, "
                "so no account was created or changed."
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username, defaults={"email": email}
        )

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if email:
            user.email = email
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                "ensure_admin: %s superuser %r."
                % ("created" if created else "updated existing", username)
            )
        )
