"""
Check that the AI features are set up correctly.

Run it with:   python manage.py check_ai

It tells you, in plain English:
  * whether your API key is present and working
  * which models your Groq account can use
  * whether chat, translation, image recognition and speech-to-text all work

Use this whenever the AI pages say "not connected" and you are not sure why.
"""
import base64
import io

from django.conf import settings
from django.core.management.base import BaseCommand

from travel.services import ai_service


class Command(BaseCommand):
    help = "Check the Groq API key, list available models, and test each AI feature."

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        # --- 1. Is there a key at all? ------------------------------------
        self.stdout.write("1. API key")
        if not ai_service.is_configured():
            self.stdout.write(bad("   MISSING. Add GROQ_API_KEY to your .env file, then restart."))
            return
        key = settings.GROQ_API_KEY
        self.stdout.write(ok(f"   Found ({key[:7]}...{key[-4:]})"))

        # --- 2. Which models can this account use? -------------------------
        self.stdout.write("\n2. Models your account can use")
        try:
            from groq import Groq

            client = Groq(api_key=key)
            available = sorted(m.id for m in client.models.list().data)
        except Exception as exc:
            self.stdout.write(bad(f"   Could not reach Groq: {exc}"))
            return

        for model_id in available:
            self.stdout.write(f"   - {model_id}")

        # --- 3. Are the models we configured actually available? -----------
        self.stdout.write("\n3. Models this project is set to use")
        configured = [
            ("Chat / translation", settings.GROQ_CHAT_MODEL),
            ("Image recognition", settings.GROQ_VISION_MODEL),
            ("Speech to text", settings.GROQ_WHISPER_MODEL),
        ]
        for label, model_id in configured:
            if model_id in available:
                self.stdout.write(ok(f"   {label}: {model_id}"))
            else:
                self.stdout.write(
                    bad(f"   {label}: {model_id} is NOT available on your account.")
                )
                self.stdout.write(
                    warn("      Pick one from the list above and set it in your .env file.")
                )

        # --- 4. Actually try each feature ---------------------------------
        self.stdout.write("\n4. Live test of each feature")

        # Chat
        try:
            reply = ai_service.chat("Say only the word: ready")
            self.stdout.write(ok(f"   Chat: working ({reply.strip()[:40]})"))
        except ai_service.AIError as exc:
            self.stdout.write(bad(f"   Chat: FAILED - {exc}"))

        # Translation
        try:
            result = ai_service.translate("నేను ముంబైకి వెళ్లాలి", "te", "en")
            self.stdout.write(ok(f"   Telugu to English: working ({result.strip()[:50]})"))
        except ai_service.AIError as exc:
            self.stdout.write(bad(f"   Translation: FAILED - {exc}"))

        # Vision - send a tiny picture we build here, so no file is needed
        try:
            from PIL import Image, ImageDraw

            image = Image.new("RGB", (240, 160), (255, 255, 255))
            ImageDraw.Draw(image).ellipse([40, 30, 200, 130], fill=(30, 90, 220))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            text, _ = ai_service.analyse_image(buffer.getvalue(), "image/jpeg", "What colour is this?")
            first_line = text.strip().splitlines()[0] if text.strip() else ""
            self.stdout.write(ok(f"   Image recognition: working ({first_line[:50]})"))
        except ai_service.AIError as exc:
            self.stdout.write(bad(f"   Image recognition: FAILED - {exc}"))
        except Exception as exc:
            self.stdout.write(bad(f"   Image recognition: FAILED - {exc}"))

        # Whisper is only checked for availability - testing it would need a
        # real audio recording, which we cannot make here.
        if settings.GROQ_WHISPER_MODEL in available:
            self.stdout.write(ok("   Speech to text: model available (record audio to test fully)"))
        else:
            self.stdout.write(bad("   Speech to text: model not available"))

        self.stdout.write("\nDone. Anything marked FAILED above needs fixing before that "
                          "page will work.")
