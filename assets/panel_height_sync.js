(() => {
  let resizeObserver = null;
  let mutationObserver = null;
  let rafId = null;

  function getElements() {
    const grid =
      document.querySelector("#layout-grid") ||
      document.querySelector(".layout-grid");
    const left =
      document.querySelector("#left-panel") ||
      document.querySelector(".left-panel");
    return { grid, left };
  }

  function syncPanelHeight() {
    const { grid, left } = getElements();
    if (!grid || !left) return;
    const topbar =
      document.querySelector(".topbar");
    const main =
      document.querySelector("#main-panel") ||
      document.querySelector(".main-panel");
    const right =
      document.querySelector("#right-panel") ||
      document.querySelector(".right-panel");

    // Respect mobile breakpoint behavior in CSS.
    if (window.matchMedia("(max-width: 980px)").matches) {
      grid.style.removeProperty("--left-panel-h");
      if (main) {
        main.style.removeProperty("height");
        main.style.removeProperty("maxHeight");
      }
      if (right) {
        right.style.removeProperty("height");
        right.style.removeProperty("maxHeight");
      }
      return;
    }

    // Fit dashboard body to viewport (no page-level scroll):
    // use available height from grid top to viewport bottom.
    const gridRect = grid.getBoundingClientRect();
    const available = Math.max(0, Math.floor(window.innerHeight - gridRect.top - 2));
    grid.style.setProperty("--viewport-h", `${available}px`);

    // Fill to viewport height so dashboard reaches bottom with no page blank area.
    const h = Math.max(0, available - 12);
    if (h > 0) {
      grid.style.setProperty("--left-panel-h", `${h}px`);
      if (main) {
        main.style.height = `${h}px`;
        main.style.maxHeight = `${h}px`;
      }
      if (right) {
        right.style.height = `${h}px`;
        right.style.maxHeight = `${h}px`;
      }
    }
  }

  function scheduleSync() {
    if (rafId) return;
    rafId = window.requestAnimationFrame(() => {
      rafId = null;
      syncPanelHeight();
    });
  }

  function bindObservers() {
    const { left } = getElements();
    if (!left) return;

    if (resizeObserver) resizeObserver.disconnect();
    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(scheduleSync);
      resizeObserver.observe(left);
    }
  }

  function init() {
    bindObservers();
    scheduleSync();

    window.addEventListener("resize", scheduleSync, { passive: true });

    // Dash frequently re-renders chunks of DOM; re-bind and sync when tree changes.
    if ("MutationObserver" in window) {
      mutationObserver = new MutationObserver(() => {
        bindObservers();
        scheduleSync();
      });
      mutationObserver.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "style"],
      });
    }

    // Lightweight safety net for cases where observers miss a frame.
    window.setInterval(scheduleSync, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
