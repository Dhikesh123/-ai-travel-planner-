/* ==========================================================================
   Voice assistant page: speak -> text -> translate -> AI answer -> speak.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const sourceText = document.getElementById("sourceText");
  if (!sourceText) return;

  const sourceLang = document.getElementById("sourceLang");
  const targetLang = document.getElementById("targetLang");
  const micBtn = document.getElementById("micBtn");
  const micStatus = document.getElementById("micStatus");
  const translateBtn = document.getElementById("translateBtn");
  const translationBox = document.getElementById("translationBox");
  const aiBox = document.getElementById("aiBox");
  const errorBox = document.getElementById("voiceError");

  let capture = null;
  let lastTranslation = "";

  // Only warn if there is NO way at all to use the microphone. If the browser
  // cannot listen by itself we can still record and let the server do it.
  if (!Speech.canCapture()) {
    const banner = document.getElementById("speechSupport");
    if (banner) banner.hidden = false;
  } else if (!Speech.canListen()) {
    micStatus.textContent =
      "This browser will record your voice and send it to the server to be written out.";
  }

  // Keep the two language boxes from matching each other
  sourceLang.addEventListener("change", function () {
    targetLang.value = sourceLang.value === "te" ? "en" : "te";
  });
  targetLang.addEventListener("change", function () {
    sourceLang.value = targetLang.value === "te" ? "en" : "te";
  });

  // ---------------------------------------------------------------------
  // Microphone
  // ---------------------------------------------------------------------
  micBtn.addEventListener("click", function () {
    if (capture) {
      capture.stop();
      return;
    }
    showError(errorBox, "");
    micBtn.classList.add("mic-active");
    micBtn.textContent = "Click to stop";

    capture = Speech.startCapture({
      lang: sourceLang.value,
      onText: (text) => {
        sourceText.value = sourceText.value ? sourceText.value + " " + text : text;
        micStatus.textContent = "Got it. You can translate now.";
      },
      onStatus: (message) => {
        micStatus.textContent = message;
      },
      onError: (message) => {
        showError(errorBox, message);
        micStatus.textContent = "";
      },
      onEnd: () => {
        capture = null;
        micBtn.classList.remove("mic-active");
        micBtn.innerHTML = "&#127908; Start listening";
      },
    });
  });

  // ---------------------------------------------------------------------
  // Translate
  // ---------------------------------------------------------------------
  translateBtn.addEventListener("click", async function () {
    const text = sourceText.value.trim();
    if (!text) {
      showError(errorBox, "Speak or type something first.");
      return;
    }

    showError(errorBox, "");
    translateBtn.disabled = true;
    translationBox.innerHTML = '<p class="muted small">Translating...</p>';

    const data = await postJSON("/api/translate/", {
      text: text,
      source: sourceLang.value,
      target: targetLang.value,
    });

    translateBtn.disabled = false;

    if (!data.ok) {
      translationBox.innerHTML = '<p class="muted small">Translation failed.</p>';
      showError(errorBox, data.error || "Could not translate. Please try again.");
      return;
    }

    lastTranslation = data.translation;
    translationBox.textContent = data.translation;
  });

  // ---------------------------------------------------------------------
  // Read aloud buttons
  // ---------------------------------------------------------------------
  document.getElementById("speakSource").addEventListener("click", function () {
    speakOrWarn(sourceText.value, sourceLang.value);
  });

  document.getElementById("speakTranslation").addEventListener("click", function () {
    speakOrWarn(lastTranslation, targetLang.value);
  });

  document.getElementById("speakAi").addEventListener("click", function () {
    speakOrWarn(aiBox.innerText, "en");
  });

  function speakOrWarn(text, lang) {
    if (!text || !text.trim()) {
      showError(errorBox, "There is nothing to read aloud yet.");
      return;
    }
    if (lang === "te" && !Speech.hasTeluguVoice()) {
      showError(
        errorBox,
        "Your device does not have a Telugu voice installed, so the text cannot be spoken. The text is still shown above."
      );
      return;
    }
    showError(errorBox, "");
    if (!Speech.speak(text, lang)) {
      showError(errorBox, "This browser cannot read text aloud.");
    }
  }

  // ---------------------------------------------------------------------
  // Send to the AI assistant
  // ---------------------------------------------------------------------
  document.getElementById("askAiBtn").addEventListener("click", async function () {
    // Prefer the English translation - the AI understands both, but this
    // shows the full Telugu -> English -> AI flow working.
    const message = (lastTranslation || sourceText.value).trim();
    if (!message) {
      showError(errorBox, "Speak or type something first.");
      return;
    }

    showError(errorBox, "");
    aiBox.innerHTML = '<p class="muted small">The AI is thinking...</p>';

    const data = await postJSON("/api/chat/", { message: message });

    if (!data.ok) {
      aiBox.innerHTML = '<p class="muted small">No answer.</p>';
      showError(errorBox, data.error || "The assistant could not reply.");
      return;
    }
    aiBox.textContent = data.reply;
  });

  // ---------------------------------------------------------------------
  // Clear
  // ---------------------------------------------------------------------
  document.getElementById("clearAll").addEventListener("click", function () {
    Speech.stopSpeaking();
    sourceText.value = "";
    lastTranslation = "";
    translationBox.innerHTML = '<p class="muted small">Your translation will appear here.</p>';
    aiBox.innerHTML = '<p class="muted small">The AI answer will appear here.</p>';
    micStatus.textContent = "";
    showError(errorBox, "");
  });
});
