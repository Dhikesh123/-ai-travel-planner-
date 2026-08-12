/*
 * Admin portal.
 *
 * Unlike the customer portal, every call here is authenticated: the browser
 * must send the Django session cookie to a different origin. That needs
 * three things to line up, and all three are easy to get wrong:
 *
 *   1. every fetch uses credentials: "include"
 *   2. the API answers with Access-Control-Allow-Credentials: true
 *   3. writes carry the CSRF token in an X-CSRFToken header
 */
const API = window.API_BASE.replace(/\/+$/, "");
const $ = (id) => document.getElementById(id);

/* ---------------------------------------------------------------- helpers */

function esc(text) {
  const d = document.createElement("div");
  d.textContent = text == null ? "" : String(text);
  return d.innerHTML;
}

function rupees(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return "Rs " + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function whenever(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString("en-IN");
}

function banner(message, kind = "error") {
  $("apiStatusText").textContent = message;
  $("apiStatus").className = "api-status api-status-" + kind;
  $("apiStatus").hidden = false;
}

/** Read a cookie the API set on this browser. */
function cookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="))
    ?.split("=")[1];
}

/**
 * Every request carries the session cookie. Without credentials: "include"
 * the browser silently omits it on a cross-origin call and the API would
 * treat a signed-in admin as an anonymous visitor.
 */
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  const token = cookie("csrftoken");
  if (token && options.method && options.method !== "GET") {
    headers["X-CSRFToken"] = token;
  }

  const response = await fetch(API + path, {
    credentials: "include",
    ...options,
    headers,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    throw Object.assign(new Error(`The API returned ${response.status}.`), {
      status: response.status,
    });
  }

  if (!response.ok || data.ok === false) {
    throw Object.assign(new Error(data.error || `The API returned ${response.status}.`), {
      status: response.status,
    });
  }
  return data;
}

/* ------------------------------------------------------------------ views */

function showLogin(message) {
  $("dashView").hidden = true;
  $("loginView").hidden = false;
  $("signOut").hidden = true;
  if (message) {
    $("loginError").textContent = message;
    $("loginError").hidden = false;
  }
}

function showDashboard() {
  $("loginView").hidden = true;
  $("dashView").hidden = false;
  $("signOut").hidden = false;
}

/* -------------------------------------------------------------- rendering */

function drawStats(data) {
  const tiles = [
    ["Customers", data.totals.customers],
    ["Trips booked", data.totals.trips],
    ["Total value", rupees(data.totals.value)],
    ["Destinations", data.totals.destinations],
    ["Tourist places", data.totals.places],
    ["Chat messages", data.totals.chats],
    ["Images analysed", data.totals.images],
  ];

  $("statGrid").innerHTML = tiles
    .map(
      ([label, value]) => `
      <div class="stat">
        <span class="stat-value">${esc(value)}</span>
        <span class="stat-label">${esc(label)}</span>
      </div>`
    )
    .join("");

  const popular = data.popular_destinations || [];
  $("popularEmpty").hidden = popular.length > 0;
  $("popularRows").innerHTML = popular
    .map((d) => `<tr><td>${esc(d.name)}</td><td>${esc(d.trip_count)}</td></tr>`)
    .join("");

  const customers = data.recent_customers || [];
  $("customersEmpty").hidden = customers.length > 0;
  $("customerRows").innerHTML = customers
    .map(
      (u) => `<tr><td>${esc(u.username)}</td><td>${esc(whenever(u.date_joined))}</td></tr>`
    )
    .join("");

  const trips = data.recent_trips || [];
  $("tripsEmpty").hidden = trips.length > 0;
  $("tripRows").innerHTML = trips
    .map(
      (t) => `
      <tr>
        <td>${esc(t.username)}</td>
        <td>${esc(t.destination)}</td>
        <td>${esc(whenever(t.travel_date))}</td>
        <td>${esc(t.travelers)}</td>
        <td>${esc(t.days)}</td>
        <td>${esc(rupees(t.total_cost))}</td>
      </tr>`
    )
    .join("");
}

async function loadDashboard() {
  const data = await api("/api/admin/stats/");
  drawStats(data);
  showDashboard();
}

/* ------------------------------------------------------------------ login */

async function signIn(event) {
  event.preventDefault();
  const button = $("loginBtn");
  $("loginError").hidden = true;
  button.disabled = true;
  button.textContent = "Signing in…";

  try {
    // Ask for the CSRF cookie first: Django only sets it once something has
    // touched a view, and the login POST needs it to be there already.
    await api("/api/destinations/").catch(() => {});

    const user = await api("/api/login/", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });

    if (!user.user.is_staff) {
      // Signed in fine, but this account may not see the figures.
      await api("/api/logout/", { method: "POST" }).catch(() => {});
      showLogin("That account is not a staff account, so it cannot open the admin portal.");
      return;
    }

    $("whoami").textContent = `Signed in as ${user.user.username}`;
    await loadDashboard();
  } catch (error) {
    showLogin(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Sign in";
  }
}

async function signOut(event) {
  event.preventDefault();
  try {
    await api("/api/logout/", { method: "POST" });
  } catch {
    /* signing out locally is what matters */
  }
  location.reload();
}

/* ------------------------------------------------------------------ start */

async function start() {
  $("apiOrigin").textContent = "API: " + API;

  const slow = setTimeout(
    () => banner("Waking the backend up — the free Render instance sleeps when idle.", "info"),
    2500
  );

  try {
    // Already signed in from a previous visit?
    const me = await api("/api/me/");
    clearTimeout(slow);
    $("apiStatus").hidden = true;

    if (me.user.is_staff) {
      $("whoami").textContent = `Signed in as ${me.user.username}`;
      await loadDashboard();
    } else {
      showLogin("That account is not a staff account.");
    }
  } catch (error) {
    clearTimeout(slow);
    if (error.status === 401 || error.status === 403) {
      $("apiStatus").hidden = true;
      showLogin();
    } else {
      banner(`Could not reach the API at ${API} — ${error.message}`);
      showLogin();
    }
  }
}

$("loginForm").addEventListener("submit", signIn);
$("signOut").addEventListener("click", signOut);

start();
