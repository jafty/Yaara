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
      ? "Il leur faudra affronter les hommes de la cité, ses murs et les secours du domaine. S’ils l’emportent, la cité vous reviendra et nos survivants rentreront à leurs origines. Ils partiront au prochain mois, combattront un mois après et reviendront le mois suivant."
      : "Nos hommes tenteront d’emporter les réserves des villages. Ils partiront au prochain mois, combattront un mois après et reviendront le mois suivant. Leur butin ne sera à notre disposition qu’à leur retour.";
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
          ? "Ces hommes ne peuvent rejoindre cette frontière par nos terres."
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
        ? `Ce mois sera clos dans ${Math.floor(remaining / 60)} min ${String(remaining % 60).padStart(2, "0")} s.`
        : "Le mois est clos. Nous attendons les nouvelles.";
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
          "De nouvelles lettres nous sont parvenues. Reprendre le livre à ce jour.";
        notice.append(link);
        document.querySelector("#main").prepend(notice);
      }
    } catch {
      /* A transient connection failure leaves the current page usable. */
    }
  }, 15000);
}
