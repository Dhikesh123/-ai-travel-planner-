/* ==========================================================================
   Speech helpers - shared by the chatbot, the voice page and image results.

   Turning speech into text can happen in TWO ways, and this file picks the
   best one automatically:

     1. The browser's own SpeechRecognition (Chrome, Edge) - instant, free,
        nothing is sent to our server.
     2. If the browser cannot do that (Safari, Firefox), we record the
        microphone with MediaRecorder and send the audio to our server,
        which passes it to Whisper. Slower, but it works everywhere.

   Speaking text out loud uses the browser's speechSynthesis in both cases.
   ========================================================================== */

const Speech = (function () {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  /** Turn "te" into "te-IN" for the browser recogniser. */
  function fullCode(lang) {
    if (!lang) return "en-IN";
    if (lang.length > 2) return lang;
    return lang === "te" ? "te-IN" : "en-IN";
  }

  /** Turn "te-IN" into "te" for our server. */
  function shortCode(lang) {
    return (lang || "en").slice(0, 2);
  }

  /** Can the browser turn speech into text by itself? */
  function canListen() {
    return Boolean(Recognition);
  }

  /** Can the browser record audio for us to send to the server? */
  function canRecord() {
    return Boolean(
      window.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia
    );
  }

  /** Is there any way at all to capture speech? */
  function canCapture() {
    return canListen() || canRecord();
  }

  /** Does this browser support speaking? */
  function canSpeak() {
    return "speechSynthesis" in window;
  }

  // -----------------------------------------------------------------------
  // Method 1: the browser's own speech recognition
  // -----------------------------------------------------------------------
  function listen({ lang = "en-IN", onResult, onError, onEnd }) {
    if (!canListen()) {
      onError && onError("This browser cannot listen to the microphone.");
      onEnd && onEnd();
      return null;
    }

    const recognition = new Recognition();
    recognition.lang = fullCode(lang);
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onresult = function (event) {
      onResult && onResult(event.results[0][0].transcript);
    };

    recognition.onerror = function (event) {
      const messages = {
        "no-speech": "I did not hear anything. Please try again.",
        "audio-capture": "No microphone found. Please check your device.",
        "not-allowed": "Microphone permission was blocked. Allow it in your browser settings.",
        network: "Speech recognition needs an internet connection.",
        "language-not-supported":
          "This browser has no voice pack for that language. Try English, or type instead.",
      };
      onError && onError(messages[event.error] || "Speech recognition failed. Please type instead.");
    };

    recognition.onend = function () {
      onEnd && onEnd();
    };

    try {
      recognition.start();
    } catch (err) {
      onError && onError("Could not start the microphone. Please try again.");
      onEnd && onEnd();
      return null;
    }
    return recognition;
  }

  // -----------------------------------------------------------------------
  // Method 2: record the microphone and let our server transcribe it
  // -----------------------------------------------------------------------
  async function record({ lang = "en", onText, onError, onStatus, onEnd }) {
    if (!canRecord()) {
      onError && onError("This browser cannot record audio. Please type instead.");
      onEnd && onEnd();
      return null;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const denied = err && (err.name === "NotAllowedError" || err.name === "SecurityError");
      onError && onError(
        denied
          ? "Microphone permission was blocked. Allow it in your browser settings."
          : "No microphone was found. Please check your device."
      );
      onEnd && onEnd();
      return null;
    }

    const chunks = [];
    let recorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch (err) {
      stream.getTracks().forEach((t) => t.stop());
      onError && onError("This browser could not start recording. Please type instead.");
      onEnd && onEnd();
      return null;
    }

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunks.push(event.data);
    };

    recorder.onstop = async function () {
      stream.getTracks().forEach((t) => t.stop()); // release the microphone

      if (!chunks.length) {
        onError && onError("Nothing was recorded. Please try again.");
        onEnd && onEnd();
        return;
      }

      onStatus && onStatus("Sending your recording to be written out...");

      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      const extension = (recorder.mimeType || "audio/webm").includes("ogg") ? "ogg" : "webm";

      const formData = new FormData();
      formData.append("audio", blob, `recording.${extension}`);
      formData.append("language", shortCode(lang));

      const data = await postForm("/api/transcribe/", formData);

      if (!data.ok) {
        onError && onError(data.error || "Could not understand that recording.");
      } else {
        onText && onText(data.text);
      }
      onEnd && onEnd();
    };

    recorder.start();
    onStatus && onStatus("Recording... click again to stop.");
    return recorder;
  }

  // -----------------------------------------------------------------------
  // The one function the pages actually use.
  // It picks the best available method and hides the difference.
  // -----------------------------------------------------------------------
  function startCapture({ lang = "en", onText, onError, onStatus, onEnd }) {
    // A small object the caller keeps so it can stop the capture later.
    const controller = { stop: function () {}, mode: "none" };

    if (canListen()) {
      controller.mode = "browser";
      onStatus && onStatus("Listening... speak now.");
      const recognition = listen({
        lang: fullCode(lang),
        onResult: onText,
        onError: onError,
        onEnd: onEnd,
      });
      controller.stop = function () {
        if (recognition) recognition.stop();
      };
      return controller;
    }

    if (canRecord()) {
      controller.mode = "server";
      let recorder = null;
      let stopped = false;
      record({ lang, onText, onError, onStatus, onEnd }).then((r) => {
        recorder = r;
        // If the user clicked stop before the microphone finished opening
        if (stopped && recorder && recorder.state === "recording") recorder.stop();
      });
      controller.stop = function () {
        stopped = true;
        if (recorder && recorder.state === "recording") recorder.stop();
      };
      return controller;
    }

    onError && onError(
      "This browser cannot use the microphone. Try Chrome or Edge, or type your message instead."
    );
    onEnd && onEnd();
    return controller;
  }

  // -----------------------------------------------------------------------
  // Text to speech
  // -----------------------------------------------------------------------
  function speak(text, lang = "en") {
    if (!canSpeak() || !text) return false;

    window.speechSynthesis.cancel(); // stop anything already speaking

    const utterance = new SpeechSynthesisUtterance(text);
    const wanted = fullCode(lang);
    utterance.lang = wanted;
    utterance.rate = 0.95;

    const voices = window.speechSynthesis.getVoices();
    const match =
      voices.find((v) => v.lang === wanted) ||
      voices.find((v) => v.lang.startsWith(wanted.slice(0, 2)));
    if (match) utterance.voice = match;

    window.speechSynthesis.speak(utterance);
    return true;
  }

  /** Is a Telugu voice installed on this device? */
  function hasTeluguVoice() {
    if (!canSpeak()) return false;
    return window.speechSynthesis.getVoices().some((v) => v.lang.startsWith("te"));
  }

  function stopSpeaking() {
    if (canSpeak()) window.speechSynthesis.cancel();
  }

  // Some browsers load the voice list late; ask for it once on start-up.
  if (canSpeak()) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function () {
      window.speechSynthesis.getVoices();
    };
  }

  return {
    canListen,
    canRecord,
    canCapture,
    canSpeak,
    listen,
    record,
    startCapture,
    speak,
    stopSpeaking,
    hasTeluguVoice,
  };
})();
