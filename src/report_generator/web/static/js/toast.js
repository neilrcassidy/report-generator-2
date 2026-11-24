// Toast notices. The server sends only a notice code, either as ?notice=…&n=… after a
// redirect or as an HX-Trigger "notice" event; the Spanish texts live in base.html.
(() => {
  "use strict";

  const region = document.getElementById("toasts");
  const template = document.getElementById("toast-template");
  const texts = document.getElementById("notice-texts");
  if (!region || !template || !texts) return;

  function textFor(code, n) {
    const find = (c) => texts.content.querySelector(`[data-code="${CSS.escape(c)}"]`);
    const el = (String(n) === "1" && find(`${code}_one`)) || find(code);
    return el ? el.textContent.replace("{n}", n ?? "") : null;
  }

  function show(code, n) {
    const text = textFor(code, n);
    if (!text) return;
    const toast = template.content.firstElementChild.cloneNode(true);
    toast.querySelector("[data-text]").textContent = text;
    region.append(toast);
    setTimeout(() => {
      toast.classList.add("is-leaving");
      toast.addEventListener("animationend", () => toast.remove(), { once: true });
      setTimeout(() => toast.remove(), 600); // in case animations are disabled
    }, 4000);
  }

  const url = new URL(window.location.href);
  const code = url.searchParams.get("notice");
  if (code) {
    show(code, url.searchParams.get("n"));
    url.searchParams.delete("notice");
    url.searchParams.delete("n");
    history.replaceState(history.state, "", url);
  }

  document.body.addEventListener("notice", (event) => show(event.detail.code, event.detail.n));
})();
