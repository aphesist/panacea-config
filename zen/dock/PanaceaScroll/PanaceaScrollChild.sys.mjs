// Panacea scroll nubs, page side: reports the page's scroll position to the browser
// window (PanaceaScrollParent), at most once per frame; scrolls when the nub is dragged.
export class PanaceaScrollChild extends JSWindowActorChild {
  handleEvent() {
    if (this._raf || !this.contentWindow) return;
    this._raf = this.contentWindow.requestAnimationFrame(() => { this._raf = 0; this.report(); });
  }
  report() {
    const w = this.contentWindow;
    const se = w?.document?.scrollingElement || w?.document?.documentElement;
    if (!se) return;
    try {
      this.sendAsyncMessage("scroll", {
        y: w.scrollY, sh: se.scrollHeight, ch: w.innerHeight,
        x: w.scrollX, sw: se.scrollWidth, cw: w.innerWidth,
      });
    } catch (e) {}
  }
  receiveMessage(m) {
    const w = this.contentWindow;
    if (!w) return;
    if (m.name === "query") this.report();
    if (m.name === "scrollTo") w.scrollTo({ left: m.data.x ?? w.scrollX, top: m.data.y ?? w.scrollY, behavior: "instant" });
  }
}
