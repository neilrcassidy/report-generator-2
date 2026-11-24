// Styled confirmation dialog (the <dialog id="confirm-dialog"> in base.html) for
// forms/buttons with data-confirm="…" and for htmx's hx-confirm.
(() => {
  "use strict";

  const dialog = document.getElementById("confirm-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return; // fall back to no confirmation UI
  const message = dialog.querySelector("[data-message]");

  function ask(text) {
    return new Promise((resolve) => {
      message.textContent = text;
      dialog.returnValue = "";
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
      dialog.showModal();
    });
  }

  // Click on the backdrop cancels.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close("cancel");
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    const submitter = event.submitter;
    const text = submitter?.dataset.confirm || form.dataset.confirm;
    if (!text || form.dataset.confirmed === "true") return;
    event.preventDefault();
    ask(text).then((ok) => {
      if (!ok) return;
      form.dataset.confirmed = "true";
      form.requestSubmit(submitter ?? undefined); // fires submit again, synchronously
      delete form.dataset.confirmed;
    });
  });

  document.addEventListener("htmx:confirm", (event) => {
    const question = event.detail.question;
    if (!question) return;
    event.preventDefault();
    ask(question).then((ok) => ok && event.detail.issueRequest(true));
  });
})();
