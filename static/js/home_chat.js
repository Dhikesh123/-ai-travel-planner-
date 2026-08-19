/* ==========================================================================
   The chat box on the home page.

   Same endpoint as the floating assistant and the full /assistant/ page, so
   there is one behaviour to maintain. The difference is that this box is on a
   public page: a visitor who is not signed in gets a short sentence and a
   login link instead of a 403 from the server.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  const box = document.getElementById("homeChat");
  if (!box) return; // not the home page

  const messages = document.getElementById("homeChatMessages");
  const form = document.getElementById("homeChatForm");
  const input = document.getElementById("homeChatInput");
  const sendBtn = document.getElementById("homeChatSend");

  const signedIn = box.dataset.auth === "1";

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = "w-bubble w-bubble-" + role;
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  /** The one case that is not a server error: nobody is signed in yet. */
  function askForLogin() {
    const bubble = document.createElement("div");
    bubble.className = "w-bubble w-bubble-assistant";
    const link = document.createElement("a");
    link.href = "/login/?next=/";
    link.textContent = "Login";
    bubble.appendChild(document.createTextNode("Please sign in to chat with the assistant. "));
    bubble.appendChild(link);
    bubble.appendChild(document.createTextNode(" or create a free account, then ask again."));
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addBubble("user", text);
    input.value = "";

    if (!signedIn) {
      askForLogin();
      return;
    }

    sendBtn.disabled = true;

    const typing = document.createElement("div");
    typing.className = "w-bubble w-bubble-assistant w-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;

    // Streamed, so the first words appear in about a second.
    let reply = null;
    const data = await postChatStream({ message: text }, function (answerSoFar) {
      if (typing.parentNode) typing.remove();
      if (!reply) reply = addBubble("assistant", "");
      reply.textContent = answerSoFar;
      messages.scrollTop = messages.scrollHeight;
    });

    if (typing.parentNode) typing.remove();
    sendBtn.disabled = false;

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
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
});
