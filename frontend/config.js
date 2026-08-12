/*
 * Where the backend lives.
 *
 * This is the one line that connects the frontend to the API. It is kept in
 * its own file, loaded before app.js, so the address can be changed without
 * touching any application code.
 *
 * Override it for local development by opening the site with ?api=... on the
 * URL, e.g. index.html?api=http://127.0.0.1:8000 - handy for pointing the
 * deployed frontend at a Django running on your own machine.
 */
window.API_BASE =
  new URLSearchParams(location.search).get("api") ||
  "https://ai-travel-planner-esxd.onrender.com";
