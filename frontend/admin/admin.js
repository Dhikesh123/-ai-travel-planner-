/*
 * Admin portal.
 *
 * Unlike the customer portal, every call here is authenticated - and it
 * authenticates with a TOKEN, not the session cookie the Django site uses.
 *
 * The reason is that the frontend and the API sit on different registrable
 * domains (vercel.app and onrender.com), which makes the session cookie a
 * third-party cookie. Chrome and Safari block those by default now, whatever
 * SameSite says, so a cookie-based sign-in here fails for most visitors with
 * a 403 that looks like a bug. A token travels in the Authorization header
 * instead, so none of that applies.
 *
 * The token is kept in sessionStorage rather than localStorage so it dies
 * with the tab instead of lingering on a shared machine.
 */
const API = window.API_BASE.replace(/\/+$/, "");
const $ = (id) => document.getElementById(id);

const TOKEN_KEY = "travelAdminToken";
const getToken = () => sessionStorage.getItem(TOKEN_KEY);
const setToken = (t) => sessionStorage.setItem(TOKEN_KEY, t);
const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

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

/**
 * Every authenticated request carries the token in an Authorization header.
 * No cookies are involved, so there is nothing for a browser's third-party
 * cookie rules to block and no CSRF token to chase.
 */
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  const token = getToken();
  if (token) headers["Authorization"] = "Token " + token;

  const response = await fetch(API + path, { ...options, headers });

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

/*
 * The console rail lists the dashboard's sections, so it is meaningless on the
 * sign-in screen - it moves with the dashboard rather than standing on its own.
 */
function showLogin(message) {
  $("dashView").hidden = true;
  $("loginView").hidden = false;
  $("signOut").hidden = true;
  $("consoleRail").hidden = true;
  if (message) {
    $("loginError").textContent = message;
    $("loginError").hidden = false;
  }
}

function showDashboard() {
  $("loginView").hidden = true;
  $("dashView").hidden = false;
  $("signOut").hidden = false;
  $("consoleRail").hidden = false;
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
    clearToken();

    const result = await api("/api/login/", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });

    if (!result.user.is_staff) {
      // The password was right, but this account may not see the figures.
      showLogin("That account is not a staff account, so it cannot open the admin portal.");
      return;
    }

    setToken(result.token);
    $("whoami").textContent = `Signed in as ${result.user.username}`;
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
    /* the token is dropped below regardless, which is what matters here */
  }
  clearToken();
  location.reload();
}

/* ------------------------------------------------------------------ start */

async function start() {
  $("apiOrigin").textContent = "API: " + API;
  // Just the host in the rail - the full URL is already in the footer. A bad
  // ?api= override must not take the whole page down, hence the guard.
  try {
    $("railApi").textContent = new URL(API).host;
  } catch {
    $("railApi").textContent = API;
  }

  // No token yet means nobody has signed in on this tab, which is the normal
  // first visit - show the form without pestering the API for a 403 first.
  if (!getToken()) {
    showLogin();
    return;
  }

  const slow = setTimeout(
    () => banner("Waking the backend up — the free Render instance sleeps when idle.", "info"),
    2500
  );

  try {
    const me = await api("/api/me/");
    clearTimeout(slow);
    $("apiStatus").hidden = true;

    if (me.user.is_staff) {
      $("whoami").textContent = `Signed in as ${me.user.username}`;
      await loadDashboard();
    } else {
      clearToken();
      showLogin("That account is not a staff account.");
    }
  } catch (error) {
    clearTimeout(slow);
    if (error.status === 401 || error.status === 403) {
      // A stale token from an earlier session, or one revoked by signing out.
      clearToken();
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
