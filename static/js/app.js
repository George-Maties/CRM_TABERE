// Behaviour for elements marked with data-* attributes. Each block is independent.
(function () {
  var root = document.documentElement;

  function save(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {
      // Storage blocked: the preference lasts until the page reloads.
    }
  }

  // [data-theme-toggle]: switch light / dark
  var themeButtons = document.querySelectorAll("[data-theme-toggle]");
  function syncThemeButtons() {
    var dark = root.getAttribute("data-bs-theme") === "dark";
    themeButtons.forEach(function (button) {
      button.setAttribute("aria-pressed", String(dark));
    });
  }
  themeButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      save("theme", next);
      syncThemeButtons();
    });
  });
  syncThemeButtons();

  // [data-sidebar-toggle]: collapse the sidebar to an icon rail (large screens)
  document.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
    var label = button.querySelector(".sidebar-label");
    function sync() {
      var collapsed = root.classList.contains("sidebar-collapsed");
      button.setAttribute("aria-expanded", String(!collapsed));
      if (label) {
        label.textContent = collapsed ? button.dataset.labelExpand : button.dataset.labelCollapse;
      }
    }
    button.addEventListener("click", function () {
      var collapsed = root.classList.toggle("sidebar-collapsed");
      save("sidebar-collapsed", collapsed ? "1" : "0");
      sync();
    });
    sync();
  });

  // [data-password-toggle]: show / hide the password field it controls
  document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) return;
    button.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show ? button.dataset.labelHide : button.dataset.labelShow);
    });
  });

  // [data-auto-submit]: submit the form as soon as the control changes (filters)
  document.querySelectorAll("[data-auto-submit]").forEach(function (control) {
    control.addEventListener("change", function () {
      control.form.requestSubmit();
    });
  });

  // [data-show-if="fieldId=value"]: show the block only while that field has that value
  // (without JavaScript every block stays visible, so the form still works)
  document.querySelectorAll("[data-show-if]").forEach(function (block) {
    var rule = block.dataset.showIf.split("=");
    var field = document.getElementById(rule[0]);
    if (!field) return;
    function sync() {
      block.hidden = field.value !== rule[1];
    }
    field.addEventListener("change", sync);
    sync();
  });

  // [data-check-all="name"]: tick / untick every checkbox with that name in the same form;
  // [data-check-count="name"] shows how many are ticked (data-label-none/-one/-many, where
  // {n} is the count and {de} the "de " Romanian puts after numbers from 20 up)
  // Also run on results replaced by a search (data-auto-search).
  function setUpCheckAll(root) {
    root.querySelectorAll("[data-check-all]").forEach(function (master) {
      var form = master.form || master.closest("form");
      if (!form) return;
      var name = master.dataset.checkAll;
      var boxes = form.querySelectorAll('input[type="checkbox"][name="' + name + '"]');
      var counters = form.querySelectorAll('[data-check-count="' + name + '"]');
      function sync() {
        var ticked = 0;
        boxes.forEach(function (box) {
          if (box.checked) ticked += 1;
        });
        master.checked = ticked > 0 && ticked === boxes.length;
        master.indeterminate = ticked > 0 && ticked < boxes.length;
        counters.forEach(function (counter) {
          var label = ticked === 0 ? counter.dataset.labelNone
            : ticked === 1 ? counter.dataset.labelOne : counter.dataset.labelMany;
          var de = ticked % 100 >= 20 || (ticked > 0 && ticked % 100 === 0) ? "de " : "";
          counter.textContent = label.replace("{n}", ticked).replace("{de}", de);
          counter.classList.toggle("is-active", ticked > 0);
        });
      }
      master.addEventListener("change", function () {
        boxes.forEach(function (box) {
          box.checked = master.checked;
        });
        sync();
      });
      boxes.forEach(function (box) {
        box.addEventListener("change", sync);
      });
      // Coming back with Back restores the ticks; show their count again.
      window.addEventListener("pageshow", sync);
      sync();
    });
  }
  setUpCheckAll(document);

  // Notifications (components/notifications.html): each closes by itself when its countdown
  // line runs out, or with its × button. notify("Text", "success") shows one from JavaScript;
  // the type is success, info, warning or danger.
  var notifications = document.getElementById("notifications");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function dismissNotification(item) {
    if (item.classList.contains("is-leaving")) return;
    item.classList.add("is-leaving");
    item.addEventListener("animationend", function (event) {
      if (event.target !== item) return;
      if (reduceMotion.matches || !item.animate) {
        item.remove();
        return;
      }
      // Close the gap smoothly, so the notifications below slide up instead of jumping.
      item.style.overflow = "hidden";
      item
        .animate(
          [
            { height: item.offsetHeight + "px" },
            { height: "0px", paddingTop: "0px", paddingBottom: "0px", marginBottom: "-0.625rem" },
          ],
          { duration: 180, easing: "ease-out" }
        )
        .finished.then(function () {
          item.remove();
        });
    });
  }

  function setUpNotification(item) {
    item.style.setProperty("--notification-timeout", (item.dataset.timeout || 5000) + "ms");
    var progress = item.querySelector(".notification-progress");
    if (progress) {
      progress.addEventListener("animationend", function () {
        dismissNotification(item);
      });
    }
    var close = item.querySelector("[data-notification-close]");
    if (close) {
      close.addEventListener("click", function () {
        dismissNotification(item);
      });
    }
  }

  function notify(text, type, options) {
    var template = document.querySelector(
      '[data-notification-template="' + (type || "info") + '"]'
    ) || document.querySelector('[data-notification-template="info"]');
    if (!notifications || !template) return null;
    var item = template.content.firstElementChild.cloneNode(true);
    item.querySelector(".notification-text").textContent = text;
    if (options && options.timeout) item.dataset.timeout = options.timeout;
    setUpNotification(item);
    notifications.prepend(item);
    return item;
  }

  if (notifications) {
    notifications.querySelectorAll("[data-notification]").forEach(setUpNotification);
    // A notification left in a hidden tab waits there until the tab is seen again.
    function syncPause() {
      notifications.classList.toggle("is-paused", document.hidden);
    }
    document.addEventListener("visibilitychange", syncPause);
    syncPause();
  }
  window.notify = notify;

  // form[data-loading-text]: show progress on the submit button once the request starts
  // Also run on results replaced by a search (data-auto-search).
  function setUpLoadingForms(root) {
    root.querySelectorAll("form[data-loading-text]").forEach(function (form) {
      var button = form.querySelector('[type="submit"]');
      if (!button) return;
      var idleLabel = button.innerHTML;
      // Coming back with the browser's Back button restores the page as it was left.
      window.addEventListener("pageshow", function () {
        button.innerHTML = idleLabel;
        button.disabled = false;
      });
      form.addEventListener("submit", function () {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm me-2";
        spinner.setAttribute("aria-hidden", "true");
        button.textContent = form.dataset.loadingText;
        button.prepend(spinner);
        button.disabled = true;
      });
    });
  }
  setUpLoadingForms(document);

  // form[data-auto-search="id"]: search as you type. After a short pause the results are
  // fetched and only the element with that id is replaced, so typing and focus carry on;
  // the address follows. Without JavaScript (or if the fetch fails) the page loads normally.
  document.querySelectorAll("form[data-auto-search]").forEach(function (form) {
    var results = document.getElementById(form.dataset.autoSearch);
    if (!results || !window.fetch) return;
    var timer;
    var pending;

    function formQuery() {
      var params = new URLSearchParams();
      new FormData(form).forEach(function (value, key) {
        if (value !== "") params.append(key, value);
      });
      return params.toString();
    }

    var last = formQuery();

    function search() {
      var query = formQuery();
      if (query === last) return;
      last = query;
      var url = (form.getAttribute("action") || window.location.pathname) + (query ? "?" + query : "");
      if (pending) pending.abort();
      pending = new AbortController();
      results.setAttribute("aria-busy", "true");
      fetch(url, { signal: pending.signal })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.text();
        })
        .then(function (html) {
          var fresh = new DOMParser().parseFromString(html, "text/html").getElementById(results.id);
          if (!fresh) throw new Error("No results in the page");
          results.innerHTML = fresh.innerHTML;
          results.removeAttribute("aria-busy");
          setUpCheckAll(results);
          setUpLoadingForms(results);
          history.replaceState(null, "", url);
        })
        .catch(function (error) {
          if (error.name !== "AbortError") window.location.href = url;
        });
    }

    form.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(search, 350);
    });
    // Enter searches at once, without reloading the page.
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      clearTimeout(timer);
      search();
    });
  });

  // form[data-confirm="Question?"]: ask before sending (removing something)
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.dataset && form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  // [data-focus-on-show]: a Bootstrap collapse that, once open, puts the cursor in its first field
  document.addEventListener("shown.bs.collapse", function (event) {
    if (!event.target.hasAttribute("data-focus-on-show")) return;
    var field = event.target.querySelector("input:not([type=hidden]), select, textarea");
    if (field) field.focus();
  });

  // [data-autocomplete="url"] (AutocompleteSelect in apps/core/widgets.py): choose one of many
  // by typing. Matches come from the url (?q=), the chosen id goes in the hidden input.
  // Arrows move through the list, Enter chooses, Escape closes.
  document.querySelectorAll("[data-autocomplete]").forEach(function (box) {
    var input = box.querySelector("[data-autocomplete-input]");
    var value = box.querySelector("[data-autocomplete-value]");
    var list = box.querySelector("[role=listbox]");
    var timer;
    var pending;
    var active = -1;

    function options() {
      return list.querySelectorAll("[role=option]:not([aria-disabled])");
    }

    function close() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      active = -1;
    }

    function highlight(index) {
      var all = options();
      if (!all.length) return;
      active = (index + all.length) % all.length;
      all.forEach(function (option, i) {
        option.setAttribute("aria-selected", String(i === active));
      });
      input.setAttribute("aria-activedescendant", all[active].id);
      all[active].scrollIntoView({ block: "nearest" });
    }

    function choose(option) {
      value.value = option.dataset.value;
      input.value = option.dataset.label;
      close();
    }

    function show(results) {
      list.innerHTML = "";
      results.forEach(function (result, i) {
        var option = document.createElement("li");
        option.id = list.id + "-" + i;
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        option.dataset.value = result.id;
        option.dataset.label = result.label;
        var label = document.createElement("span");
        label.className = "autocomplete-label";
        label.textContent = result.label;
        option.appendChild(label);
        if (result.detail) {
          var detail = document.createElement("span");
          detail.className = "autocomplete-detail";
          detail.textContent = result.detail;
          option.appendChild(detail);
        }
        list.appendChild(option);
      });
      if (!results.length) {
        var empty = document.createElement("li");
        empty.setAttribute("role", "option");
        empty.setAttribute("aria-disabled", "true");
        empty.className = "autocomplete-empty";
        empty.textContent = "Nimic găsit.";
        list.appendChild(empty);
      }
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      active = -1;
    }

    function search() {
      if (pending) pending.abort();
      pending = new AbortController();
      var url = box.dataset.autocomplete + "?q=" + encodeURIComponent(input.value.trim());
      fetch(url, { signal: pending.signal, headers: { Accept: "application/json" } })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (document.activeElement === input) show(data.results);
        })
        .catch(function () {
          // Aborted by a newer search, or offline: the box stays as it is.
        });
    }

    input.addEventListener("input", function () {
      // Typing again means the earlier choice no longer holds.
      value.value = "";
      clearTimeout(timer);
      timer = setTimeout(search, 250);
    });
    input.addEventListener("focus", function () {
      if (!value.value) search();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (list.hidden) search();
        else highlight(active + (event.key === "ArrowDown" ? 1 : -1));
      } else if (event.key === "Enter" && !list.hidden && active >= 0) {
        event.preventDefault();
        choose(options()[active]);
      } else if (event.key === "Escape" && !list.hidden) {
        event.preventDefault();
        close();
      }
    });
    // mousedown, not click: it comes before the box loses focus and closes the list.
    list.addEventListener("mousedown", function (event) {
      var option = event.target.closest("[role=option]:not([aria-disabled])");
      if (!option) return;
      event.preventDefault();
      choose(option);
    });
    input.addEventListener("blur", close);
  });
})();
