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
  let listening = false;
  let restartInNewLanguage = false;
  let lastTranslation = "";

  // Only warn if there is NO way at all to use the microphone. If the browser
  // cannot listen by itself we can still record and let the server do it.
  const banner = document.getElementById("speechSupport");
  if (!Speech.canCapture()) {
    if (banner) banner.hidden = false;
  } else if (!Speech.isSecureContext()) {
    // The microphone is blocked on plain http, which is what happens when the
    // site is opened by its network address instead of 127.0.0.1.
    if (banner) {
      banner.textContent =
        "The microphone only works on a secure page. Open this site as http://127.0.0.1:8000/ (or over https) to speak. You can still type and translate.";
      banner.hidden = false;
    }
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
  const MIC_IDLE_LABEL = "&#127908; Start listening";
  const MIC_BUSY_LABEL = "&#9209; Stop listening";

  async function startListening() {
    showError(errorBox, "");

    // Say something useful before the browser fails with a cryptic error.
    if ((await Speech.permissionState()) === "denied") {
      showError(
        errorBox,
        "Microphone permission is blocked for this site. Click the padlock in the address bar, allow the microphone, then reload this page."
      );
      return;
    }

    // Never listen to ourselves reading the last answer aloud.
    Speech.stopSpeaking();

    listening = true;
    micBtn.classList.add("mic-active");
    micBtn.innerHTML = MIC_BUSY_LABEL;
    micStatus.textContent = "Starting the microphone...";

    capture = Speech.startCapture({
      lang: sourceLang.value,
      onText: (text) => {
        sourceText.value = sourceText.value ? sourceText.value + " " + text : text;
        micStatus.textContent = "Got it - keep speaking, or click stop.";
      },
      // Words heard so far, before the browser has settled on them. Showing
      // these is how the user knows the microphone is really working.
      onInterim: (text) => {
        micStatus.textContent = "Hearing: " + text;
      },
      onStatus: (message) => {
        micStatus.textContent = message;
      },
      onError: (message) => {
        showError(errorBox, message);
        micStatus.textContent = "";
      },
      onEnd: () => {
        listening = false;
        capture = null;
        micBtn.classList.remove("mic-active");
        micBtn.innerHTML = MIC_IDLE_LABEL;
        // Only a language change asks for this: pick the microphone straight
        // back up so the user never has to press start again themselves.
        if (restartInNewLanguage) {
          restartInNewLanguage = false;
          startListening();
        }
      },
    });

    // If the capture already finished during startCapture, onEnd has run and
    // this controller is spent - drop it so the next click starts fresh.
    if (!listening) capture = null;
  }

  micBtn.addEventListener("click", function () {
    // "listening" is the truth about the microphone, not "capture". A capture
    // can finish the instant it starts (permission blocked, for example), and
    // then its controller is already dead - checking "capture" instead would
    // leave the button stuck on stop and the microphone would never open again.
    if (listening) {
      if (capture) capture.stop(); // the only thing that ends listening
      return;
    }
    startListening();
  });

  // The recogniser cannot change language mid-session, so swap it out and
  // carry on listening. The button stays on stop, because the user has not
  // pressed it.
  sourceLang.addEventListener("change", function () {
    if (!listening || !capture) return;
    restartInNewLanguage = true;
    micStatus.textContent = "Switching to " + (sourceLang.value === "te" ? "Telugu" : "English") + "...";
    capture.stop();
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

    // The answer is shown as it is written, so the first words appear in
    // about a second instead of after the whole itinerary is finished.
    const data = await postChatStream({ message: message }, (answerSoFar) => {
      aiBox.textContent = answerSoFar;
    });

    if (!data.ok) {
      // Keep whatever did arrive - half an answer beats losing it.
      if (!data.reply) aiBox.innerHTML = '<p class="muted small">No answer.</p>';
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
