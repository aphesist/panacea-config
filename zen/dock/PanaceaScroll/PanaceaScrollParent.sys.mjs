// Panacea scroll nubs, window side: hands the page's scroll position to the window's
// panacea-scroll.uc.js (window.PanaceaScroll).
export class PanaceaScrollParent extends JSWindowActorParent {
  receiveMessage(m) {
    const browser = this.browsingContext?.top?.embedderElement;
    browser?.ownerGlobal?.PanaceaScroll?.update(browser, m.data);
  }
}
