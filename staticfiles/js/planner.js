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
  // The places worth offering for THIS journey
  //
  // Not everything in the catalogue, and not even everything at the far end:
  // what is near where you start, what the road passes, and what is around
  // where you are going. The server works that out from the two addresses,
  // so this asks again whenever either of them changes - typing a different
  // starting town changes the answer just as much as choosing another
  // destination does.
  // ---------------------------------------------------------------------
  let latestRequest = 0;   // only the newest answer is allowed to paint

  function setHint(message) {
    if (placesHint) placesHint.textContent = message;
  }

  /** Which boxes are ticked right now, so rebuilding the list keeps them. */
  function tickedIds() {
    return new Set(
      Array.from(placesGrid.querySelectorAll('input[name="places"]:checked'))
        .map((box) => box.value)
    );
  }

  function placeLabel(place, ticked) {
    const fee = Number(place.entry_fee) > 0
      ? "entry ~ " + formatRupees(place.entry_fee) + " (est.)"
      : "free";
    const label = document.createElement("label");
    label.className = "place-option";
    label.innerHTML = `
      <input type="checkbox" name="places" value="${place.id}"
             data-fee="${place.entry_fee}"${ticked.has(String(place.id)) ? " checked" : ""}>
      <span class="place-body">
        <strong>${escapeHtml(place.name)}</strong>
        <span class="muted small">${escapeHtml(place.category_label)} &middot; ${fee}</span>
        ${place.opening_info
          ? `<span class="muted small">${escapeHtml(place.opening_info)}</span>`
          : ""}
      </span>`;
    return label;
  }

  /** Build the same grouped markup the server renders on first paint. */
  function renderGroups(groups, ticked) {
    placesGrid.innerHTML = "";
    let count = 0;

    groups.forEach((group) => {
      const section = document.createElement("div");
      section.className = "place-group";

      const heading = document.createElement("h3");
      heading.className = "place-group-heading";
      heading.textContent = group.heading;
      section.appendChild(heading);

      const note = document.createElement("p");
      note.className = "place-group-note muted small";
      note.textContent = group.note;
      section.appendChild(note);

      group.destinations.forEach((city) => {
        if (!city.places.length) return;

        const name = document.createElement("p");
        name.className = "place-city";
        name.innerHTML = `${escapeHtml(city.name)}${
          city.state ? `<span class="muted"> &middot; ${escapeHtml(city.state)}</span>` : ""
        }`;
        section.appendChild(name);

        const options = document.createElement("div");
        options.className = "place-city-options";
        city.places.forEach((place) => {
          options.appendChild(placeLabel(place, ticked));
          count += 1;
        });
        section.appendChild(options);
      });

      placesGrid.appendChild(section);
    });
    return count;
  }

  async function loadJourneyPlaces() {
    if (!placesGrid) return;

    if (!destination.value) {
      placesGrid.innerHTML = "";
      setHint("Choose where you are going, and the places along the way appear here.");
      return;
    }

    const ticked = tickedIds();
    const mine = ++latestRequest;
    setHint("Finding the places along your journey...");

    const query = new URLSearchParams({
      destination: destination.value,
      source: source ? source.value.trim() : "",
    });

    let data;
    try {
      data = await fetch(`/api/journey-places/?${query}`).then((r) => r.json());
    } catch (error) {
      setHint("Could not load the places for this journey.");
      return;
    }

    // Someone kept typing while this was in flight: that answer is stale.
    if (mine !== latestRequest) return;

    if (!data.ok) {
      setHint(data.error || "Could not load the places for this journey.");
      return;
    }

    const count = renderGroups(data.groups, ticked);
    const typed = source && source.value.trim();

    if (!count) {
      setHint("No tourist places are listed for this journey yet.");
    } else if (typed && !data.source_located) {
      // Being honest about it beats silently showing a shorter list.
      setHint(
        `${count} places to choose from. We could not find "${typed}" on the map, ` +
        "so these are the ones around your destination only."
      );
    } else if (typed) {
      setHint(`${count} places along the way from ${typed}. Tick the ones you want to visit.`);
    } else {
      setHint(`${count} places to choose from. Type where you are starting from to see what is on the way.`);
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
    // Repeated in the sticky action bar. On a narrow screen the estimate panel
    // sits below the whole form, so the total would otherwise be off-screen at
    // the exact moment you are deciding whether to save.
    setText("actionTotal", "Estimated " + formatRupees(costs.total_cost));
    setText("travelCost", formatRupees(costs.travel_cost));
    setText("hotelCost", formatRupees(costs.hotel_cost));
    setText("foodCost", formatRupees(costs.food_cost));
    setText("localCost", formatRupees(costs.local_transport_cost));
    setText("activityCost", formatRupees(costs.activity_cost));
    setText("otherCost", formatRupees(costs.other_cost));
    setText("perPerson", formatRupees(data.details.per_person) + " per person (estimate)");

    // The dashboard tiles and bars. The old table ids above still carry the
    // figures; these add the proportions beside them.
    setText("perPersonValue", formatRupees(data.details.per_person));
    setText("perDayValue", formatRupees(costs.total_cost / Math.max(1, Number(data.details.days) || 1)));
    setText("perPersonNote", (data.details.travelers || 1) + " travelling");
    setText("perDayNote", "over " + (data.details.days || 1) + " days");

    // Share of the total, not of the largest line: the bars are meant to be
    // read against each other and against the whole.
    var total = Number(costs.total_cost) || 0;
    [
      ["travelBar", costs.travel_cost],
      ["hotelBar", costs.hotel_cost],
      ["foodBar", costs.food_cost],
      ["localBar", costs.local_transport_cost],
      ["activityBar", costs.activity_cost],
      ["otherBar", costs.other_cost],
    ].forEach(function (pair) {
      var bar = document.getElementById(pair[0]);
      if (!bar) return;
      bar.style.width = total ? (Number(pair[1]) / total) * 100 + "%" : "0%";
    });
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

  // Changing where you start changes what is on the way, so the place list
  // has to be asked for again. Debounced harder than the cost is: this one
  // reaches a geocoder the first time a town is typed, and there is no sense
  // asking after every letter of "Bhimavaram".
  const reloadJourney = debounce(loadJourneyPlaces, 800);

  [travelers, days, activity].forEach((field) => {
    if (field) field.addEventListener("input", recalculate);
  });
  if (source) {
    source.addEventListener("input", function () {
      recalculate();
      reloadJourney();
    });
  }
  [transportation, hotel, food].forEach((field) => {
    if (field) field.addEventListener("change", calculate);
  });
  destination.addEventListener("change", function () {
    loadJourneyPlaces();
    calculate();
  });
  if (placesGrid) {
    placesGrid.addEventListener("change", function (event) {
      if (event.target.name === "places") calculate();
    });
  }

  // The server has already painted the right groups for whatever the form
  // arrived holding, so only fetch when it could not: no destination chosen
  // yet, or a page (the standalone calculator) that renders none at all.
  if (!placesGrid || !placesGrid.querySelector(".place-option")) {
    loadJourneyPlaces();
  } else {
    setHint(
      `${placesGrid.querySelectorAll(".place-option").length} places along your journey. ` +
      "Tick the ones you want to visit."
    );
  }
  calculate();
});
