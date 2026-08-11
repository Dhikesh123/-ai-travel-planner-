/* ==========================================================================
   Live trip cost calculator.
   Used by BOTH the planner page and the standalone calculator page.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const source = document.getElementById("id_source");
  const destination = document.getElementById("id_destination");
  const travelers = document.getElementById("id_travelers");
  const days = document.getElementById("id_days");
  const transportation = document.getElementById("id_transportation");
  const hotel = document.getElementById("id_hotel_category");
  const food = document.getElementById("id_food_budget");
  const activity = document.getElementById("id_activity_budget");

  const placesGrid = document.getElementById("placesGrid");
  const placesHint = document.getElementById("placesHint");
  const errorBox = document.getElementById("calcError");

  if (!destination || !transportation) return; // not on a calculator page

  // ---------------------------------------------------------------------
  // If a destination id was passed in the URL (?destination=3), select it
  // ---------------------------------------------------------------------
  const urlDestination = new URLSearchParams(window.location.search).get("destination");
  if (urlDestination) {
    const option = destination.querySelector(`option[value="${urlDestination}"]`);
    if (option) destination.value = urlDestination;
  }

  // ---------------------------------------------------------------------
  // Show only the tourist places that belong to the chosen destination
  // ---------------------------------------------------------------------
  function showPlacesForDestination() {
    const chosen = destination.value;

    if (window.CALCULATOR_MODE) {
      loadPlacesFromApi(chosen);
      return;
    }

    let visible = 0;
    placesGrid.querySelectorAll(".place-option").forEach((option) => {
      const matches = option.dataset.destination === chosen;
      option.hidden = !matches;
      if (!matches) {
        const box = option.querySelector("input");
        if (box) box.checked = false;
      } else {
        visible += 1;
      }
    });

    if (placesHint) {
      placesHint.textContent = visible
        ? `Tick the places you want to visit (${visible} available).`
        : "No tourist places listed for this destination yet.";
    }
  }

  // The standalone calculator has no places in the HTML, so fetch them.
  async function loadPlacesFromApi(destinationId) {
    if (!destinationId) return;
    placesGrid.innerHTML = "";
    if (placesHint) placesHint.textContent = "Loading places...";

    const data = await fetch(`/api/destinations/${destinationId}/`).then((r) => r.json());
    if (!data.ok) {
      if (placesHint) placesHint.textContent = "Could not load places.";
      return;
    }

    const places = data.destination.places || [];
    places.forEach((place) => {
      const label = document.createElement("label");
      label.className = "place-option";
      label.innerHTML = `
        <input type="checkbox" name="places" value="${place.id}">
        <span class="place-body">
          <strong>${escapeHtml(place.name)}</strong>
          <span class="muted small">${escapeHtml(place.category_label)} &middot;
            ${Number(place.entry_fee) > 0
              ? "entry ~ " + formatRupees(place.entry_fee) + " (est.)"
              : "free"}</span>
        </span>`;
      label.querySelector("input").addEventListener("change", calculate);
      placesGrid.appendChild(label);
    });

    if (placesHint) {
      placesHint.textContent = places.length
        ? `Tick the places you want to visit (${places.length} available).`
        : "No tourist places listed for this destination yet.";
    }
    calculate();
  }

  // ---------------------------------------------------------------------
  // Ask the server for the cost breakdown and itinerary
  // ---------------------------------------------------------------------
  function selectedPlaceIds() {
    return Array.from(
      placesGrid.querySelectorAll('input[name="places"]:checked')
    ).map((box) => Number(box.value));
  }

  async function calculate() {
    if (!destination.value || !transportation.value) return;

    const payload = {
      source: source ? source.value : "",
      destination_id: destination.value,
      travelers: travelers ? travelers.value : 1,
      days: days ? days.value : 1,
      transportation_id: transportation.value,
      hotel_category: hotel ? hotel.value : "standard",
      food_budget: food ? food.value : "standard",
      activity_budget: activity ? activity.value : 0,
      place_ids: selectedPlaceIds(),
    };

    if (!payload.source || payload.source.trim().length < 2) {
      showError(errorBox, "Enter your starting city to see the estimate.");
      return;
    }

    const data = await postJSON("/api/calculate-cost/", payload);

    if (!data.ok) {
      showError(errorBox, data.error || "Could not calculate the cost.");
      return;
    }
    showError(errorBox, "");
    render(data);
  }

  // ---------------------------------------------------------------------
  // Put the numbers on the page
  // ---------------------------------------------------------------------
  function render(data) {
    const costs = data.costs;
    setText("totalCost", formatRupees(costs.total_cost));
    setText("travelCost", formatRupees(costs.travel_cost));
    setText("hotelCost", formatRupees(costs.hotel_cost));
    setText("foodCost", formatRupees(costs.food_cost));
    setText("localCost", formatRupees(costs.local_transport_cost));
    setText("activityCost", formatRupees(costs.activity_cost));
    setText("otherCost", formatRupees(costs.other_cost));
    setText("perPerson", formatRupees(data.details.per_person) + " per person (estimate)");
    setText("distance", data.distance_km + " km");
    setText("travelTime", Number(data.travel_hours).toFixed(1) + " hrs");

    const warning = document.getElementById("distanceWarning");
    if (warning) warning.hidden = data.distance_is_known;

    const box = document.getElementById("itinerary");
    if (box) {
      box.innerHTML = (data.itinerary || [])
        .map(
          (day) => `
          <div class="day-card">
            <h4>${escapeHtml(day.title)}</h4>
            <ul>${day.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </div>`
        )
        .join("");
    }
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  // ---------------------------------------------------------------------
  // Wire everything up
  // ---------------------------------------------------------------------
  const recalculate = debounce(calculate, 400);

  [source, travelers, days, activity].forEach((field) => {
    if (field) field.addEventListener("input", recalculate);
  });
  [transportation, hotel, food].forEach((field) => {
    if (field) field.addEventListener("change", calculate);
  });
  destination.addEventListener("change", function () {
    showPlacesForDestination();
    calculate();
  });
  if (placesGrid) {
    placesGrid.addEventListener("change", function (event) {
      if (event.target.name === "places") calculate();
    });
  }

  showPlacesForDestination();
  calculate();
});
