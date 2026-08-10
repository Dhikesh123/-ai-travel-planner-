# AI Travel Planner & Smart Trip Assistant

A complete travel portal built with **Django** and the **Groq AI API**.

It has a **Customer Portal** and an **Admin Portal**, a **trip cost calculator**,
a **day-by-day itinerary generator**, an **AI chatbot**, **voice input**,
**Telugu ↔ English translation**, **text-to-speech**, and **image recognition**.

> **Important:** every price, distance and travel time in this project is a
> **demonstration estimate** calculated from sample rates stored in the
> database. They are **not** live fares, live hotel rates, or live availability.

---

## Table of contents

1. [What you need before you start](#1-what-you-need-before-you-start)
2. [Installation (exact Windows commands)](#2-installation-exact-windows-commands)
3. [The 16 build phases](#3-the-16-build-phases)
4. [Project folder structure](#4-project-folder-structure)
5. [Database design](#5-database-design)
6. [API endpoints](#6-api-endpoints)
7. [The cost calculator explained](#7-the-cost-calculator-explained)
8. [Security](#8-security)
9. [Error handling](#9-error-handling)
10. [Testing](#10-testing)
11. [Beginner explanation of every concept](#11-beginner-explanation-of-every-concept)
12. [Putting it on GitHub](#12-putting-it-on-github)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What you need before you start

| Thing | Why | Where |
|---|---|---|
| Python 3.11–3.14 | Runs Django | <https://python.org/downloads> |
| A code editor | To read and edit files | VS Code is free |
| A Groq API key | For the AI features only | <https://console.groq.com> |
| Git (optional) | To put the code on GitHub | <https://git-scm.com> |

**You can run the whole site without an API key.** The planner, cost
calculator, itinerary, admin portal and database all work. Only the chat,
translation and image recognition need the key, and they show a clear
message when it is missing instead of crashing.

---

## 2. Installation (exact Windows commands)

Open **Command Prompt** or **PowerShell** and run these one at a time.

### Step 1 — go to the project folder

```
cd ai-travel-planner
```

### Step 2 — create a virtual environment

```
python -m venv venv
```

*A virtual environment is a private box of Python packages just for this
project. Without it, installing Django here could break another project on
your computer.*

### Step 3 — activate the virtual environment

```
venv\Scripts\activate
```

*Your prompt now starts with `(venv)`. That means the box is open. You must
run this command every time you open a new terminal for this project.*

### Step 4 — install the packages

```
pip install django
pip install djangorestframework
pip install groq
pip install python-dotenv
pip install pillow
```

Or install all of them at once:

```
pip install -r requirements.txt
```

*What each one does:*
- **django** — the web framework (pages, database, admin, security)
- **djangorestframework** — makes building the JSON API easier
- **groq** — the official library for talking to the Groq AI API
- **python-dotenv** — reads your secret keys from the `.env` file
- **pillow** — lets Django handle image uploads

### Step 5 — create your `.env` file

```
copy .env.example .env
```

Then open `.env` in your editor and paste your API key:

```
GROQ_API_KEY=gsk_your-real-key-here
```

*`.env` holds your secrets. It is listed in `.gitignore`, so it will never be
uploaded to GitHub.*

**Which AI models this project uses.** Groq offers several models, and this
project picks the right one for each job. The defaults are already set, so
you normally do not need to change anything:

| Job | Setting | Default model | Why this one |
|---|---|---|---|
| Chat and translation | `GROQ_CHAT_MODEL` | `llama-3.3-70b-versatile` | Fast, and good at Telugu |
| Image recognition | `GROQ_VISION_MODEL` | `qwen/qwen3.6-27b` | The model that can actually see pictures |
| Speech to text | `GROQ_WHISPER_MODEL` | `whisper-large-v3` | Turns a recording into words |

**Check that it all works** with the built-in checker:

```
python manage.py check_ai
```

It prints your key status, every model your account can use, and a live test
of chat, translation and image recognition. Run it whenever an AI page says
"not connected" and you are not sure why.

### Step 6 — create the database tables

```
python manage.py makemigrations
python manage.py migrate
```

*`makemigrations` looks at `models.py` and writes the instructions for
changing the database. `migrate` actually runs those instructions and builds
the tables.*

### Step 7 — load the sample destinations and places

```
python manage.py seed_data
```

*This fills the database with 6 destinations, 27 tourist places, 4 transport
options and 12 sample distances so the site is usable immediately.*

### Step 8 — create your admin account

```
python manage.py createsuperuser
```

*It asks for a username, email and password. This account can open the admin
portal. The password you type is never stored — only a secure hash of it.*

### Step 9 — start the server

```
python manage.py runserver
```

Now open your browser at **<http://127.0.0.1:8000/>**

| Address | What it is |
|---|---|
| `http://127.0.0.1:8000/` | Home page |
| `http://127.0.0.1:8000/register/` | Create a customer account |
| `http://127.0.0.1:8000/dashboard/` | Customer dashboard |
| `http://127.0.0.1:8000/manage/` | Admin dashboard (staff only) |
| `http://127.0.0.1:8000/django-admin/` | Full Django admin |

Press **Ctrl + C** in the terminal to stop the server.

---

## 3. The 16 build phases

Everything below is already built. This section explains **what each phase
did, how to test it, and what you should see** — so you can walk through the
project the way it was constructed.

### Phase 1 — Django setup
**Objective:** get an empty Django site running.
**Files:** `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`, `.env`
**Test:** `python manage.py runserver` → the home page loads.
**Expected:** no errors in the terminal.

### Phase 2 — Database models
**Objective:** design the tables.
**Files:** `travel/models.py`, `travel/signals.py`
**Commands:** `python manage.py makemigrations` then `migrate`
**Test:** `python manage.py migrate` finishes with `OK` on every line.
**Expected:** a `db.sqlite3` file appears.

### Phase 3 — Registration and login
**Objective:** customers can create accounts.
**Files:** `travel/forms.py` (`RegisterForm`), `travel/views.py`, `templates/register.html`, `templates/login.html`
**Test:** go to `/register/`, create an account, then log out and log back in.
**Expected:** after registering you land on the dashboard with a welcome message.

### Phase 4 — Customer dashboard
**Objective:** a home base for the logged-in customer.
**Files:** `templates/dashboard.html`
**Test:** visit `/dashboard/` while logged out → you are sent to the login page.
**Expected:** stat cards, quick links, and recent trips as cards.

### Phase 5 — Travel planner
**Objective:** the trip form.
**Files:** `travel/forms.py` (`TripForm`), `templates/planner.html`
**Test:** enter Pune → Mumbai, 2 travellers, 3 days, Car.
**Expected:** the trip saves and you are taken to the trip detail page.

### Phase 6 — Trip cost calculator
**Objective:** live cost estimates.
**Files:** `travel/services/travel_service.py`, `static/js/planner.js`, `templates/calculator.html`
**Test:** on `/calculator/`, change the number of travellers.
**Expected:** the total updates within about half a second, without reloading the page.

### Phase 7 — Tourist places
**Objective:** the destination database.
**Files:** `travel/models.py`, `travel/management/commands/seed_data.py`, `templates/destinations.html`
**Test:** `python manage.py seed_data`, then visit `/destinations/`.
**Expected:** 6 destination cards; clicking one shows its tourist places.

### Phase 8 — Admin portal
**Objective:** staff management screens.
**Files:** `travel/admin.py`, `templates/admin_dashboard.html`
**Test:** log in as your superuser and visit `/manage/`.
**Expected:** customer counts, trip counts, popular destinations, recent trips.
A normal customer visiting `/manage/` is blocked.

### Phase 9 — Groq AI chatbot
**Objective:** the AI travel assistant.
**Files:** `travel/services/ai_service.py`, `travel/api_views.py`, `templates/chatbot.html`, `static/js/chatbot.js`
**Test:** go to `/assistant/` and ask *"Plan a 3-day trip from Pune to Mumbai for 2 people."*
**Expected:** a suggested itinerary. Without an API key you get a clear
message telling you to add one — not an error page.

### Phase 10 — Speech to text
**Objective:** speak instead of typing, in **any** browser.
**Files:** `static/js/speech.js`, `/api/transcribe/`, `travel/services/ai_service.py` (`transcribe`)
**Test:** click the microphone button on `/assistant/` or `/voice/` and speak.
**Expected:** your words appear in the text box.

There are two ways this can happen, and the app picks automatically:

1. **Chrome and Edge** turn speech into text inside the browser (Web Speech
   API). Instant, free, and the audio never leaves your computer.
2. **Safari, Firefox and some phones** cannot do that. There, the app records
   the microphone with `MediaRecorder`, sends the audio to `/api/transcribe/`,
   and Whisper writes it out on the server.

`Speech.startCapture()` in `speech.js` hides this difference, so the chat page
and the voice page both just call one function and do not care which method
was used. If neither works, you get a clear message telling you to type.

### Phase 11 — Telugu ↔ English translation
**Objective:** translate both directions.
**Files:** `travel/services/speech_service.py`, `/api/translate/`, `templates/voice.html`
**Test:** on `/voice/` type `నేను ముంబైకి వెళ్లాలి` and press Translate.
**Expected:** *"I want to go to Mumbai."*

### Phase 12 — Text to speech
**Objective:** read answers aloud.
**Files:** `static/js/speech.js` (`Speech.speak`)
**Test:** click the 🔊 button next to any AI message.
**Expected:** your device reads it aloud. If no Telugu voice is installed the
app says so clearly instead of failing silently.

### Phase 13 — Image recognition
**Objective:** identify a place from a photo.
**Files:** `travel/services/ai_service.py` (`analyse_image`), `templates/image_recognition.html`, `static/js/image.js`
**Test:** upload a photo of a monument on `/image-recognition/`.
**Expected:** place name, location, description, how to visit and nearby
places. If the AI is unsure it says **CONFIDENCE: LOW** and the page shows a
warning banner.

### Phase 14 — Integrate everything
**Objective:** one connected app.
**Test:** plan a trip → open it → press *Get AI suggestions* → open the chat →
attach a photo → use the voice page.
**Expected:** the AI already knows your route, dates and budget on the trip page.

### Phase 15 — Testing
**Files:** `travel/tests.py` (63 tests)
**Command:** `python manage.py test`
**Expected:** `Ran 63 tests ... OK`

### Phase 16 — GitHub preparation
**Files:** `.gitignore`, `.env.example`, `requirements.txt`, this README.
See [section 12](#12-putting-it-on-github).

---

## 4. Project folder structure

```
ai-travel-planner/
├── manage.py                  Django's command tool
├── requirements.txt           List of packages to install
├── .env                       YOUR SECRETS - never goes to GitHub
├── .env.example               A safe template of .env
├── .gitignore                 Tells Git what to ignore
├── db.sqlite3                 The database file
│
├── config/                    Project-wide settings
│   ├── settings.py            All configuration
│   ├── urls.py                Top-level address list
│   ├── wsgi.py / asgi.py      Server entry points
│
├── travel/                    The main app
│   ├── models.py              Database tables
│   ├── admin.py               Admin portal setup
│   ├── forms.py               Input validation rules
│   ├── serializers.py         Database objects -> JSON
│   ├── views.py               Builds the HTML pages
│   ├── api_views.py           Builds the JSON API
│   ├── urls.py                All addresses
│   ├── utils.py               Shared trip calculation helper
│   ├── signals.py             Auto-create a Profile per user
│   ├── tests.py               Automated tests
│   ├── migrations/            Database change history
│   ├── management/commands/
│   │   └── seed_data.py       Loads the sample data
│   └── services/
│       ├── ai_service.py  ALL Groq AI API calls
│       ├── travel_service.py  Distance, costs, itinerary
│       └── speech_service.py  Language detection + translation
│
├── templates/                 The HTML pages
│   ├── base.html              Shared layout (navbar + footer)
│   ├── home.html  register.html  login.html  dashboard.html
│   ├── planner.html  calculator.html  trips.html  trip_detail.html
│   ├── destinations.html  destination_detail.html  profile.html
│   ├── chatbot.html  voice.html  image_recognition.html
│   └── admin_dashboard.html
│
├── static/
│   ├── css/style.css          All styling (responsive)
│   └── js/
│       ├── app.js             Shared helpers (fetch, CSRF, formatting)
│       ├── planner.js         Live cost calculator
│       ├── chatbot.js         Chat page
│       ├── speech.js          Microphone + text-to-speech
│       ├── voice.js           Voice/translation page
│       ├── image.js           Image upload page
│       └── trip_detail.js     AI suggestions button
│
└── media/uploads/             Customer-uploaded images
```

---

## 5. Database design

### The tables

| Model | What it stores |
|---|---|
| `User` | Django's built-in login account (username, hashed password) |
| `Profile` | Extra customer info: phone, city, preferred language, avatar |
| `Destination` | A city you can travel to (Mumbai, Goa…) |
| `TouristPlace` | A spot inside a destination (Gateway of India) |
| `Transportation` | Car / Bike / Bus / Train and their sample rates |
| `RouteDistance` | Sample distance between two cities |
| `Trip` | One saved trip plan |
| `TripPlace` | Which place, on which day, of which trip |
| `TripCost` | The money breakdown of one trip |
| `ChatMessage` | One line of AI conversation |
| `UploadedImage` | A photo sent for recognition |

### The relationships

```
User ──1:1──> Profile                 each user has exactly one profile
User ──1:M──> Trip                    a user saves many trips
User ──1:M──> ChatMessage             a user has many chat messages
User ──1:M──> UploadedImage           a user uploads many images

Destination ──1:M──> TouristPlace     Mumbai has many places
Destination ──1:M──> Trip             many trips go to Mumbai
Transportation ──1:M──> Trip          many trips use "Car"

Trip ──1:1──> TripCost                each trip has one cost breakdown
Trip ──1:M──> TripPlace ──M:1──> TouristPlace
       (a trip visits many places, a place is in many trips, and the
        TripPlace row in the middle also records WHICH DAY)
```

Reading it as the project brief describes it:

```
Customer
   ↓
  Trip  ────→  Destination  ────→  Tourist Places
   ↓
Trip Cost

Customer  ────→  Chat Messages
```

**Why `TripPlace` exists:** a plain many-to-many link could only say *"this
trip includes Marine Drive."* We also need *"…on day 2, second stop."* The
extra table stores that.

**Moving to PostgreSQL later:** only the `DATABASES` block in
`config/settings.py` changes. No model code changes at all.

---

## 6. API endpoints

All of them return JSON. `Login?` means you must be signed in.

| Method | URL | Login? | What it does |
|---|---|---|---|
| POST | `/api/register/` | No | Creates an account and signs you in |
| POST | `/api/login/` | No | Signs in, starts a session |
| POST | `/api/logout/` | Yes | Ends the session |
| GET | `/api/me/` | Yes | Who is logged in |
| GET | `/api/destinations/` | No | List destinations (`?q=` to search) |
| GET | `/api/destinations/<id>/` | No | One destination **plus its tourist places** |
| GET | `/api/transportation/` | No | Car/bike/bus/train and their sample rates |
| GET | `/api/trips/` | Yes | List **my** saved trips |
| POST | `/api/trips/` | Yes | Create a trip, then auto-calculate cost + itinerary |
| GET | `/api/trips/<id>/` | Yes | Read one of my trips |
| PUT/PATCH | `/api/trips/<id>/` | Yes | Update it and recalculate |
| DELETE | `/api/trips/<id>/` | Yes | Delete it |
| POST | `/api/trips/<id>/suggestions/` | Yes | Ask the AI to review this trip |
| POST | `/api/calculate-cost/` | No | Full breakdown **without saving** — powers the live calculator |
| POST | `/api/chat/` | Yes | Send a message to the AI assistant |
| GET/DELETE | `/api/chat/history/` | Yes | Read or clear chat history |
| POST | `/api/translate/` | Yes | Telugu ↔ English translation |
| POST | `/api/image-recognition/` | Yes | Upload a photo, get an AI identification |
| POST | `/api/transcribe/` | Yes | Send a recording, get text back (Whisper) |

### Example: the cost calculator

**Request**
```json
POST /api/calculate-cost/
{
  "source": "Pune",
  "destination_id": 1,
  "travelers": 2,
  "days": 3,
  "transportation_id": 1,
  "hotel_category": "standard",
  "food_budget": "standard",
  "activity_budget": 0,
  "place_ids": [1, 2, 3]
}
```

**Response (real output from this project)**
```json
{
  "ok": true,
  "distance_km": 150,
  "distance_is_known": true,
  "travel_hours": "2.73",
  "costs": {
    "travel_cost": "3600.00",
    "hotel_cost": "4400.00",
    "food_cost": "3900.00",
    "local_transport_cost": "1500.00",
    "activity_cost": "0.00",
    "other_cost": "1072.00",
    "total_cost": "14472.00"
  },
  "itinerary": [ { "day": 1, "title": "Day 1", "items": ["..."] } ],
  "disclaimer": "All prices ... are DEMONSTRATION ESTIMATES ..."
}
```

Every error looks the same, so the JavaScript only needs one handler:
```json
{ "ok": false, "error": "Number of travellers must be between 1 and 50." }
```

---

## 7. The cost calculator explained

```
   Travel cost
 + Hotel cost
 + Food cost
 + Local transport cost
 + Activity cost
 + Other expenses
 ─────────────────────
 = Estimated total
```

| Part | Formula | Sample rates |
|---|---|---|
| **Travel** | distance × 2 × rate × units | Car ₹12/km, Bike ₹3.50/km, Bus ₹1.80/km, Train ₹1.20/km |
| **Hotel** | rate × rooms × nights | Budget ₹1,200 · Standard ₹2,200 · Deluxe ₹4,000 · Luxury ₹7,500 |
| **Food** | rate × travellers × days | Budget ₹350 · Standard ₹650 · Premium ₹1,300 |
| **Local transport** | ₹500 × groups × days | 1 group per 4 people |
| **Activities** | entry fees × travellers + extra budget | From each place's `entry_fee` |
| **Other** | 8% of everything above | Shopping, tips, emergencies |

**The rules that make it realistic**
- **Round trip:** distance is doubled (you come back).
- **Car and bike are per vehicle.** 6 people by car = 2 cars.
- **Bus and train are per person.** 3 people = 3 tickets.
- **Rooms hold 2 people.** 5 travellers = 3 rooms.
- **Nights = days − 1.** A 3-day trip needs 2 hotel nights; a 1-day trip needs none.

### Worked example — the project's demo trip

**Pune → Mumbai · 2 travellers · 3 days · Car**

| Part | Working | Amount |
|---|---|---|
| Travel | 150 km × 2 × ₹12 × 1 car | ₹3,600 |
| Hotel | 1 room × 2 nights × ₹2,200 | ₹4,400 |
| Food | 2 people × 3 days × ₹650 | ₹3,900 |
| Local transport | 1 group × 3 days × ₹500 | ₹1,500 |
| Activities | free places selected | ₹0 |
| Other | 8% of ₹13,400 | ₹1,072 |
| **Estimated total** | | **₹14,472** |
| | | *(₹7,236 per person)* |

Generated itinerary:

```
Day 1: Travel Pune to Mumbai by Car | Hotel check-in | Colaba Causeway | Gateway of India
Day 2: Juhu Beach | Marine Drive | Siddhivinayak Temple
Day 3: Free time / local sightseeing / shopping | Return journey Mumbai to Pune
```

> These are demonstration estimates from sample rates — not live prices.

**Everything recalculates** when you change travellers, days, transport,
hotel category, food budget or the selected places.

---

## 8. Security

| Protection | Where | What it stops |
|---|---|---|
| Password hashing | Django built-in | Nobody can read passwords, not even you |
| CSRF tokens | Every form and `fetch()` | Another website submitting forms as your user |
| Session authentication | `@login_required` | Strangers opening customer pages |
| Ownership checks | `Trip.objects.get(pk=pk, user=request.user)` | Customer A reading customer B's trips |
| Staff-only admin | `@staff_member_required` | Customers reaching the admin dashboard |
| Form validation | `travel/forms.py` | Bad dates, 0 travellers, past dates |
| API validation | `travel/serializers.py`, `api_views.py` | Bad data sent straight to the API |
| Upload size limit | 5 MB, in `settings.py` | Huge files filling the disk |
| Upload type limit | `.jpg .jpeg .png .webp .gif` | Someone uploading a program instead of a photo |
| API key protection | `.env` + `.gitignore` | Your Groq key leaking to GitHub |
| Server-side AI calls | `ai_service.py` only | The key never reaches the browser |
| Auto-escaped templates | Django default | Cross-site scripting (XSS) |
| ORM queries | Django default | SQL injection |
| Secure cookies when live | `if not DEBUG` in settings | Session theft over plain HTTP |

**Never exposed anywhere:** API keys, passwords (only hashes exist),
other customers' data.

**Test it yourself:** log in as a customer and open `/manage/` — you are
blocked. Try opening another user's trip URL — you get a 404.

---

## 9. Error handling

Every failure shows a plain-English message. Nothing shows a crash page.

| Problem | What the customer sees |
|---|---|
| Empty form field | "Please enter a valid starting city." |
| 0 travellers | "There must be at least 1 traveller." |
| Date in the past | "The travel date cannot be in the past." |
| Return before departure | "The return date must be on or after the travel date." |
| Same source and destination | "The starting city and destination cannot be the same." |
| Unknown route | Uses 250 km and shows a visible warning that it is a guess |
| Missing API key | Explains how to add it; the rest of the site keeps working |
| Invalid API key | "the Groq AI API key is missing or invalid." |
| No internet | "Could not reach the AI service. Check your internet connection." |
| AI rate limit | "Too many requests right now. Please try again in a moment." |
| Image too large | "That image is too large. Please use a file under 5 MB." |
| Wrong image type | "Unsupported image type. Please use JPG, PNG, WEBP or GIF." |
| Microphone blocked | "Microphone permission was blocked. Allow it in your browser settings." |
| No speech support at all | "This browser cannot use the microphone… or type your message instead." |
| No Telugu voice | Says the device has no Telugu voice; still shows the text |
| AI unsure about a photo | Shows a **CONFIDENCE: LOW** warning banner |
| Database error | "Could not save the trip. Please try again." |

---

## 10. Testing

```
python manage.py test
```

Expected output:

```
Ran 63 tests in ...s

OK
```

The 63 tests cover: profile auto-creation, distance lookup (both directions
and unknown routes), all six cost components, per-vehicle vs per-person
transport, hotel tiers, one-day trips with no hotel, itinerary structure,
form validation, trip saving and recalculation, login protection, staff-only
access, **one customer being unable to read another's trip**, password
hashing, public pages, full API create/read/update/delete, and Telugu
language detection, the AI no-key paths, upload validation, the speech-to-text endpoint, and the stripping of the vision model's internal reasoning.

Run one group only:

```
python manage.py test travel.tests.CostCalculatorTests
```

---

## 11. Beginner explanation of every concept

**1. What is Django?**
A Python web framework — a big box of ready-made parts for websites: pages,
database handling, login, an admin panel, and security. Without it you would
write all of that yourself.

**2. What is a Python backend?**
The part of the website that runs on the *server*, not in your browser. It
reads and writes the database, checks passwords, and talks to the AI. Nobody
can see this code.

**3. What is HTML?**
The language that describes what is *on* a page: headings, paragraphs,
buttons, forms. Our HTML lives in `templates/`. CSS (`static/css/style.css`)
then describes what it *looks like*.

**4. What is JavaScript?**
The language that runs *inside the browser* and makes pages interactive —
updating the cost total as you type, without reloading the page. Ours lives
in `static/js/`.

**5. What is an API?**
A way for two programs to talk. Instead of sending a pretty web page, an API
sends plain data (JSON) that another program can use. Our JavaScript calls
our Django API; our Django API calls Groq's API.

**6. What is the Groq AI API?**
Groq's service. You send text (or an image) and it sends back an
intelligent reply. It is what makes the chatbot, the translation and the
image recognition work.

**7. What is an API key?**
A long secret password that proves *you* are the one calling the API — and
decides who gets billed. Treat it like a bank password: keep it in `.env`,
never put it in your code, and never upload it to GitHub.

**8. What is a database?**
An organised store of information that survives after the program closes.
Ours holds customers, destinations, trips and chat messages.

**9. What is SQLite?**
The simplest database — a single file (`db.sqlite3`) with no separate
program to install. Perfect for learning. For a busy live site you would
switch to PostgreSQL, which only needs a settings change here.

**10. What is a Django model?**
A Python class that describes one database table. `class Trip(models.Model)`
creates a `trip` table, and each attribute becomes a column. You write
Python; Django writes the SQL.

**11. What is an API endpoint?**
One specific address in your API that does one job — for example
`/api/calculate-cost/` calculates a cost. This project has 19 of them.

**12. How does the frontend talk to the backend?**
```
You change "travellers" from 2 to 4
        ↓
JavaScript notices the change (planner.js)
        ↓
fetch() sends JSON to /api/calculate-cost/  ── with a CSRF token
        ↓
Django validates it, calculates, returns JSON
        ↓
JavaScript writes the new total onto the page
```
No page reload happens — that is why it feels instant.

**13. How does the backend talk to the AI?**
```
Django reads GROQ_API_KEY from .env
        ↓
ai_service.py builds a message + a system prompt
        ↓
client.messages.create(...) sends it over the internet
        ↓
The AI replies with a message
        ↓
We keep only the text blocks and return them
```
The key stays on the server the entire time.

**14. How does speech recognition work?**
Your browser has a built-in `SpeechRecognition` feature. It records the
microphone, sends the audio to the browser maker's service, and returns
text — free, and no server code needed. See `static/js/speech.js`.

**15. How does speech-to-text work here?**
Exactly as above: you press 🎤, speak, and the recognised words appear in the
text box. You choose English or Telugu first, because the recogniser needs to
know which language to expect.

**16. How does translation work?**
The text goes to our `/api/translate/` endpoint. Django asks the AI with a
strict instruction: *"Reply with ONLY the translation."* The result comes
back and is shown. `speech_service.detect_language()` spots Telugu
automatically by checking for Telugu letters (Unicode range 0C00–0C7F).

**17. How does text-to-speech work?**
The browser's `speechSynthesis` feature reads text aloud using the voices
installed on your device. That is why Telugu speech depends on your device
having a Telugu voice — the app tells you when it does not.

**18. How does image recognition work?**
```
You choose a photo
        ↓
JavaScript checks size and type FIRST (fast feedback)
        ↓
The file uploads to /api/image-recognition/
        ↓
Django saves it, converts it to base64 text
        ↓
The vision model looks at it and answers
        ↓
We check for "CONFIDENCE: HIGH" and warn you if it is LOW
```
Base64 is a way of writing a picture as plain text so it can travel inside a
normal API request.

**19. How does the customer portal work?**
Register → login → dashboard → plan a trip → pick places → see the estimate →
save → view/edit/delete → chat with the AI → speak → upload photos. Every
page is protected by `@login_required`, and every trip query is filtered by
`user=request.user` so you only ever see your own data.

**20. How does the admin portal work?**
Django reads `travel/admin.py` and builds full management screens
automatically. `/manage/` adds a custom dashboard with statistics.
`@staff_member_required` blocks normal customers. Customer passwords are
never shown — only hashes exist in the database.

---

## 12. Putting it on GitHub

**Before you push, check that `.env` is ignored.** Run:

```
git status
```

If you see `.env` in the list, **stop** — your API key would be published.
Make sure `.gitignore` contains `.env`.

```
git init
git add .
git commit -m "AI Travel Planner: Django + Groq AI API"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ai-travel-planner.git
git push -u origin main
```

What gets ignored (and why): `.env` (secrets), `venv/` (huge, rebuildable),
`db.sqlite3` (your local data), `media/` (uploads), `__pycache__/`.

Anyone cloning your repo runs the [Step 2–9 commands](#2-installation-exact-windows-commands)
and gets a working site with their own key.

**Before going live on a real server:**
- Set `DEBUG=False` in `.env`
- Put your real domain in `ALLOWED_HOSTS`
- Generate a new long `SECRET_KEY`
- Run `python manage.py collectstatic`
- Switch `DATABASES` to PostgreSQL

---

## 13. Troubleshooting

| Message | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add Python to PATH** |
| `No module named django` | Activate the venv: `venv\Scripts\activate` |
| `no such table: travel_trip` | Run `python manage.py migrate` |
| Home page has no destinations | Run `python manage.py seed_data` |
| "AI assistant is not connected" | Put your key in `.env`, then restart the server |
| `Port 8000 is already in use` | `python manage.py runserver 8001` |
| CSS looks missing | Hard refresh with **Ctrl + F5** |
| Microphone does nothing | Use Chrome or Edge; allow the microphone permission |
| Telugu is not spoken aloud | Your device has no Telugu voice; the text still appears |
| Changed `.env` but nothing changed | Restart the server — `.env` is read once at startup |

---

## Credits

Built with Django, Django REST Framework and the Groq AI API.

**Final reminder:** all prices, distances and travel times in this project
are demonstration estimates from sample rates. Connect a real travel API
before using anything here for actual bookings.
