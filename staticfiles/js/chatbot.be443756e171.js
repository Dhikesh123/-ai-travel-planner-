/* ==========================================================================
   The AI chat page: typing, speaking, attaching a photo, and reading answers.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("chatForm");
  if (!form) return;

  const chatWindow = document.getElementById("chatWindow");
  const textBox = document.getElementById("chatText");
  const sendBtn = document.getElementById("sendBtn");
  const micBtn = document.getElementById("micBtn");
  const languageSelect = document.getElementById("inputLanguage");
  const typing = document.getElementById("typing");
  const errorBox = document.getElementById("chatError");
  const imageInput = document.getElementById("chatImage");
  const attachName = document.getElementById("attachName");
  const clearBtn = document.getElementById("clearChat");

  let capture = null;
  let attachedFile = null;

  scrollToBottom();

  // ---------------------------------------------------------------------
  // Adding messages to the screen
  // ---------------------------------------------------------------------
  function addBubble(role, text, imageDataUrl) {
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-" + role;

    const language = /[ఀ-౿]/.test(text) ? "te" : "en";
    const picture = imageDataUrl ? `<img src="${imageDataUrl}" alt="Uploaded photo">` : "";

    bubble.innerHTML = `
      ${picture}
      <div class="bubble-text">${escapeHtml(text)}</div>
      <div class="bubble-actions">
        <button class="speak-btn" data-lang="${language}" title="Read aloud">&#128266;</button>
      </div>`;

    chatWindow.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function scrollToBottom() {
    if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  // Read any message aloud (works for messages loaded from the database too)
  chatWindow.addEventListener("click", function (event) {
    const button = event.target.closest(".speak-btn");
    if (!button) return;
    const text = button.closest(".bubble").querySelector(".bubble-text").innerText;
    const spoke = Speech.speak(text, button.dataset.lang || "en");
    if (!spoke) showError(errorBox, "This browser cannot read text aloud.");
  });

  // ---------------------------------------------------------------------
  // Attaching a photo
  // ---------------------------------------------------------------------
  imageInput.addEventListener("change", function () {
    attachedFile = imageInput.files[0] || null;
    if (!attachedFile) {
      attachName.textContent = "";
      return;
    }
    if (attachedFile.size > 5 * 1024 * 1024) {
      showError(errorBox, "That image is larger than 5 MB. Please choose a smaller one.");
      imageInput.value = "";
      attachedFile = null;
      attachName.textContent = "";
      return;
    }
    showError(errorBox, "");
    attachName.textContent = attachedFile.name;
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

    // startCapture uses the browser's own recogniser when it can, and
    // otherwise records and sends the audio to our server for Whisper.
    capture = Speech.startCapture({
      lang: languageSelect.value,
      onText: (text) => {
        textBox.value = textBox.value ? textBox.value + " " + text : text;
        textBox.focus();
      },
      onStatus: (message) => {
        micBtn.textContent = message.includes("Sending") ? "Writing it out..." : "Click to stop";
      },
      onError: (message) => showError(errorBox, message),
      onEnd: () => {
        capture = null;
        micBtn.classList.remove("mic-active");
        micBtn.innerHTML = "&#127908; Speak";
      },
    });
  });

  // ---------------------------------------------------------------------
  // Sending a message
  // ---------------------------------------------------------------------
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const message = textBox.value.trim();

    if (!message && !attachedFile) {
      showError(errorBox, "Type a message or attach a photo first.");
      return;
    }

    showError(errorBox, "");
    sendBtn.disabled = true;
    typing.hidden = false;

    // Show the customer's own message straight away
    const previewUrl = attachedFile ? URL.createObjectURL(attachedFile) : null;
    addBubble("user", message || "(photo)", previewUrl);
    textBox.value = "";

    let data;
    if (attachedFile) {
      // A photo means we use the image recognition endpoint
      const formData = new FormData();
      formData.append("image", attachedFile);
      formData.append("question", message);
      data = await postForm("/api/image-recognition/", formData);
      if (data.ok) data.reply = data.result;

      attachedFile = null;
      imageInput.value = "";
      attachName.textContent = "";
    } else {
      data = await postJSON("/api/chat/", { message: message });
    }

    typing.hidden = true;
    sendBtn.disabled = false;

    if (!data.ok) {
      showError(errorBox, data.error || "The assistant could not reply. Please try again.");
      return;
    }

    addBubble("assistant", data.reply);
    if (data.note) addBubble("assistant", data.note);
  });

  // Enter sends, Shift+Enter makes a new line
  textBox.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  // ---------------------------------------------------------------------
  // Clearing the history
  // ---------------------------------------------------------------------
  if (clearBtn) {
    clearBtn.addEventListener("click", async function () {
      if (!confirm("Delete your whole chat history?")) return;
      const response = await fetch("/api/chat/history/", {
        method: "DELETE",
        headers: { "X-CSRFToken": window.CSRF_TOKEN },
      });
      if (response.ok) {
        chatWindow.innerHTML = "";
        addBubble("assistant", "History cleared. How can I help you plan a trip?");
      } else {
        showError(errorBox, "Could not clear the history. Please try again.");
      }
    });
  }
});
