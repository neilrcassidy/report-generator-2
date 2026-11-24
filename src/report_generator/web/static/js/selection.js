// Checkbox selection on the students list: the select-all box, the row highlight,
// and the selection bar's labels/disabled states. All visible text comes from
// data-label-* attributes in the template ({n} is replaced with a count).
(() => {
  "use strict";

  const fill = (template, n) => (template || "").replace("{n}", String(n));

  function setLabel(button, text) {
    const label = button.querySelector("[data-label]");
    if (label) label.textContent = text;
  }

  function update(form) {
    const rows = [...form.querySelectorAll("[data-select-row]")];
    const selected = rows.filter((box) => box.checked);
    const n = selected.length;
    const withResults = selected.filter((box) => box.dataset.hasResult === "true").length;
    const all = rows.length > 0 && n === rows.length;

    const master = form.querySelector("[data-select-all]");
    if (master) {
      master.checked = all;
      master.indeterminate = n > 0 && !all;
    }
    for (const box of rows) box.closest("tr")?.classList.toggle("is-selected", box.checked);

    const bar = form.querySelector("[data-selection-bar]");
    bar?.classList.toggle("has-selection", n > 0);

    const count = form.querySelector("[data-count]");
    if (count) {
      const d = count.dataset;
      count.textContent = n === 0 ? d.labelNone : n === 1 ? d.labelOne : fill(d.labelMany, n);
    }

    // Download: counts only students that have exams (the others have no report).
    const download = form.querySelector('[data-action="download"]');
    if (download) {
      const d = download.dataset;
      let label = d.labelNone;
      if (withResults === 1) label = d.labelOne;
      else if (withResults > 1) label = all ? d.labelAll : fill(d.labelMany, withResults);
      setLabel(download, label);
      download.disabled = withResults === 0;
    }
    const hint = form.querySelector("[data-hint]");
    if (hint) hint.hidden = !(n > 0 && withResults === 0);

    const remove = form.querySelector('[data-action="delete"]');
    if (remove) {
      const d = remove.dataset;
      setLabel(remove, n === 0 ? d.labelNone : all && n > 1 ? d.labelAll : fill(d.labelMany, n));
      remove.disabled = n === 0;
      remove.dataset.confirm = fill(n === 1 ? d.confirmOne : d.confirmMany, n);
    }

    const clear = form.querySelector('[data-action="clear"]');
    if (clear) clear.disabled = n === 0;
  }

  function init() {
    document.querySelectorAll("form[data-selection]").forEach(update);
  }

  document.addEventListener("change", (event) => {
    const form = event.target.closest("form[data-selection]");
    if (!form) return;
    if (event.target.matches("[data-select-all]")) {
      for (const box of form.querySelectorAll("[data-select-row]")) box.checked = event.target.checked;
    }
    update(form);
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest('[data-action="clear"]');
    const form = button?.closest("form[data-selection]");
    if (!form) return;
    for (const box of form.querySelectorAll("[data-select-row], [data-select-all]")) box.checked = false;
    update(form);
  });

  // Search/filter swaps the rows: the new rows start unselected.
  document.addEventListener("htmx:afterSwap", init);
  // Back/forward cache can restore ticked boxes without firing change events.
  window.addEventListener("pageshow", init);
  init();
})();
