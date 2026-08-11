/* ==========================================================================
   Shared helpers used by every page.
   ========================================================================== */

/**
 * Send JSON to our Django API.
 * The CSRF token is required by Django for every POST - it proves the request
 * really came from our own page and not from another website.
 */
async function postJSON(url, data) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.CSRF_TOKEN,
    },
    body: JSON.stringify(data),
  });
  return readResponse(response);
}

/** Send a file (multipart form) to our Django API. */
async function postForm(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": window.CSRF_TOKEN },
    body: formData,
  });
  return readResponse(response);
}

/** Turn any server reply into { ok, ...data } and never throw on HTTP errors. */
async function readResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch (err) {
    return { ok: false, error: "The server sent an unexpected reply. Please try again." };
  }
  if (!response.ok && data.ok === undefined) {
    data.ok = false;
    data.error = data.error || data.detail || "Something went wrong. Please try again.";
  }
  return data;
}

/** Format a number as Indian rupees, e.g. 8500 -> "Rs 8,500". */
function formatRupees(value) {
  const number = Number(value || 0);
  return "Rs " + number.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

/** Show an error message inside an element, or hide it when message is empty. */
function showError(element, message) {
  if (!element) return;
  if (message) {
    element.textContent = message;
    element.hidden = false;
  } else {
    element.textContent = "";
    element.hidden = true;
  }
}

/** Wait until the user stops typing before running a function. */
function debounce(fn, wait) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}

/** Escape text so it is safe to put inside HTML. */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

// Mobile navigation toggle
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", () => links.classList.toggle("open"));
  }
});
