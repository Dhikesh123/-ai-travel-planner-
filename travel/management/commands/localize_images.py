"""
Download every destination and tourist-place photograph and keep it inside
the project, so the site stops borrowing pictures from Wikimedia on every
page view.

Run it with:   python manage.py localize_images

What it does, in order:

1. Reads the IMAGES map in seed_data.py - the one list of "which picture
   belongs to which place".
2. Downloads anything that is still a web address into
   static/images/destinations/ and static/images/places/, shrinking each
   photograph to a 640px wide JPEG so the folder stays a sensible size.
3. Writes static/images/CREDITS.md, because Wikimedia photographs are free
   to reuse but their photographers must be named.
4. Rewrites the IMAGES map to point at the downloaded copies, so a fresh
   "python manage.py seed_data" on a new machine uses the local files too.
5. Updates the rows already in the database, so the running site switches
   over without a re-seed.

Re-running is safe: a photograph already on disk is left alone unless you
pass --force.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image

from travel.models import Destination, TouristPlace
from travel.management.commands import seed_data

# Wikimedia asks every automated caller to say who it is and how to make
# contact, and blocks the generic Python one.
USER_AGENT = (
    "AITravelPlanner/1.0 (student project; yerradhikesh@gmail.com) Python-urllib"
)
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# The widest a card is ever drawn is about 370px (three across a 1200px page),
# so 640px still has pixels to spare on a high-density screen. It keeps each
# photograph around 40-60 KB instead of the 1-7 MB Commons original, which
# matters because static/ is committed and shipped with the code.
MAX_WIDTH = 640
JPEG_QUALITY = 78

IMAGE_ROOT = Path(settings.BASE_DIR) / "static" / "images"
SEED_FILE = Path(seed_data.__file__)


def fetch(url, timeout=45):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout).read()


def commons_title(url):
    """Work out the Commons file name from an upload.wikimedia.org address.

    Thumbnails look like  .../commons/thumb/a/ab/Name.jpg/800px-Name.jpg
    and originals like    .../commons/a/ab/Name.jpg
    """
    path = urllib.parse.urlparse(url).path
    if "/thumb/" in path:
        # the part before the "800px-..." tail is the real file name
        name = path.split("/thumb/", 1)[1].split("/")[2]
    else:
        name = path.rsplit("/", 1)[-1]
    return urllib.parse.unquote(name)


def commons_info(title):
    """Ask Commons for a right-sized thumbnail plus the credit line."""
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": "File:" + title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": MAX_WIDTH,
        }
    )
    pages = json.loads(fetch(COMMONS_API + "?" + query))["query"]["pages"]
    page = next(iter(pages.values()))
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})

    def field(key):
        value = meta.get(key, {}).get("value", "")
        # the author field arrives as HTML: "<a href=...>Someone</a>"
        return re.sub(r"<[^>]+>", "", value).strip()

    return {
        "download": info.get("thumburl") or info.get("url", ""),
        "page": info.get("descriptionurl", ""),
        "author": field("Artist") or "Unknown",
        "licence": field("LicenseShortName") or "see file page",
    }


def save_photograph(raw, destination_path):
    """Shrink to MAX_WIDTH and write it out as a JPEG."""
    image = Image.open(BytesIO(raw))
    # PNGs and GIFs can carry transparency, which JPEG cannot: lay them on
    # white first so the corners do not turn black.
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGB", image.size, (255, 255, 255))
        canvas.paste(image, mask=image.split()[-1])
        image = canvas
    else:
        image = image.convert("RGB")
    if image.width > MAX_WIDTH:
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.LANCZOS)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        destination_path,
        "JPEG",
        quality=JPEG_QUALITY,
        optimize=True,
        progressive=True,
    )
    return destination_path.stat().st_size


class Command(BaseCommand):
    help = "Download the place photographs into static/ and link them locally."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Download again even when the file is already on disk.",
        )
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Leave seed_data.py alone (only touch the database).",
        )
        parser.add_argument(
            "--skip-db",
            action="store_true",
            help="Leave the database alone (only download and rewrite the seeder).",
        )
        parser.add_argument(
            "--only",
            default="",
            help="Download just the places whose name contains this text.",
        )

    def handle(self, *args, **options):
        images = dict(seed_data.IMAGES)
        destination_names = {item["name"] for item in seed_data.DESTINATIONS}
        if options["only"]:
            needle = options["only"].lower()
            images = {k: v for k, v in images.items() if needle in k.lower()}

        local_path = {}      # place name  -> "/static/images/..."
        by_source = {}       # web address -> "/static/images/..." (share repeats)
        credits = []
        failures = []

        total = len(images)
        for index, (name, source) in enumerate(images.items(), start=1):
            if not source:
                continue
            if not source.startswith("http"):
                # already a local path from an earlier run
                local_path[name] = source
                continue
            if source in by_source:
                # two places already sharing one photograph, e.g. a hill town
                # and the temple on top of it - reuse the same file
                local_path[name] = by_source[source]
                continue

            folder = "destinations" if name in destination_names else "places"
            target = IMAGE_ROOT / folder / (slugify(name) + ".jpg")
            web_path = "%simages/%s/%s" % (settings.STATIC_URL, folder, target.name)
            if not web_path.startswith("/"):
                web_path = "/" + web_path

            if target.exists() and not options["force"]:
                local_path[name] = by_source[source] = web_path
                self.stdout.write("[%3d/%d] have   %s" % (index, total, target.name))
                continue

            try:
                title = commons_title(source)
                info = commons_info(title)
                raw = fetch(info["download"] or source)
                size = save_photograph(raw, target)
            except Exception as exc:                  # keep going, report later
                failures.append((name, source, str(exc)))
                self.stdout.write(
                    self.style.WARNING(
                        "[%3d/%d] FAILED %s - %s" % (index, total, name, exc)
                    )
                )
                time.sleep(1)
                continue

            local_path[name] = by_source[source] = web_path
            credits.append(
                {
                    "place": name,
                    "file": "%s/%s" % (folder, target.name),
                    "author": info["author"],
                    "licence": info["licence"],
                    "source": info["page"] or source,
                }
            )
            self.stdout.write(
                "[%3d/%d] saved  %-38s %5.0f KB"
                % (index, total, target.name, size / 1024)
            )
            time.sleep(0.2)                           # be polite to Wikimedia

        self.write_credits(credits)
        if not options["skip_seed"]:
            self.rewrite_seed(local_path)
        if not options["skip_db"]:
            self.update_database(local_path)

        self.stdout.write(
            self.style.SUCCESS(
                "\nPhotographs on disk: %d   failures: %d"
                % (len(set(local_path.values())), len(failures))
            )
        )
        for name, source, error in failures:
            self.stdout.write(self.style.WARNING("  %s: %s" % (name, error)))

    # ------------------------------------------------------------------
    def write_credits(self, credits):
        """Name the photographers - the licences require it."""
        if not credits:
            return
        path = IMAGE_ROOT / "CREDITS.md"
        known = {}
        if path.exists():
            # keep the lines written by earlier runs
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("| `"):
                    known[line.split("|")[1].strip()] = line
        for entry in credits:
            known["`%s`" % entry["file"]] = (
                "| `%(file)s` | %(place)s | %(author)s | %(licence)s | %(source)s |"
                % entry
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Photograph credits\n\n"
            "Every picture below came from Wikimedia Commons and is reused "
            "under the licence named in its row.\n"
            "Downloaded by `python manage.py localize_images`.\n\n"
            "| File | Place | Photographer | Licence | Source |\n"
            "| --- | --- | --- | --- | --- |\n"
            + "\n".join(known[key] for key in sorted(known))
            + "\n",
            encoding="utf-8",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Credits written: static/images/CREDITS.md (%d files)" % len(known)
            )
        )

    # ------------------------------------------------------------------
    def rewrite_seed(self, local_path):
        """Point the IMAGES map at the downloaded copies."""
        text = SEED_FILE.read_text(encoding="utf-8")
        start = text.index("IMAGES = {")
        end = text.index("\n}\n", start)
        head, body, tail = text[:start], text[start:end], text[end:]

        changed = 0
        for name, path in local_path.items():
            pattern = re.compile(r'("%s":\s*)"[^"]*"' % re.escape(name))
            body, count = pattern.subn(
                lambda match: match.group(1) + '"%s"' % path, body
            )
            changed += count

        SEED_FILE.write_text(head + body + tail, encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(
                "seed_data.py updated: %d entries now point at static/images/"
                % changed
            )
        )

    # ------------------------------------------------------------------
    def update_database(self, local_path):
        """Switch the rows already saved to the downloaded copies."""
        updated = 0
        for model in (Destination, TouristPlace):
            for row in model.objects.all():
                path = local_path.get(row.name)
                if path and row.image_url != path:
                    row.image_url = path
                    row.save(update_fields=["image_url"])
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS("Database rows repointed: %d" % updated)
        )
