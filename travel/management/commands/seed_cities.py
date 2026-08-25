"""
Load the starting-city list into the database.

Run it with:   python manage.py seed_cities

These are the towns the "From" box suggests as you type. They live in
travel/data/cities.py with their coordinates already looked up, so this
command needs no internet and can be re-run safely - a city already in the
table is updated, never duplicated.

A city that is NOT on the list still works: type it, and geo_service asks
OpenStreetMap once when the trip is planned and writes the answer into the
same table. The two feed each other - the seeded list is the head start, and
the site fills in the rest as people use it.
"""
from django.core.management.base import BaseCommand

from travel.data.cities import CITIES
from travel.models import CityLocation


class Command(BaseCommand):
    help = "Load the suggested starting cities into the CityLocation table."

    def handle(self, *args, **options):
        added = updated = 0
        for name, state, latitude, longitude in CITIES:
            _row, created = CityLocation.objects.update_or_create(
                # lower-cased, because that is the key geo_service looks up by
                name=name.lower(),
                defaults={
                    # what the dropdown shows: "Bhimavaram, Andhra Pradesh"
                    "display_name": "%s, %s" % (name, state),
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            if created:
                added += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Starting cities: %d added, %d already known" % (added, updated)
            )
        )
