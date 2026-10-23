// Loaded in <head>, before the page paints, so saved preferences apply without a flash.
(function () {
  var root = document.documentElement;
  var theme = null;
  var collapsed = null;
  try {
    theme = localStorage.getItem("theme");
    collapsed = localStorage.getItem("sidebar-collapsed");
  } catch (e) {
    // Storage blocked (private mode): fall back to defaults.
  }
  if (theme !== "light" && theme !== "dark") {
    theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  root.setAttribute("data-bs-theme", theme);
  if (collapsed === "1") {
    root.classList.add("sidebar-collapsed");
  }
})();
