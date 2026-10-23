// Room configurator of a camp (templates/tabere/configurator.html).
// Someone is moved by dragging them onto a room (or back onto the participants, to take
// them out), or by tapping them and then "Pune aici" — drag and drop doesn't work on phones.
// Every move is saved at once; if the server refuses (a full room), nothing changes.
(function () {
  var root = document.querySelector("[data-configurator]");
  if (!root) return;
  var moveUrl = root.dataset.moveUrl;
  var csrf = root.querySelector("input[name=csrfmiddlewaretoken]").value;
  var template = document.getElementById("room-occupant-template");
  var roster = root.querySelector("[data-roster]");
  var selected = null;

  function rooms() {
    return root.querySelectorAll("[data-room]:not([data-roster])");
  }

  function roomOf(key) {
    var chip = root.querySelector('.room-occupant[data-occupant="' + key + '"]');
    return chip ? chip.closest("[data-room]") : null;
  }

  function rosterPerson(key) {
    return root.querySelector('.roster-person[data-occupant="' + key + '"]');
  }

  function say(text, type) {
    if (window.notify) window.notify(text, type);
  }

  function plural(count, one, many) {
    if (count === 1) return "1 " + one;
    var de = count % 100 >= 20 || (count > 0 && count % 100 === 0) ? "de " : "";
    return count + " " + de + many;
  }

  // Count, free places and empty slots of a room, after a change
  function refresh(room) {
    if (!room) return;
    var list = room.querySelector("[data-room-list]");
    var taken = list.querySelectorAll(".room-occupant").length;
    var capacity = Number(room.dataset.capacity);
    var free = Math.max(capacity - taken, 0);
    list.querySelectorAll(".room-slot").forEach(function (slot) {
      slot.remove();
    });
    for (var i = 0; i < free; i += 1) {
      var slot = document.createElement("li");
      slot.className = "room-slot";
      slot.setAttribute("aria-hidden", "true");
      list.appendChild(slot);
    }
    room.querySelector("[data-room-count]").textContent = taken + "/" + capacity;
    room.querySelector("[data-room-free]").textContent =
      free ? plural(free, "loc liber", "locuri libere") : "Plină";
    room.classList.toggle("is-full", free === 0);
  }

  function refreshSummary() {
    var summary = root.querySelector("[data-summary]");
    if (!summary) return;
    var people = root.querySelectorAll(".roster-person").length;
    var placed = root.querySelectorAll(".roster-person.is-placed").length;
    var beds = 0;
    rooms().forEach(function (room) {
      beds += Number(room.dataset.capacity);
    });
    summary.textContent = placed + " din " + plural(people, "persoană", "persoane") +
      " cazate · " + plural(beds, "loc", "locuri");
  }

  function chipFor(person) {
    var chip = template.content.firstElementChild.cloneNode(true);
    chip.dataset.occupant = person.dataset.occupant;
    chip.querySelector("[data-name]").textContent = person.dataset.label;
    chip.querySelector("[data-meta]").textContent = person.dataset.meta;
    chip.querySelector("[data-unplace]").setAttribute(
      "aria-label", "Scoate pe " + person.dataset.label + " din cameră"
    );
    if (person.dataset.adult === "1") {
      chip.classList.add("is-adult");
      chip.querySelector(".bi").className = "bi bi-person-badge";
    }
    return chip;
  }

  // Show the move on the page, once the server has saved it
  function apply(key, room) {
    var person = rosterPerson(key);
    var before = roomOf(key);
    var old = root.querySelector('.room-occupant[data-occupant="' + key + '"]');
    if (old) old.remove();
    if (room) {
      var list = room.querySelector("[data-room-list]");
      var firstSlot = list.querySelector(".room-slot");
      list.insertBefore(chipFor(person), firstSlot);
    }
    person.classList.toggle("is-placed", Boolean(room));
    person.querySelector("[data-roster-room]").textContent = room ? room.dataset.name : "Fără cameră";
    refresh(before);
    refresh(room);
    refreshSummary();
  }

  function move(key, room) {
    var target = room && room.dataset.room ? room : null;
    if (roomOf(key) === target) return;
    if (target && target.classList.contains("is-full")) {
      say(target.dataset.name + " e plină.", "warning");
      return;
    }
    var body = new FormData();
    body.append("occupant", key);
    body.append("room", target ? target.dataset.room : "");
    fetch(moveUrl, { method: "POST", body: body, headers: { "X-CSRFToken": csrf } })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) throw new Error(data.error || "Nu s-a putut salva.");
          apply(key, target);
        });
      })
      .catch(function (error) {
        say(error.message || "Nu s-a putut salva. Încercați din nou.", "danger");
      });
  }

  // Tap to choose someone, then "Pune aici" on a room
  function select(key) {
    root.querySelectorAll(".is-selected").forEach(function (element) {
      element.classList.remove("is-selected");
      if (element.classList.contains("roster-person")) element.setAttribute("aria-pressed", "false");
    });
    selected = selected === key ? null : key;
    if (selected) {
      var person = rosterPerson(selected);
      person.classList.add("is-selected");
      person.setAttribute("aria-pressed", "true");
      var chip = root.querySelector('.room-occupant[data-occupant="' + selected + '"]');
      if (chip) chip.classList.add("is-selected");
    }
    root.classList.toggle("is-placing", Boolean(selected));
    root.querySelectorAll("[data-place-here]").forEach(function (button) {
      button.hidden = !selected;
    });
  }

  root.addEventListener("click", function (event) {
    var unplace = event.target.closest("[data-unplace]");
    if (unplace) {
      move(unplace.closest("[data-occupant]").dataset.occupant, null);
      return;
    }
    var placeHere = event.target.closest("[data-place-here]");
    if (placeHere && selected) {
      var key = selected;
      select(null);
      move(key, placeHere.closest("[data-room]"));
      return;
    }
    var occupant = event.target.closest(".roster-person, .room-occupant");
    if (occupant) select(occupant.dataset.occupant);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && selected) select(null);
  });

  // The participants are role="button" (Firefox can't drag real buttons): Enter or Space chooses.
  root.addEventListener("keydown", function (event) {
    var person = event.target.closest(".roster-person");
    if (!person || (event.key !== "Enter" && event.key !== " ")) return;
    event.preventDefault();
    select(person.dataset.occupant);
  });

  // Drag and drop
  root.addEventListener("dragstart", function (event) {
    var occupant = event.target.closest("[data-occupant]");
    if (!occupant) return;
    event.dataTransfer.setData("text/plain", occupant.dataset.occupant);
    event.dataTransfer.effectAllowed = "move";
    occupant.classList.add("is-dragging");
  });

  root.addEventListener("dragend", function (event) {
    var occupant = event.target.closest("[data-occupant]");
    if (occupant) occupant.classList.remove("is-dragging");
    root.querySelectorAll(".is-over").forEach(function (zone) {
      zone.classList.remove("is-over");
    });
  });

  function dropZone(event) {
    return event.target.closest ? event.target.closest("[data-room]") : null;
  }

  root.addEventListener("dragover", function (event) {
    var zone = dropZone(event);
    if (!zone) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    zone.classList.add("is-over");
  });

  root.addEventListener("dragleave", function (event) {
    var zone = dropZone(event);
    if (zone && !zone.contains(event.relatedTarget)) zone.classList.remove("is-over");
  });

  root.addEventListener("drop", function (event) {
    var zone = dropZone(event);
    if (!zone) return;
    event.preventDefault();
    zone.classList.remove("is-over");
    var key = event.dataTransfer.getData("text/plain");
    if (key) move(key, zone === roster ? null : zone);
  });
})();
