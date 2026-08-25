/* ==========================================================================
   "From" box suggestions.

   Attaches to any text input carrying data-city-search, and offers matching
   towns as they type - the destinations in the catalogue first, then the
   starting cities the site knows.

   The list comes from our own tables (/api/city-search/), never from a live
   geocoder: OpenStreetMap's usage policy rules out autocomplete against
   their servers. A town that is not on the list can still be typed in full;
   it is looked up once when the trip is planned.

   Built as a combobox rather than a <datalist> because the site needs to
   show a second line ("Andhra Pradesh") under each name, which a datalist
   cannot do, and because a datalist gives no way to say "no matches".
   ========================================================================== */

(function () {
  "use strict";

  var MINIMUM_LETTERS = 2;
  var TYPING_PAUSE = 220;   // ms of quiet before asking the server

  function attach(input) {
    var box = document.createElement("ul");
    box.className = "city-suggestions";
    box.setAttribute("role", "listbox");
    box.hidden = true;

    // The input is usually inside a <label>; the list is positioned against
    // a wrapper so it lines up with the box rather than the whole label.
    var shell = document.createElement("div");
    shell.className = "city-search";
    input.parentNode.insertBefore(shell, input);
    shell.appendChild(input);
    shell.appendChild(box);

    input.setAttribute("autocomplete", "off");
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-autocomplete", "list");

    var results = [];
    var active = -1;
    var timer = null;
    var latest = 0;

    function close() {
      box.hidden = true;
      input.setAttribute("aria-expanded", "false");
      active = -1;
    }

    function choose(index) {
      if (index < 0 || index >= results.length) return;
      input.value = results[index].name;
      close();
      // Let the planner know: it reloads the places along the journey, and
      // recalculates the cost, off these same events.
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function highlight(index) {
      active = index;
      Array.prototype.forEach.call(box.children, function (item, position) {
        var on = position === index;
        item.classList.toggle("is-active", on);
        item.setAttribute("aria-selected", on ? "true" : "false");
      });
    }

    function render() {
      box.innerHTML = "";
      if (!results.length) {
        close();
        return;
      }

      results.forEach(function (result, index) {
        var item = document.createElement("li");
        item.className = "city-suggestion";
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", "false");

        var parts = result.label.split(",");
        var name = document.createElement("span");
        name.className = "city-suggestion-name";
        name.textContent = parts.shift();
        item.appendChild(name);

        if (parts.length) {
          var where = document.createElement("span");
          where.className = "city-suggestion-where";
          where.textContent = parts.join(",").trim();
          item.appendChild(where);
        }
        if (result.kind === "destination") {
          var tag = document.createElement("span");
          tag.className = "city-suggestion-tag";
          tag.textContent = "We plan trips here";
          item.appendChild(tag);
        }

        // mousedown, not click: blur fires first on a click and would close
        // the list before the selection ever landed
        item.addEventListener("mousedown", function (event) {
          event.preventDefault();
          choose(index);
        });
        item.addEventListener("mouseenter", function () {
          highlight(index);
        });
        box.appendChild(item);
      });

      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      highlight(-1);
    }

    async function search() {
      var text = input.value.trim();
      if (text.length < MINIMUM_LETTERS) {
        results = [];
        close();
        return;
      }

      var mine = ++latest;
      try {
        var data = await fetch(
          "/api/city-search/?q=" + encodeURIComponent(text)
        ).then(function (response) {
          return response.json();
        });
        if (mine !== latest) return;      // they kept typing
        results = data.ok ? data.results : [];
        render();
      } catch (error) {
        results = [];
        close();                          // no suggestions is not an error
      }
    }

    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(search, TYPING_PAUSE);
    });

    input.addEventListener("keydown", function (event) {
      if (box.hidden) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        highlight((active + 1) % results.length);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        highlight(active <= 0 ? results.length - 1 : active - 1);
      } else if (event.key === "Enter" && active >= 0) {
        event.preventDefault();          // do not submit the form yet
        choose(active);
      } else if (event.key === "Escape") {
        close();
      }
    });

    input.addEventListener("blur", function () {
      // a moment for a click on the list to land first
      window.setTimeout(close, 120);
    });
    input.addEventListener("focus", function () {
      if (results.length) render();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-city-search]"),
      attach
    );
  });
})();
