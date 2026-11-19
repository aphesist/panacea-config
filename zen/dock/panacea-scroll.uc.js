// ==UserScript==
// @name        Panacea scroll nubs
// @description The page's scrollbars as nubs of the frame: a short stroke in the frame colour
//              along the inside of the page edge. Vertical on the right; horizontal along the
//              bottom, riding over the dock's curves. Drag them to scroll.
// ==/UserScript==
// Part of panacea-config (zen/dock). The page's own scrollbars are hidden in userContent.css.
(function () {
  try {
    ChromeUtils.registerWindowActor("PanaceaScroll", {
      parent: { esModuleURI: "chrome://userscripts/content/PanaceaScroll/PanaceaScrollParent.sys.mjs" },
      child: {
        esModuleURI: "chrome://userscripts/content/PanaceaScroll/PanaceaScrollChild.sys.mjs",
        events: { scroll: {}, resize: {}, pageshow: {}, load: {}, DOMContentLoaded: {} },
      },
      allFrames: false,
    });
  } catch (e) {}   // already registered by another window

  const NS = "http://www.w3.org/2000/svg";
  const T = 5, O = T / 2;          // stroke thickness; offset of its centre line from the edge
  const state = new WeakMap();     // browser -> last scroll data
  let svg, vPath, hPath, vLen = 0, hLen = 0;

  function build() {
    svg = document.createElementNS(NS, "svg");
    svg.id = "panacea-scroll";
    for (const id of ["v", "h"]) {
      const p = document.createElementNS(NS, "path");
      p.id = "panacea-scroll-" + id;
      p.setAttribute("fill", "none");
      p.setAttribute("stroke-width", T);
      p.setAttribute("stroke-linecap", "round");
      svg.appendChild(p);
      p.addEventListener("pointerdown", (e) => drag(e, id));
    }
    vPath = svg.querySelector("#panacea-scroll-v");
    hPath = svg.querySelector("#panacea-scroll-h");
    document.documentElement.appendChild(svg);
  }

  function card() {
    const b = gBrowser.selectedBrowser;
    return (b.closest(".browserSidebarContainer") || b).getBoundingClientRect();
  }

  function geometry() {
    const c = card();
    // vertical: down the right edge, clear of the rounded corners
    const x = c.right - O;
    vPath.setAttribute("d", `M${x} ${c.top + 16}L${x} ${c.bottom - 16}`);
    // horizontal: along the bottom edge, over the dock's notch when it's there
    const yb = c.bottom - O, L = c.left + 16, R = c.right - 16;
    const bar = document.getElementById("urlbar");
    let d = `M${L} ${yb}`;
    if (document.documentElement.hasAttribute("panacea-dock") && bar) {
      const u = bar.getBoundingClientRect();
      const h = c.bottom - u.top;                                   // notch height above the page edge
      let r = parseFloat(getComputedStyle(bar).getPropertyValue("--dock-r-out")) || 22;
      r = Math.max(O + 1, Math.min(r, h / 2));
      const top = u.top - O, dl = u.left - O, dr = u.right + O;
      d += `L${u.left - r} ${yb}` +
           `A${r - O} ${r - O} 0 0 0 ${dl} ${c.bottom - r}` +
           `L${dl} ${u.top + r}` +
           `A${r + O} ${r + O} 0 0 1 ${u.left + r} ${top}` +
           `L${u.right - r} ${top}` +
           `A${r + O} ${r + O} 0 0 1 ${dr} ${u.top + r}` +
           `L${dr} ${c.bottom - r}` +
           `A${r - O} ${r - O} 0 0 0 ${u.right + r} ${yb}`;
    }
    d += `L${R} ${yb}`;
    hPath.setAttribute("d", d);
    vLen = vPath.getTotalLength();
    hLen = hPath.getTotalLength();
    // the straight parts only, for mapping the horizontal position (the notch is a detour)
    hPath._span = R - L;
  }

  function draw() {
    if (!svg) return;
    const s = state.get(gBrowser.selectedBrowser);
    geometry();
    const show = (p, len, pos, view, total) => {
      if (!s || total <= view + 1) { p.style.opacity = "0"; p.style.pointerEvents = "none"; return; }
      const thumb = Math.max(30, Math.min(len * 0.9, len * view / total));
      const off = (len - thumb) * Math.min(1, Math.max(0, pos / (total - view)));
      p.setAttribute("stroke-dasharray", `${thumb} ${len + thumb}`);
      p.setAttribute("stroke-dashoffset", `${-off}`);
      p.style.opacity = "1";
      p.style.pointerEvents = "";
      p._thumb = thumb;
    };
    show(vPath, vLen, s?.y, s?.ch, s?.sh);
    show(hPath, hLen, s?.x, s?.cw, s?.sw);
  }

  let raf = 0;
  const later = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; draw(); }); };

  function actor() {
    try { return gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.getActor("PanaceaScroll"); }
    catch (e) { return null; }
  }

  function drag(e, axis) {
    const s = state.get(gBrowser.selectedBrowser);
    if (!s) return;
    e.preventDefault();
    const p = axis === "v" ? vPath : hPath;
    p.setPointerCapture(e.pointerId);
    const len = axis === "v" ? vLen : hLen;
    const start = axis === "v" ? e.clientY : e.clientX;
    const from = axis === "v" ? s.y : s.x;
    const total = axis === "v" ? s.sh - s.ch : s.sw - s.cw;
    const per = total / Math.max(1, len - (p._thumb || 30));
    const move = (ev) => {
      const delta = ((axis === "v" ? ev.clientY : ev.clientX) - start) * per;
      actor()?.sendAsyncMessage("scrollTo", axis === "v" ? { y: from + delta } : { x: from + delta });
    };
    const up = () => { p.removeEventListener("pointermove", move); p.removeEventListener("pointerup", up); };
    p.addEventListener("pointermove", move);
    p.addEventListener("pointerup", up);
  }

  window.PanaceaScroll = {
    update(browser, data) { state.set(browser, data); if (browser === gBrowser.selectedBrowser) later(); },
  };

  function hook() {
    build();
    gBrowser.tabContainer.addEventListener("TabSelect", () => { actor()?.sendAsyncMessage("query"); later(); });
    window.addEventListener("resize", later);
    const bar = document.getElementById("urlbar");
    if (bar) new ResizeObserver(later).observe(bar);        // the dock moves/resizes: re-path
    bar?.addEventListener("transitionend", later);
    for (const ev of ["mouseenter", "mouseleave", "focus", "blur"]) bar?.addEventListener(ev, () => setTimeout(later, 340));
    setTimeout(() => { actor()?.sendAsyncMessage("query"); later(); }, 500);
  }
  if (document.readyState === "complete") hook(); else window.addEventListener("load", hook, { once: true });
})();
