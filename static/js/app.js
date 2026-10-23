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

  // form[data-loading-text]: show progress on the submit button once the request starts
  document.querySelectorAll("form[data-loading-text]").forEach(function (form) {
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
})();
