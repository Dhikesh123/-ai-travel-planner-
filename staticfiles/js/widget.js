/* ==========================================================================
   The floating assistant in the corner of every page.

   It holds all three AI tools behind three tabs - Chat, Image AI and Voice -
   so they no longer need a nav link each. Every tab talks to exactly the same
   endpoints as the full pages (/api/chat/, /api/image-recognition/,
   /api/translate/), so there is one behaviour to maintain, not two.

   The full pages at /assistant/, /image-recognition/ and /voice/ still work
   for anyone who visits them directly.

   Everything this file needs is looked up FIRST, before a single listener is
   attached. That ordering matters: if a lookup below a listener were to fail,
   the listener would already be live while the consts it depends on were
   still uninitialised, and the panel would open into a dead, empty box.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  // ---------------------------------------------------------------------
  // Everything we touch, resolved up front
  // ---------------------------------------------------------------------
  const fab = document.getElementById("chatFab");
  const panel = document.getElementById("chatWidget");
  if (!fab || !panel) return; // not shown when logged out

  const closeBtn = document.getElementById("widgetClose");
  const tabs = Array.from(panel.querySelectorAll(".widget-tab"));
  const panels = Array.from(panel.querySelectorAll(".widget-panel"));

  // Chat
  const messages = document.getElementById("widgetMessages");
  const chatForm = document.getElementById("widgetForm");
  const chatInput = document.getElementById("widgetInput");
  const chatSend = document.getElementById("widgetSend");

  // Image AI
  const drop = document.getElementById("wDrop");
  const imageInput = document.getElementById("wImageInput");
  const preview = document.getElementById("wPreview");
  const dropText = document.getElementById("wDropText");
  const imageQuestion = document.getElementById("wImageQuestion");
  const analyseBtn = document.getElementById("wAnalyse");
  const imageResult = document.getElementById("wImageResult");
  const imageNote = document.getElementById("wImageNote");
  const imageError = document.getElementById("wImageError");

  // Voice
  const sourceLang = document.getElementById("wSourceLang");
  const targetLang = document.getElementById("wTargetLang");
  const micBtn = document.getElementById("wMic");
  const micStatus = document.getElementById("wMicStatus");
  const sourceText = document.getElementById("wSourceText");
  const translateBtn = document.getElementById("wTranslate");
  const speakBtn = document.getElementById("wSpeak");
  const voiceClear = document.getElementById("wVoiceClear");
  const translationBox = document.getElementById("wTranslationBox");
  const voiceAi = document.getElementById("wVoiceAi");
  const voiceError = document.getElementById("wVoiceError");
  const askAiBtn = document.getElementById("wAskAi");

  const MAX_MB = 5;
  const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];
  const MIC_IDLE = "🎤 Start listening";
  const MIC_BUSY = "⏹ Stop listening";

  const CLOSE_MS = 170; // must match the widgetOut animation in style.css

  let closeTimer = null;
  let capture = null;
  let listening = false;
  let restartInNewLanguage = false;
  let lastTranslation = "";

  // ---------------------------------------------------------------------
  // Small helpers
  // ---------------------------------------------------------------------
  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = "w-bubble w-bubble-" + role;
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  function activeTab() {
    const current = tabs.find((t) => t.classList.contains("is-active"));
    return current ? current.dataset.panel : "panelChat";
  }

  function stopListening() {
    if (listening && capture) capture.stop();
  }

  // ---------------------------------------------------------------------
  // Open and close
  // ---------------------------------------------------------------------
  function openPanel() {
    // Re-opening mid-close cancels the pending hide, so a quick close-then-
    // open never leaves the panel visible but marked closed.
    clearTimeout(closeTimer);
    panel.classList.remove("is-closing");
    panel.hidden = false;
    panel.style.display = ""; // hand control back to the stylesheet
    fab.classList.add("is-open");
    fab.setAttribute("aria-expanded", "true");
    // The greeting is already in the HTML, so there is nothing to add here.
    if (activeTab() === "panelChat") chatInput.focus();
  }

  function closePanel() {
    if (panel.hidden) return;

    fab.classList.remove("is-open");
    fab.setAttribute("aria-expanded", "false");

    // The hide is scheduled FIRST, before anything that could throw. Tidying
    // up the microphone below is worth doing but must never be able to leave
    // the panel stuck open if it fails.
    panel.classList.add("is-closing");
    clearTimeout(closeTimer);
    closeTimer = setTimeout(function () {
      panel.classList.remove("is-closing");
      panel.hidden = true;
      // An inline style outranks every stylesheet rule, so the panel closes
      // even if a browser is still holding an old style.css that lacks the
      // .chat-widget[hidden] rule. `hidden` alone is not enough: the base
      // .chat-widget rule sets display:flex, which beats the browser default.
      panel.style.display = "none";
    }, CLOSE_MS);

    // Never leave the microphone or a voice reading running behind a closed
    // panel - the user has no way to stop it once it is out of sight.
    try {
      stopListening();
      if (typeof Speech !== "undefined") Speech.stopSpeaking();
    } catch (err) {
      /* the panel is already on its way out; nothing here is worth blocking it */
    }
  }

  fab.addEventListener("click", function () {
    if (panel.hidden) openPanel();
    else closePanel();
  });

  closeBtn.addEventListener("click", closePanel);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !panel.hidden) closePanel();
  });

  // ---------------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------------
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      // Switching away from Voice must not leave the microphone open.
      if (tab.dataset.panel !== "panelVoice") stopListening();

      tabs.forEach(function (other) {
        const on = other === tab;
        other.classList.toggle("is-active", on);
        other.setAttribute("aria-selected", on ? "true" : "false");
      });
      panels.forEach(function (p) {
        const on = p.id === tab.dataset.panel;
        p.classList.toggle("is-active", on);
        p.hidden = !on;
      });
      if (tab.dataset.panel === "panelChat") chatInput.focus();
    });
  });

  // =====================================================================
  // Tab 1: Chat
  // =====================================================================
  chatForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    addBubble("user", text);
    chatInput.value = "";
    chatSend.disabled = true;

    const typing = document.createElement("div");
    typing.className = "w-bubble w-bubble-assistant w-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;

    // Streamed, so the first words appear in about a second instead of after
    // the whole itinerary is written. Falls back to /api/chat/ on its own.
    let reply = null;
    const data = await postChatStream({ message: text }, function (answerSoFar) {
      if (typing.parentNode) typing.remove();
      if (!reply) reply = addBubble("assistant", "");
      reply.textContent = answerSoFar;
      messages.scrollTop = messages.scrollHeight;
    });

    if (typing.parentNode) typing.remove();
    chatSend.disabled = false;

    if (!data.ok) {
      // Keep whatever did arrive - half an answer beats losing it.
      if (!reply) {
        const problem = addBubble(
          "assistant",
          data.error || "Sorry, I could not reply just now. Please try again."
        );
        problem.classList.add("w-bubble-error");
      }
      return;
    }
    if (reply) reply.textContent = data.reply;
    else addBubble("assistant", data.reply);
  });

  // Enter sends, Shift+Enter makes a new line
  chatInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      chatForm.requestSubmit();
    }
  });

  // =====================================================================
  // Tab 2: Image AI
  // =====================================================================
  drop.addEventListener("click", () => imageInput.click());

  drop.addEventListener("dragover", function (event) {
    event.preventDefault();
    drop.classList.add("drag");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop.addEventListener("drop", function (event) {
    event.preventDefault();
    drop.classList.remove("drag");
    if (event.dataTransfer.files.length) {
      imageInput.files = event.dataTransfer.files;
      handleFile();
    }
  });

  imageInput.addEventListener("change", handleFile);

  function handleFile() {
    const file = imageInput.files[0];
    if (!file) return;

    // Checked here as well as on the server, so the answer is instant.
    if (!ALLOWED.includes(file.type)) {
      showError(imageError, "Unsupported image type. Please use JPG, PNG, WEBP or GIF.");
      resetImage();
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      showError(imageError, `That image is too large. Please use a file under ${MAX_MB} MB.`);
      resetImage();
      return;
    }

    showError(imageError, "");
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    dropText.hidden = true;
  }

  function resetImage() {
    imageInput.value = "";
    preview.hidden = true;
    dropText.hidden = false;
  }

  analyseBtn.addEventListener("click", async function () {
    if (!imageInput.files[0]) {
      showError(imageError, "Please choose an image first.");
      return;
    }

    showError(imageError, "");
    imageNote.hidden = true;
    analyseBtn.disabled = true;
    analyseBtn.textContent = "Looking at your photo...";
    imageResult.innerHTML = '<p class="muted small">The AI is analysing the image...</p>';

    const formData = new FormData();
    formData.append("image", imageInput.files[0]);
    formData.append("question", imageQuestion.value || "");

    const data = await postForm("/api/image-recognition/", formData);

    analyseBtn.disabled = false;
    analyseBtn.textContent = "Identify this place";

    if (!data.ok) {
      imageResult.innerHTML = '<p class="muted small">No result.</p>';
      showError(imageError, data.error || "Could not analyse the image. Please try again.");
      return;
    }

    imageResult.textContent = data.result;

    // The caveat is shown either way, only worded differently. The model has
    // answered confidently while naming a monument in the wrong state, so its
    // own confidence is not a reason to pass the answer on as fact.
    imageNote.hidden = false;
    imageNote.className = data.is_confident ? "w-note w-note-warn" : "w-note w-note-bad";
    imageNote.innerHTML = data.is_confident
      ? "This is the AI's <strong>best guess</strong> - similar-looking places are easy to confuse."
      : "The AI is <strong>not confident</strong>. Treat this as a guess, not a fact.";
  });

  // =====================================================================
  // Tab 3: Voice
  // =====================================================================

  // Keep the two language boxes from matching each other
  targetLang.addEventListener("change", function () {
    sourceLang.value = targetLang.value === "te" ? "en" : "te";
  });

  async function startListening() {
    showError(voiceError, "");

    if (!Speech.canCapture()) {
      showError(voiceError, "This browser cannot use the microphone. Please type instead.");
      return;
    }
    if (!Speech.isSecureContext()) {
      showError(
        voiceError,
        "The microphone only works on a secure page. Open this site as http://127.0.0.1:8000/ or over https. You can still type and translate."
      );
      return;
    }
    if ((await Speech.permissionState()) === "denied") {
      showError(
        voiceError,
        "Microphone permission is blocked for this site. Click the padlock in the address bar, allow the microphone, then reload."
      );
      return;
    }

    // Never listen to ourselves reading the last answer aloud.
    Speech.stopSpeaking();

    listening = true;
    micBtn.classList.add("mic-active");
    micBtn.textContent = MIC_BUSY;
    micStatus.textContent = "Starting the microphone...";

    capture = Speech.startCapture({
      lang: sourceLang.value,
      onText: function (text) {
        sourceText.value = sourceText.value ? sourceText.value + " " + text : text;
        micStatus.textContent = "Got it - keep speaking, or click stop.";
      },
      onInterim: function (text) {
        micStatus.textContent = "Hearing: " + text;
      },
      onStatus: function (message) {
        micStatus.textContent = message;
      },
      onError: function (message) {
        showError(voiceError, message);
        micStatus.textContent = "";
      },
      onEnd: function () {
        listening = false;
        capture = null;
        micBtn.classList.remove("mic-active");
        micBtn.textContent = MIC_IDLE;
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
    // "listening" is the truth about the microphone, not "capture" - a capture
    // can die the instant it starts (permission blocked), leaving a controller
    // that would strand the button on "stop" forever.
    if (listening) {
      stopListening();
      return;
    }
    startListening();
  });

  // The recogniser cannot change language mid-session, so swap it out and
  // carry on listening. Also keeps the two language boxes from matching.
  sourceLang.addEventListener("change", function () {
    targetLang.value = sourceLang.value === "te" ? "en" : "te";
    if (!listening || !capture) return;
    restartInNewLanguage = true;
    micStatus.textContent =
      "Switching to " + (sourceLang.value === "te" ? "Telugu" : "English") + "...";
    capture.stop();
  });

  translateBtn.addEventListener("click", async function () {
    const text = sourceText.value.trim();
    if (!text) {
      showError(voiceError, "Speak or type something first.");
      return;
    }

    showError(voiceError, "");
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
      showError(voiceError, data.error || "Could not translate. Please try again.");
      return;
    }

    lastTranslation = data.translation;
    translationBox.textContent = data.translation;
  });

  speakBtn.addEventListener("click", function () {
    // Read the translation when there is one, otherwise what was typed.
    const text = (lastTranslation || sourceText.value).trim();
    const lang = lastTranslation ? targetLang.value : sourceLang.value;
    if (!text) {
      showError(voiceError, "There is nothing to read aloud yet.");
      return;
    }
    if (lang === "te" && !Speech.hasTeluguVoice()) {
      showError(
        voiceError,
        "Your device has no Telugu voice installed, so this cannot be spoken. The text is still shown above."
      );
      return;
    }
    showError(voiceError, "");
    if (!Speech.speak(text, lang)) {
      showError(voiceError, "This browser cannot read text aloud.");
    }
  });

  askAiBtn.addEventListener("click", async function () {
    // Prefer the English translation - the AI understands both, but this is
    // the full Telugu -> English -> AI path working end to end.
    const message = (lastTranslation || sourceText.value).trim();
    if (!message) {
      showError(voiceError, "Speak or type something first.");
      return;
    }

    showError(voiceError, "");
    askAiBtn.disabled = true;
    voiceAi.innerHTML = '<p class="muted small">The AI is thinking...</p>';

    const data = await postChatStream({ message: message }, function (answerSoFar) {
      voiceAi.textContent = answerSoFar;
    });

    askAiBtn.disabled = false;

    if (!data.ok) {
      if (!data.reply) voiceAi.innerHTML = '<p class="muted small">No answer.</p>';
      showError(voiceError, data.error || "The assistant could not reply.");
      return;
    }
    voiceAi.textContent = data.reply;
  });

  voiceClear.addEventListener("click", function () {
    Speech.stopSpeaking();
    sourceText.value = "";
    lastTranslation = "";
    translationBox.innerHTML = '<p class="muted small">Your translation will appear here.</p>';
    voiceAi.innerHTML = '<p class="muted small">The AI answer will appear here.</p>';
    micStatus.textContent = "";
    showError(voiceError, "");
  });
});
