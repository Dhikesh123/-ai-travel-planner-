"""
The languages the site speaks, in one place.

Before this file the site knew exactly two languages, and it knew them
separately in nine places: two model fields, the AI prompts, three templates
with hand-written <option> tags, and three JavaScript files that each decided
what "te" meant on their own. Adding a language meant finding all nine.

Now everything reads this list:

  * Profile.preferred_language and the sign-up form take their choices here.
  * ai_service asks it for the name to put in a prompt.
  * The templates loop over it to build their dropdowns.
  * The browser gets it as JSON (see context_processors.languages), so
    speech.js and chatbot.js work from the same list rather than a regex
    with one alphabet in it.

To add a language, add one row below. Nothing else needs to change.

The set is English plus the eleven most widely spoken Indian languages,
which is what a travel site for India needs. Groq's chat model writes all of
them and Whisper transcribes them; how well a browser SPEAKS them aloud
depends on the voices installed on the customer's own device, which is why
speech.js checks before promising.
"""


class Language:
    """One language the site can read, write, hear and speak."""

    def __init__(self, code, name, native_name, speech_code, script=None):
        # code         ISO 639-1, what we store and send to Whisper ("te")
        # name         English name, for prompts and the admin ("Telugu")
        # native_name  what it calls itself, for the dropdowns ("తెలుగు")
        # speech_code  BCP-47, what a browser recogniser wants ("te-IN")
        # script       (first, last) characters of its alphabet, or None for
        #              the Latin alphabet, which we treat as the fallback
        self.code = code
        self.name = name
        self.native_name = native_name
        self.speech_code = speech_code
        self.script = script

    def __str__(self):
        return self.name

    @property
    def label(self):
        """What a dropdown shows: "Telugu (తెలుగు)", or just "English"."""
        if self.native_name == self.name:
            return self.name
        return "%s (%s)" % (self.name, self.native_name)

    def as_dict(self):
        """The shape handed to the browser as JSON."""
        return {
            "code": self.code,
            "name": self.name,
            "nativeName": self.native_name,
            "speechCode": self.speech_code,
            "label": self.label,
            # JavaScript builds a RegExp from these two characters
            "scriptStart": self.script[0] if self.script else "",
            "scriptEnd": self.script[1] if self.script else "",
        }


# English first because it is the default, then Telugu because this project
# started as a Telugu-and-English site, then the rest by number of speakers.
LANGUAGES = [
    Language("en", "English", "English", "en-IN"),
    Language("te", "Telugu", "తెలుగు", "te-IN", ("ఀ", "౿")),
    Language("hi", "Hindi", "हिन्दी", "hi-IN", ("ऀ", "ॿ")),
    Language("ta", "Tamil", "தமிழ்", "ta-IN", ("஀", "௿")),
    Language("kn", "Kannada", "ಕನ್ನಡ", "kn-IN", ("ಀ", "೿")),
    Language("ml", "Malayalam", "മലയാളം", "ml-IN", ("ഀ", "ൿ")),
    # Marathi is written in the same Devanagari alphabet as Hindi, so no
    # amount of looking at the letters can tell the two apart. It has no
    # script range here on purpose: see detect() below.
    Language("mr", "Marathi", "मराठी", "mr-IN"),
    Language("bn", "Bengali", "বাংলা", "bn-IN", ("ঀ", "৿")),
    Language("gu", "Gujarati", "ગુજરાતી", "gu-IN", ("઀", "૿")),
    Language("pa", "Punjabi", "ਪੰਜਾਬੀ", "pa-IN", ("਀", "੿")),
    Language("ur", "Urdu", "اردو", "ur-IN", ("؀", "ۿ")),
    Language("or", "Odia", "ଓଡ଼ିଆ", "or-IN", ("଀", "୿")),
]

BY_CODE = {language.code: language for language in LANGUAGES}

# For a model field's choices=, and for any form built from one.
CHOICES = [(language.code, language.label) for language in LANGUAGES]

# code -> English name, which is what the AI prompts want.
NAMES = {language.code: language.name for language in LANGUAGES}

DEFAULT_CODE = "en"


def is_supported(code):
    return code in BY_CODE


def get(code):
    """The Language for a code, falling back to English rather than failing."""
    return BY_CODE.get(code) or BY_CODE[DEFAULT_CODE]


def name_for(code):
    """The English name for a code, for putting inside an AI prompt."""
    return NAMES.get(code, code)


def clean_code(code, default=DEFAULT_CODE):
    """
    Make a language code from whatever arrived - a form field, a JSON body,
    a browser's "te-IN". Anything unrecognised becomes the default, so a
    stray value can never reach the AI service or the database.
    """
    if not code:
        return default
    code = str(code).strip().lower().replace("_", "-").split("-")[0]
    return code if code in BY_CODE else default


def detect(text):
    """
    Guess which language a piece of text is written in, by its alphabet.

    Used for one thing only: choosing the voice for the "read aloud" button.
    Getting it wrong makes a sentence sound odd, not break, so a simple
    count of letters per alphabet is enough.

    Text in Devanagari is reported as Hindi. It could equally be Marathi -
    they share every letter - and no rule over the characters alone can
    separate them. Hindi wins because it has far more speakers.
    """
    if not text:
        return DEFAULT_CODE

    counts = {}
    for character in text:
        for language in LANGUAGES:
            if language.script and language.script[0] <= character <= language.script[1]:
                counts[language.code] = counts.get(language.code, 0) + 1
                break

    if not counts:
        return DEFAULT_CODE
    return max(counts, key=counts.get)


def as_dicts():
    """The whole list in the shape the browser receives it."""
    return [language.as_dict() for language in LANGUAGES]
