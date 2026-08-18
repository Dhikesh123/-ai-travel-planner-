/* ==========================================================================
   Speech helpers - shared by the chatbot, the voice page and image results.

   Turning speech into text can happen in TWO ways, and this file picks the
   best one automatically:

     1. The browser's own SpeechRecognition (Chrome, Edge) - instant, free,
        nothing is sent to our server.
     2. If the browser cannot do that (Safari, Firefox), or if it cannot
        handle the chosen language, we record the microphone with
        MediaRecorder and send the audio to our server, which passes it to
        Whisper. Slower, but it works everywhere and understands Telugu.

   Speaking text out loud uses the browser's speechSynthesis in both cases.
   ========================================================================== */

const Speech = (function () {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  // Listening ends when the user clicks stop - never on a timer, and never
  // because the room went quiet for a while.
  //
  // Restarting inside onend throws InvalidStateError, so wait a moment first.
  const RESTART_DELAY_MS = 250;
  // After this many quiet stretches, say we are still listening, so a muted
  // microphone is not mistaken for patience. We keep listening either way.
  const QUIET_HINT_AFTER = 3;
  // A healthy listening turn lasts seconds. Anything shorter that also heard
  // nothing means the browser is refusing to listen rather than waiting.
  const MIN_HEALTHY_TURN_MS = 1000;
  const MAX_RAPID_FAILURES = 5;
  // The one real limit: the transcription API rejects very large uploads, and
  // this is minutes of speech, well past a single spoken request.
  const MAX_RECORDING_MS = 600000;

  const ERROR_MESSAGES = {
    "audio-capture":
      "No microphone was found. Plug one in, or choose the right one in your browser's microphone settings.",
    "not-allowed":
      "Microphone permission was blocked. Click the padlock in the address bar, allow the microphone, then reload this page.",
    "service-not-allowed":
      "The browser's speech service is not available. Please type instead.",
    network: "Speech recognition needs an internet connection.",
    "language-not-supported":
      "This browser has no voice pack for that language. Try English, or type instead.",
    "bad-grammar": "Speech recognition failed. Please try again.",
  };

  // Errors that mean the browser's own recogniser cannot do this job. When we
  // see one of these we quietly switch to recording + server transcription
  // instead of showing the user a dead end.
  const FALLBACK_ERRORS = ["language-not-supported", "service-not-allowed", "network"];

  // Languages this browser's recogniser has already refused. Once we know it
  // cannot do Telugu we go straight to recording, instead of making the user
  // wait through the same failure on every click.
  const unsupportedLanguages = [];

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

  /**
   * Browsers only allow the microphone on a secure page. localhost counts as
   * secure; opening the site by its network address over plain http does not,
   * and that is the most common reason the microphone "does nothing".
   */
  function isSecureContext() {
    if (window.isSecureContext !== undefined) return Boolean(window.isSecureContext);
    return location.protocol === "https:" || location.hostname === "localhost";
  }

  /**
   * Ask the browser whether microphone permission is already blocked, so we
   * can say something useful instead of waiting for a cryptic error. Returns
   * "granted", "denied", "prompt" or "unknown".
   */
  async function permissionState() {
    if (!navigator.permissions || !navigator.permissions.query) return "unknown";
    try {
      const status = await navigator.permissions.query({ name: "microphone" });
      return status.state || "unknown";
    } catch (err) {
      return "unknown"; // Firefox and Safari do not know this permission name
    }
  }

  // -----------------------------------------------------------------------
  // Method 1: the browser's own speech recognition
  //
  // Returns a small object with .stop(). It keeps listening through the
  // natural pauses in a sentence and only finishes when the caller stops it,
  // when the language is unsupported, or after a long silence.
  // -----------------------------------------------------------------------
  function listen({ lang = "en-IN", onResult, onInterim, onStatus, onError, onEnd, onGiveUp }) {
    if (!canListen()) {
      onError && onError("This browser cannot listen to the microphone.");
      onEnd && onEnd();
      return { stop: function () {} };
    }

    const recognition = new Recognition();
    recognition.lang = fullCode(lang);
    // People pause while they think, and Telugu sentences are long. Without
    // continuous mode the browser stops at the first pause, so only the first
    // few words are ever captured.
    recognition.continuous = true;
    // Interim results let the page show the words as they are being heard.
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let stoppedByUser = false;
    let finished = false;
    let starts = 0;
    let turnStartedAt = 0;
    let heardThisTurn = false;
    let quietTurns = 0;
    let rapidFailures = 0;
    let fatalMessage = null;
    let fallbackError = null;
    let restartTimer = null;

    function finish() {
      if (finished) return;
      finished = true;
      clearTimeout(restartTimer);
      onEnd && onEnd();
    }

    recognition.onstart = function () {
      starts += 1;
      heardThisTurn = false;
      turnStartedAt = Date.now();
      // Only announce the first start; the restarts are our business, not the
      // user's, and would wipe out whatever the page is showing.
      if (starts === 1) {
        onStatus && onStatus("Listening... speak now. I will keep listening until you click stop.");
      }
    };

    recognition.onresult = function (event) {
      let interim = "";
      // In continuous mode the results pile up, so read only what is new.
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = (result[0] && result[0].transcript) || "";
        if (result.isFinal) {
          const trimmed = text.trim();
          if (trimmed) {
            heardThisTurn = true;
            silentRestarts = 0;
            onResult && onResult(trimmed);
          }
        } else {
          interim += text;
        }
      }
      if (interim.trim()) {
        heardThisTurn = true;
        silentRestarts = 0;
        onInterim && onInterim(interim.trim());
      }
    };

    recognition.onerror = function (event) {
      const code = event.error;
      // "no-speech" is Chrome saying the room went quiet, and "aborted" is our
      // own restart. Neither is a failure - onend decides what happens next.
      if (code === "no-speech" || code === "aborted") return;
      if (FALLBACK_ERRORS.indexOf(code) !== -1 && onGiveUp) {
        fallbackError = code;
        return;
      }
      fatalMessage = ERROR_MESSAGES[code] || "Speech recognition failed. Please type instead.";
    };

    recognition.onend = function () {
      if (finished) return;

      if (fallbackError) {
        const code = fallbackError;
        // Hand over without firing onEnd - the fallback owns the session now.
        finished = true;
        clearTimeout(restartTimer);
        onGiveUp(code);
        return;
      }
      if (fatalMessage) {
        onError && onError(fatalMessage);
        finish();
        return;
      }
      if (stoppedByUser) {
        finish();
        return;
      }

      // Everything below is Chrome closing its own session - after a few
      // seconds of quiet, or at the end of a phrase. That is never a reason
      // to stop: only the user's stop click ends the microphone. So we start
      // it again and carry on, however long the silence lasts.
      if (heardThisTurn) {
        quietTurns = 0;
      } else {
        quietTurns += 1;
        // Say we are still here, so a muted microphone does not look like
        // patience. We keep listening either way.
        if (quietTurns === QUIET_HINT_AFTER) {
          onStatus &&
            onStatus(
              "Still listening - nothing heard yet. Check your microphone is unmuted, or click stop when you are done."
            );
        }
      }

      // The one thing we will not do is spin: a browser that closes the
      // session instantly, again and again, is refusing to listen rather
      // than waiting for speech, and restarting forever would hang the page.
      if (!heardThisTurn && Date.now() - turnStartedAt < MIN_HEALTHY_TURN_MS) {
        rapidFailures += 1;
      } else {
        rapidFailures = 0;
      }
      if (rapidFailures >= MAX_RAPID_FAILURES) {
        onError &&
          onError(
            "The browser keeps closing the microphone straight away. Check that the right microphone is selected and allowed, then try again."
          );
        finish();
        return;
      }

      restartTimer = setTimeout(function () {
        if (finished || stoppedByUser) return;
        try {
          recognition.start();
        } catch (err) {
          finish();
        }
      }, RESTART_DELAY_MS);
    };

    try {
      recognition.start();
    } catch (err) {
      onError && onError("Could not start the microphone. Please try again.");
      onEnd && onEnd();
      return { stop: function () {} };
    }

    return {
      stop: function () {
        stoppedByUser = true;
        clearTimeout(restartTimer);
        try {
          recognition.stop(); // lets the last words come through before onend
        } catch (err) {
          finish();
        }
      },
    };
  }

  // -----------------------------------------------------------------------
  // Method 2: record the microphone and let our server transcribe it
  // -----------------------------------------------------------------------

  /** Pick a recording format this browser actually supports. */
  function pickRecordingType() {
    const candidates = [
      { mime: "audio/webm;codecs=opus", ext: "webm" },
      { mime: "audio/webm", ext: "webm" },
      { mime: "audio/ogg;codecs=opus", ext: "ogg" },
      { mime: "audio/mp4", ext: "m4a" }, // Safari records mp4, never webm
    ];
    const supported = window.MediaRecorder && window.MediaRecorder.isTypeSupported;
    if (supported) {
      for (let i = 0; i < candidates.length; i += 1) {
        if (window.MediaRecorder.isTypeSupported(candidates[i].mime)) return candidates[i];
      }
    }
    return { mime: "", ext: "webm" }; // let the browser choose
  }

  /** Work out the file extension from whatever the recorder actually used. */
  function extensionFor(mimeType) {
    const type = (mimeType || "").toLowerCase();
    if (type.indexOf("ogg") !== -1) return "ogg";
    if (type.indexOf("mp4") !== -1 || type.indexOf("m4a") !== -1 || type.indexOf("aac") !== -1) {
      return "m4a";
    }
    if (type.indexOf("mpeg") !== -1 || type.indexOf("mp3") !== -1) return "mp3";
    if (type.indexOf("wav") !== -1) return "wav";
    return "webm";
  }

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
      const name = err && err.name;
      let message = "No microphone was found. Please check your device.";
      if (name === "NotAllowedError" || name === "SecurityError") {
        message =
          "Microphone permission was blocked. Click the padlock in the address bar, allow the microphone, then reload this page.";
      } else if (name === "NotReadableError" || name === "AbortError") {
        message =
          "Another program is using the microphone. Close it (a video call, for example) and try again.";
      }
      onError && onError(message);
      onEnd && onEnd();
      return null;
    }

    const chunks = [];
    const chosen = pickRecordingType();
    let recorder;
    try {
      recorder = chosen.mime
        ? new MediaRecorder(stream, { mimeType: chosen.mime })
        : new MediaRecorder(stream);
    } catch (err) {
      try {
        recorder = new MediaRecorder(stream); // fall back to the default format
      } catch (err2) {
        stream.getTracks().forEach((t) => t.stop());
        onError && onError("This browser could not start recording. Please type instead.");
        onEnd && onEnd();
        return null;
      }
    }

    let stopTimer = null;

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunks.push(event.data);
    };

    recorder.onstop = async function () {
      clearTimeout(stopTimer);
      stream.getTracks().forEach((t) => t.stop()); // release the microphone

      if (!chunks.length) {
        onError && onError("Nothing was recorded. Please try again.");
        onEnd && onEnd();
        return;
      }

      onStatus && onStatus("Sending your recording to be written out...");

      // Name the file after the format the recorder really used - Safari
      // records mp4, and calling that ".webm" makes the server reject it.
      const mimeType = recorder.mimeType || chosen.mime || "audio/webm";
      const blob = new Blob(chunks, { type: mimeType });

      const formData = new FormData();
      formData.append("audio", blob, "recording." + extensionFor(mimeType));
      formData.append("language", shortCode(lang));

      const data = await postForm("/api/transcribe/", formData);

      if (!data.ok) {
        onError && onError(data.error || "Could not understand that recording.");
      } else if (!data.text || !data.text.trim()) {
        onError && onError("I could not make out any words in that recording. Please try again.");
      } else {
        onText && onText(data.text.trim());
      }
      onEnd && onEnd();
    };

    recorder.start();
    // Stop on our own if the user forgets, so the upload stays small enough.
    stopTimer = setTimeout(function () {
      if (recorder.state === "recording") recorder.stop();
    }, MAX_RECORDING_MS);

    onStatus && onStatus("Recording... click the microphone again to stop.");
    return recorder;
  }

  // -----------------------------------------------------------------------
  // The one function the pages actually use.
  // It picks the best available method and hides the difference.
  // -----------------------------------------------------------------------
  function startCapture({ lang = "en", onText, onInterim, onError, onStatus, onEnd }) {
    // A small object the caller keeps so it can stop the capture later.
    const controller = { stop: function () {}, mode: "none" };
    let stopped = false;

    if (!isSecureContext()) {
      onError &&
        onError(
          "The microphone only works on a secure page. Open this site as http://127.0.0.1:8000/ or over https."
        );
      onEnd && onEnd();
      return controller;
    }

    // Record the microphone and let the server write it out.
    function startRecording(noticeMessage) {
      controller.mode = "server";
      if (noticeMessage) onStatus && onStatus(noticeMessage);

      let recorder = null;
      controller.stop = function () {
        stopped = true;
        if (recorder && recorder.state === "recording") recorder.stop();
      };

      record({ lang, onText, onError, onStatus, onEnd }).then((started) => {
        recorder = started;
        // If the user clicked stop before the microphone finished opening
        if (stopped && recorder && recorder.state === "recording") recorder.stop();
      });
    }

    if (canListen() && unsupportedLanguages.indexOf(fullCode(lang)) === -1) {
      controller.mode = "browser";
      const session = listen({
        lang: fullCode(lang),
        onResult: onText,
        onInterim: onInterim,
        onStatus: onStatus,
        onError: onError,
        onEnd: onEnd,
        // The browser recogniser cannot handle this language (Telugu is the
        // usual case). Switch to recording instead of giving up.
        onGiveUp: function (code) {
          // A missing voice pack will not appear between two clicks, so
          // remember it. A network or service problem might, so do not.
          if (code === "language-not-supported" && unsupportedLanguages.indexOf(fullCode(lang)) === -1) {
            unsupportedLanguages.push(fullCode(lang));
          }
          if (stopped) {
            onEnd && onEnd();
            return;
          }
          if (canRecord()) {
            startRecording(
              "This browser cannot understand that language on its own, so your voice is being recorded for the server to write out. Speak now, then click the microphone again."
            );
            return;
          }
          onError &&
            onError(ERROR_MESSAGES[code] || "Speech recognition failed. Please type instead.");
          onEnd && onEnd();
        },
      });
      controller.stop = function () {
        stopped = true;
        session.stop();
      };
      return controller;
    }

    if (canRecord()) {
      startRecording(null);
      return controller;
    }

    onError &&
      onError(
        "This browser cannot use the microphone. Try Chrome or Edge, or type your message instead."
      );
    onEnd && onEnd();
    return controller;
  }

  // -----------------------------------------------------------------------
  // Text to speech
  // -----------------------------------------------------------------------

  // Chrome fills the voice list in late, so keep our own copy and refresh it.
  let voiceCache = [];

  function refreshVoices() {
    if (!canSpeak()) return [];
    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length) voiceCache = voices;
    return voiceCache;
  }

  function speak(text, lang = "en") {
    if (!canSpeak() || !text) return false;

    window.speechSynthesis.cancel(); // stop anything already speaking

    const utterance = new SpeechSynthesisUtterance(text);
    const wanted = fullCode(lang);
    utterance.lang = wanted;
    utterance.rate = 0.95;

    const voices = refreshVoices();
    const match =
      voices.find((v) => v.lang === wanted) ||
      voices.find((v) => v.lang && v.lang.replace("_", "-").startsWith(wanted.slice(0, 2)));
    if (match) utterance.voice = match;

    window.speechSynthesis.speak(utterance);
    return true;
  }

  /**
   * Is a Telugu voice installed on this device? When the browser has not
   * loaded its voice list yet we answer "yes" and let it try, because saying
   * "no" would block a device that can actually speak Telugu.
   */
  function hasTeluguVoice() {
    if (!canSpeak()) return false;
    const voices = refreshVoices();
    if (!voices.length) return true;
    return voices.some((v) => v.lang && v.lang.replace("_", "-").toLowerCase().startsWith("te"));
  }

  function stopSpeaking() {
    if (canSpeak()) window.speechSynthesis.cancel();
  }

  // Some browsers load the voice list late; ask for it once on start-up.
  if (canSpeak()) {
    refreshVoices();
    window.speechSynthesis.onvoiceschanged = refreshVoices;
  }

  return {
    canListen,
    canRecord,
    canCapture,
    canSpeak,
    isSecureContext,
    permissionState,
    listen,
    record,
    startCapture,
    speak,
    stopSpeaking,
    hasTeluguVoice,
  };
})();
