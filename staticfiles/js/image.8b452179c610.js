/* ==========================================================================
   Image recognition page: choose a photo, send it to the AI, show the answer.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("imageForm");
  if (!form) return;

  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("imageInput");
  const preview = document.getElementById("preview");
  const dropText = document.getElementById("dropText");
  const question = document.getElementById("questionInput");
  const button = document.getElementById("analyseBtn");
  const resultBox = document.getElementById("resultBox");
  const errorBox = document.getElementById("imageError");
  const uncertain = document.getElementById("uncertainNote");
  const speakBtn = document.getElementById("speakResult");

  const MAX_MB = 5;
  const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];

  // ---------------------------------------------------------------------
  // Choosing a file (click or drag and drop)
  // ---------------------------------------------------------------------
  dropzone.addEventListener("click", () => input.click());

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("drag");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("drag");
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      handleFile();
    }
  });

  input.addEventListener("change", handleFile);

  function handleFile() {
    const file = input.files[0];
    if (!file) return;

    // Check the file BEFORE uploading, so the customer gets a fast answer
    if (!ALLOWED.includes(file.type)) {
      showError(errorBox, "Unsupported image type. Please use JPG, PNG, WEBP or GIF.");
      reset();
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      showError(errorBox, `That image is too large. Please use a file under ${MAX_MB} MB.`);
      reset();
      return;
    }

    showError(errorBox, "");
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    dropText.hidden = true;
  }

  function reset() {
    input.value = "";
    preview.hidden = true;
    dropText.hidden = false;
  }

  // ---------------------------------------------------------------------
  // Sending the photo to the server
  // ---------------------------------------------------------------------
  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (!input.files[0]) {
      showError(errorBox, "Please choose an image first.");
      return;
    }

    showError(errorBox, "");
    uncertain.hidden = true;
    speakBtn.hidden = true;
    button.disabled = true;
    button.textContent = "Looking at your photo...";
    resultBox.innerHTML = '<p class="muted small">The AI is analysing the image...</p>';

    const formData = new FormData();
    formData.append("image", input.files[0]);
    formData.append("question", question.value || "");

    const data = await postForm("/api/image-recognition/", formData);

    button.disabled = false;
    button.textContent = "Identify this place";

    if (!data.ok) {
      resultBox.innerHTML = '<p class="muted small">No result.</p>';
      showError(errorBox, data.error || "Could not analyse the image. Please try again.");
      return;
    }

    resultBox.textContent = data.result;

    // The caveat is shown either way, only worded differently. The model has
    // answered HIGH while naming a monument in the wrong state, so treating
    // its own confidence as a reason to say nothing would pass that straight
    // on to the customer as fact.
    uncertain.hidden = false;
    uncertain.className = data.is_confident
      ? "alert alert-warning small"
      : "alert alert-error small";
    uncertain.innerHTML = data.is_confident
      ? "This is the AI's <strong>best guess</strong>. It identifies buildings " +
        "from their appearance alone, and similar-looking monuments are easy " +
        "to confuse - check the name before relying on it."
      : "The AI is <strong>not confident</strong> about this image. Treat the " +
        "answer below as a guess, not a fact.";

    speakBtn.hidden = false;
  });

  // ---------------------------------------------------------------------
  // Read the answer aloud
  // ---------------------------------------------------------------------
  speakBtn.addEventListener("click", function () {
    if (!Speech.speak(resultBox.innerText, "en")) {
      showError(errorBox, "This browser cannot read text aloud.");
    }
  });
});
