"use strict";

document.querySelectorAll("[data-busy-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  });
});

const targetSelect = document.querySelector("#mission-target");
if (targetSelect) {
  const origins = JSON.parse(
    document.querySelector("#attack-origins").textContent,
  );
  const kind = document.querySelector("#mission-kind");
  const rows = [...document.querySelectorAll(".contribution")];
  const format = new Intl.NumberFormat("fr-FR");
  const updateTotals = () => {
    const total = rows.reduce(
      (sum, row) => sum + Number(row.querySelector("input").value || 0),
      0,
    );
    const capture = kind.value === "capture";
    document.querySelector("#army-total").textContent = format.format(total);
    document.querySelector("#army-cost").textContent = format.format(
      (capture ? 900000 : 20000) + total * (capture ? 18000 : 2500),
    );
    document.querySelector("#mission-help").textContent = capture
      ? "La capture affronte la garnison, les murs et les secours automatiques. La victoire transfère la cité ; vos survivants rentrent à leurs origines. Départ au prochain mois, combat un mois après, retour le mois suivant."
      : "Le pillage vise les réserves des villages. Départ au prochain mois, combat un mois après, retour le mois suivant. Le butin ne sera disponible qu’au retour.";
  };
  const updateOrigins = () => {
    const eligible = origins[targetSelect.value] || [];
    rows.forEach((row) => {
      const input = row.querySelector("input");
      input.disabled = !eligible.includes(row.dataset.origin);
      row.classList.toggle("disabled", input.disabled);
      if (input.disabled) input.value = "0";
      row.querySelector(".origin-note").textContent =
        input.disabled && targetSelect.value
          ? "Non reliée à cette frontière"
          : "";
    });
    updateTotals();
  };
  targetSelect.addEventListener("change", updateOrigins);
  kind.addEventListener("change", updateTotals);
  rows.forEach((row) =>
    row.querySelector("input").addEventListener("input", updateTotals),
  );
  updateOrigins();
}

document.querySelectorAll("[data-deadline]").forEach((element) => {
  const update = () => {
    const remaining = Math.max(
      0,
      Math.ceil((new Date(element.dataset.deadline) - Date.now()) / 1000),
    );
    element.textContent =
      remaining > 0
        ? `Clôture dans ${Math.floor(remaining / 60)} min ${String(remaining % 60).padStart(2, "0")} s`
        : "Mois clos · résolution en attente";
  };
  update();
  window.setInterval(update, 1000);
});

// Never submit commands on a timer. For scheduled games, show an explicit refresh
// affordance when the server's revision changes, preserving any unsubmitted form.
if (document.querySelector("[data-deadline]")) {
  const initialUrl = new URL(window.location.href);
  let revision;
  window.setInterval(async () => {
    try {
      const response = await fetch(`${initialUrl.pathname}state/`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      const payload = await response.json();
      if (revision === undefined) revision = payload.game.revision;
      else if (
        payload.game.revision !== revision &&
        !document.querySelector("#refresh-notice")
      ) {
        const notice = document.createElement("div");
        notice.id = "refresh-notice";
        notice.className = "notice";
        const link = document.createElement("a");
        link.href = initialUrl.href;
        link.textContent =
          "De nouvelles chroniques sont disponibles. Actualiser la page.";
        notice.append(link);
        document.querySelector("#main").prepend(notice);
      }
    } catch {
      /* A transient connection failure leaves the current page usable. */
    }
  }, 15000);
}
