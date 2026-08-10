/* ==========================================================================
   Trip detail page: ask the AI to review this saved trip.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const button = document.getElementById("suggestBtn");
  if (!button) return;

  const box = document.getElementById("suggestionBox");

  button.addEventListener("click", async function () {
    const tripId = button.dataset.trip;

    button.disabled = true;
    button.textContent = "Asking the AI...";
    box.hidden = false;
    box.innerHTML = '<p class="muted small">The AI is reading your trip plan...</p>';

    const data = await postJSON(`/api/trips/${tripId}/suggestions/`, {});

    button.disabled = false;
    button.textContent = "Get AI suggestions for this trip";

    if (!data.ok) {
      box.innerHTML = `<p class="field-error">${escapeHtml(
        data.error || "Could not get suggestions. Please try again."
      )}</p>`;
      return;
    }
    box.textContent = data.suggestion;
  });
});
