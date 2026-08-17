/*
 * The frontend's whole job: read from the Django API on Render and render it.
 *
 * There is no build step and no framework - the pages are small enough that
 * plain DOM code stays shorter and easier to follow than a bundle would be.
 */
const API = window.API_BASE.replace(/\/+$/, "");

const $ = (id) => document.getElementById(id);

/* ---------------------------------------------------------------- helpers */

/** One place that talks to the API, so every call reports failure the same way. */
async function api(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    throw new Error(`The API returned a ${response.status} that was not JSON.`);
  }

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `The API returned ${response.status}.`);
  }
  return data;
}

/** Rupees, written the way the rest of the project writes them. */
function rupees(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return "Rs " + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function banner(message, kind = "error") {
  const box = $("apiStatus");
  $("apiStatusText").textContent = message;
  box.className = "api-status api-status-" + kind;
  box.hidden = false;
}

function hideBanner() {
  $("apiStatus").hidden = true;
}

/** Escape anything that came from the API before it goes near innerHTML. */
function esc(text) {
  const d = document.createElement("div");
  d.textContent = text == null ? "" : String(text);
  return d.innerHTML;
}

/**
 * A picture for a destination or a place.
 *
 * The API hands back whatever the record has - an uploaded file, a web URL, or
 * nothing at all - so three things are guarded here:
 *
 *   - no image at all: return nothing, and the card lays out without a slot
 *     rather than leaving a broken frame behind
 *   - a URL that 404s or is blocked: onerror hides the element, for the same
 *     reason - a broken-image icon looks like a bug in the site
 *   - only http(s) is allowed through, so a javascript: value coming back from
 *     the API could never reach the src attribute
 *
 * loading="lazy" matters here: a destination list is a screenful of photos and
 * most are below the fold on a phone.
 */
function photo(url, alt, className) {
  const src = String(url || "");
  if (!/^https?:\/\//i.test(src)) return "";
  return (
    `<img class="${className}" src="${esc(src)}" alt="${esc(alt)}"` +
    ` loading="lazy" decoding="async" onerror="this.remove()">`
  );
}

/* ------------------------------------------------------------ destinations */

let DESTINATIONS = [];

function drawDestinations(list) {
  const grid = $("destGrid");

  if (!list.length) {
    grid.innerHTML = `<p class="muted">No destinations match that search.</p>`;
    return;
  }

  grid.innerHTML = list
    .map(
      (d) => `
      <article class="card">
        ${photo(d.image, d.name, "card-media")}
        <h3>${esc(d.name)}</h3>
        <p class="muted small">${esc(d.state || d.country || "")}</p>
        <p class="small">${esc(d.description || "")}</p>
        <p class="meta">
          <span>≈ ${rupees(d.estimated_cost_per_day)} / person / day</span>
          <span>${esc(d.recommended_days)} days suggested</span>
        </p>
        <button class="btn btn-quiet" data-plan="${esc(d.id)}">Plan a trip here</button>
      </article>`
    )
    .join("");

  grid.querySelectorAll("[data-plan]").forEach((button) => {
    button.addEventListener("click", () => {
      $("fDest").value = button.dataset.plan;
      loadPlaces(button.dataset.plan);
      $("planner").scrollIntoView({ behavior: "smooth" });
    });
  });
}

/* ------------------------------------------------------------------ places */

async function loadPlaces(destinationId) {
  const box = $("placesList");
  // Every path below except the grid itself writes a single line of text, so
  // drop the grid class first rather than leaving one message stretched across
  // a photo layout from the previously chosen destination.
  box.classList.remove("place-grid");
  if (!destinationId) {
    box.innerHTML = `<span class="muted">Choose a destination first.</span>`;
    refreshPlaceControls();
    return;
  }

  box.innerHTML = `<span class="muted">Loading places…</span>`;
  refreshPlaceControls();
  try {
    const { destination } = await api(`/api/destinations/${destinationId}/`);
    const places = destination.places || [];

    if (!places.length) {
      box.innerHTML = `<span class="muted">No places listed for this destination.</span>`;
      refreshPlaceControls();
      return;
    }

    box.classList.remove("muted");
    box.classList.add("place-grid");
    box.innerHTML = places
      .map(
        (p) => `
        <label class="place-card">
          <input type="checkbox" name="place" value="${esc(p.id)}">
          ${photo(p.image, p.name, "place-media") ||
            `<span class="place-media place-media-empty" aria-hidden="true">📍</span>`}
          <span class="place-body">
            <span class="place-name">${esc(p.name)}</span>
            <span class="place-meta">
              <span class="place-tag">${esc(p.category_label || p.category || "")}</span>
              <span>${
                Number(p.entry_fee) > 0 ? rupees(p.entry_fee) : "Free entry"
              }</span>
              ${
                p.visit_duration_minutes
                  ? `<span>~${Math.round(p.visit_duration_minutes / 60 * 10) / 10} h</span>`
                  : ""
              }
            </span>
          </span>
          <span class="place-tick" aria-hidden="true">✓</span>
        </label>`
      )
      .join("");
  } catch (error) {
    box.innerHTML = `<span class="muted">Could not load places: ${esc(error.message)}</span>`;
  }
  refreshPlaceControls();
  // A new destination means new places and none of them chosen, so the entry
  // fees in the running total are stale until it is recomputed.
  scheduleLiveCost();
}

/* ------------------------------------------------------- place selection

   "Select all" is the shortcut most people want: a destination has a handful
   of places and seeing what the whole lot costs is the usual first question.
   Everything below reads and writes the checkboxes themselves, so the count,
   the buttons and the form can never disagree about what is selected.
   -------------------------------------------------------------------------- */

const placeBoxes = () => [...document.querySelectorAll('input[name="place"]')];

/** Keep the count line and the two buttons in step with the checkboxes. */
function refreshPlaceControls() {
  const boxes = placeBoxes();
  const chosen = boxes.filter((box) => box.checked).length;

  $("placesCount").textContent = !boxes.length
    ? "No places to choose from"
    : chosen === 0
    ? `None of ${boxes.length} chosen — the cost will cover travel, hotel and food only`
    : chosen === boxes.length
    ? `All ${boxes.length} places chosen`
    : `${chosen} of ${boxes.length} places chosen`;

  // Nothing to select, or everything already is: the button would do nothing.
  $("selectAllPlaces").disabled = !boxes.length || chosen === boxes.length;
  $("clearPlaces").disabled = chosen === 0;
}

function setAllPlaces(checked) {
  placeBoxes().forEach((box) => {
    box.checked = checked;
  });
  refreshPlaceControls();
  // Ticking boxes in code fires no change event, so ask for the recount here.
  scheduleLiveCost();
}

/* --------------------------------------------------------------- calculate */

function drawResults(data) {
  const labels = {
    travel_cost: "Travel",
    hotel_cost: "Hotel",
    food_cost: "Food",
    local_transport_cost: "Local transport",
    activity_cost: "Activities & entry fees",
    other_cost: "Other (8% buffer)",
  };

  $("costRows").innerHTML = Object.entries(labels)
    .map(([key, label]) => `<tr><th>${label}</th><td>${rupees(data.costs[key])}</td></tr>`)
    .join("");

  $("costTotal").textContent = rupees(data.costs.total_cost);
  $("perPerson").textContent = `That is ${rupees(data.details.per_person)} per person.`;

  $("factDistance").textContent = `${data.distance_km} km each way`;
  $("factHours").textContent = `${data.travel_hours} hours`;
  $("factUnits").textContent = data.details.vehicles_or_tickets;
  $("factRooms").textContent = `${data.details.rooms} for ${data.details.nights} nights`;

  const warn = $("distanceWarn");
  if (data.distance_is_known) {
    warn.hidden = true;
  } else {
    warn.hidden = false;
    warn.textContent =
      "That city pair is not in the distance table, so 250 km was assumed. " +
      "Treat the travel cost as a rough guide.";
  }

  $("itinerary").innerHTML = data.itinerary
    .map(
      (day) => `
      <li>
        <h4>${esc(day.title)}</h4>
        <ul>${day.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>
      </li>`
    )
    .join("");

  $("disclaimer").textContent = data.disclaimer;
  $("results").hidden = false;
}

/**
 * The form as the API wants it. One reader, so the running total and the full
 * plan can never be costing two different trips.
 */
function formPayload() {
  return {
    source: $("fSource").value.trim(),
    destination_id: Number($("fDest").value),
    travelers: Number($("fTravelers").value),
    days: Number($("fDays").value),
    transportation_id: Number($("fTransport").value),
    hotel_category: $("fHotel").value,
    food_budget: $("fFood").value,
    activity_budget: $("fActivity").value || "0",
    place_ids: [...document.querySelectorAll('input[name="place"]:checked')].map(
      (input) => input.value
    ),
  };
}

async function calculate(event) {
  event.preventDefault();

  const button = $("calcBtn");
  const note = $("calcNote");
  button.disabled = true;
  note.textContent = "Calculating…";

  const body = formPayload();

  try {
    const data = await api("/api/calculate-cost/", {
      method: "POST",
      body: JSON.stringify(body),
    });
    drawResults(data);
    note.textContent = "";
    $("results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    note.textContent = error.message;
    note.className = "error-text";
  } finally {
    button.disabled = false;
  }
}

/* ------------------------------------------------------ running total

   The cost of a choice should be visible when the choice is made, not after
   a trip through a button. Every change to the form re-costs the trip.

   Three things this has to get right:

     - the arithmetic stays on the server. Recomputing it here would mean two
       implementations of the same pricing, and they would drift.
     - typing must not fire a request per keystroke, so changes are debounced.
     - replies can arrive out of order on a sleepy free-tier backend, so each
       request carries a sequence number and a stale one is discarded rather
       than allowed to overwrite a newer total.
   -------------------------------------------------------------------------- */

const LIVE_LINES = {
  travel_cost: "Travel",
  hotel_cost: "Hotel",
  food_cost: "Food",
  local_transport_cost: "Local transport",
  activity_cost: "Places & activities",
  other_cost: "Buffer (8%)",
};

let liveTimer = null;
let liveSeq = 0;

function liveMessage(text) {
  $("liveLines").innerHTML = `<span class="live-cost-hint">${esc(text)}</span>`;
  $("liveTotal").textContent = "—";
  $("livePerPerson").textContent = "";
}

function scheduleLiveCost() {
  clearTimeout(liveTimer);
  liveTimer = setTimeout(updateLiveCost, 400);
}

async function updateLiveCost() {
  const body = formPayload();

  // The two selects are filled from the API, so on a cold load they are empty
  // for a moment. Asking to cost a trip with no destination just earns a 400.
  if (!body.destination_id || !body.transportation_id) {
    liveMessage("Choose a destination to see the running total.");
    return;
  }

  const seq = ++liveSeq;
  $("liveCost").classList.add("is-updating");

  try {
    const data = await api("/api/calculate-cost/", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (seq !== liveSeq) return; // a newer request has already been sent

    const chosen = body.place_ids.length;
    $("liveLines").innerHTML = Object.entries(LIVE_LINES)
      .map(([key, label]) => {
        const name = key === "activity_cost" && chosen ? `${label} (${chosen})` : label;
        return `<span class="live-line"><span>${esc(name)}</span><b>${rupees(
          data.costs[key]
        )}</b></span>`;
      })
      .join("");

    $("liveTotal").textContent = rupees(data.costs.total_cost);
    $("livePerPerson").textContent = `${rupees(data.details.per_person)} per person`;
  } catch (error) {
    if (seq !== liveSeq) return;
    liveMessage(error.message);
  } finally {
    if (seq === liveSeq) $("liveCost").classList.remove("is-updating");
  }
}

/* ------------------------------------------------------------------- start */

async function start() {
  $("apiOrigin").textContent = "API: " + API;
  $("backendLink").href = API;

  // Account pages live on the Django site, so they are built from whatever the
  // API base happens to be - that keeps them working against a local backend
  // opened with ?api=http://127.0.0.1:8000 as well as against Render.
  $("signInLink").href = API + "/login/";
  $("registerLink").href = API + "/register/";
  $("forgotLink").href = API + "/password-reset/";

  // The Render free plan sleeps when idle, and the first request after that
  // can take the best part of a minute. Say so rather than looking broken.
  const slow = setTimeout(() => {
    banner(
      "Waking the backend up - the free Render instance sleeps when idle, " +
        "so this first request can take up to a minute.",
      "info"
    );
  }, 2500);

  try {
    const [dests, transport] = await Promise.all([
      api("/api/destinations/"),
      api("/api/transportation/"),
    ]);
    clearTimeout(slow);
    hideBanner();

    DESTINATIONS = dests.results;
    drawDestinations(DESTINATIONS);

    $("fDest").innerHTML = DESTINATIONS.map(
      (d) => `<option value="${esc(d.id)}">${esc(d.name)}</option>`
    ).join("");

    $("fTransport").innerHTML = transport.results
      .map((t) => `<option value="${esc(t.id)}">${esc(t.name)}</option>`)
      .join("");

    if (DESTINATIONS.length) loadPlaces(DESTINATIONS[0].id);
    scheduleLiveCost();
  } catch (error) {
    clearTimeout(slow);
    banner(`Could not reach the API at ${API} - ${error.message}`, "error");
    $("destGrid").innerHTML = `<p class="muted">Destinations unavailable.</p>`;
  }
}

$("planForm").addEventListener("submit", calculate);
$("fDest").addEventListener("change", (e) => loadPlaces(e.target.value));

$("selectAllPlaces").addEventListener("click", () => setAllPlaces(true));
$("clearPlaces").addEventListener("click", () => setAllPlaces(false));

// Delegated, because the checkboxes are replaced every time the destination
// changes - a listener bound to each one would die with it.
$("placesList").addEventListener("change", (event) => {
  if (event.target.name === "place") refreshPlaceControls();
});

// Anything that can change the price re-costs the trip. "input" covers typing
// and the number steppers; "change" covers the selects and the checkboxes.
$("planForm").addEventListener("input", scheduleLiveCost);
$("planForm").addEventListener("change", scheduleLiveCost);
$("destSearch").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  drawDestinations(
    DESTINATIONS.filter(
      (d) =>
        !q ||
        d.name.toLowerCase().includes(q) ||
        (d.state || "").toLowerCase().includes(q)
    )
  );
});

start();
