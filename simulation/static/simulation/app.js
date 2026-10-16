"use strict";

const english = document.documentElement.lang.startsWith("en");
const text = (fr, en) => english ? en : fr;

document.querySelectorAll("[data-busy-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  });
});

// One shared checklist supports the same work in any number of cities.
document.querySelectorAll("[data-work-form]").forEach((form) => {
  const choices = [...form.querySelectorAll('input[name="cities"]:not(:disabled)')];
  const controls = form.querySelector(".batch-controls");
  const format = new Intl.NumberFormat(document.documentElement.lang);
  const update = () => {
    const selected = choices.filter((input) => input.checked);
    controls.querySelector("[data-city-count]").textContent = format.format(selected.length);
    controls.querySelector("[data-work-cost]").textContent = format.format(
      selected.reduce((sum, input) => sum + Number(input.dataset.cost), 0),
    );
  };
  controls.hidden = false;
  controls.querySelector("[data-select-cities]").addEventListener("click", () => {
    choices.forEach((input) => { input.checked = true; });
    update();
  });
  controls.querySelector("[data-clear-cities]").addEventListener("click", () => {
    choices.forEach((input) => { input.checked = false; });
    update();
  });
  choices.forEach((input) => input.addEventListener("change", update));
  update();
});

const targetSelect = document.querySelector("#mission-target");
if (targetSelect) {
  const origins = JSON.parse(document.querySelector("#attack-origins").textContent);
  const prices = JSON.parse(document.querySelector("#expedition-prices").textContent);
  const kind = document.querySelector("#mission-kind");
  const rows = [...document.querySelectorAll(".contribution")];
  const format = new Intl.NumberFormat(document.documentElement.lang);
  const updateTotals = () => {
    const total = rows.reduce((sum, row) => sum + Number(row.querySelector("input").value || 0), 0);
    const price = prices[kind.value];
    document.querySelector("#army-total").textContent = format.format(total);
    document.querySelector("#army-cost").textContent = format.format(price.base + total * price.per_person);
    document.querySelector("#mission-help").textContent = text(
      `Il faut au moins ${price.minimum} Fidèles. Départ à la clôture de cette lune, combat à la suivante, retour une lune après le combat. Le butin ne sera disponible qu’au retour.`,
      `At least ${price.minimum} Faithful are required. Departure at this Moon’s closure, combat in the next Moon, return one Moon after combat. Loot is available only upon return.`,
    );
  };
  const updateOrigins = () => {
    const eligible = origins[targetSelect.value] || [];
    rows.forEach((row) => {
      const input = row.querySelector("input");
      input.disabled = !eligible.includes(row.dataset.origin);
      row.classList.toggle("disabled", input.disabled);
      if (input.disabled) input.value = "0";
      row.querySelector(".origin-note").textContent = input.disabled && targetSelect.value
        ? text("Ces hommes ne peuvent rejoindre cette frontière par nos terres.", "These men cannot reach this border through our lands.") : "";
    });
    updateTotals();
  };
  targetSelect.addEventListener("change", updateOrigins);
  kind.addEventListener("change", updateTotals);
  rows.forEach((row) => row.querySelector("input").addEventListener("input", updateTotals));
  updateOrigins();
}

document.querySelectorAll("[data-deadline]").forEach((element) => {
  const update = () => {
    const remaining = Math.max(0, Math.ceil((new Date(element.dataset.deadline) - Date.now()) / 1000));
    const duration = `${Math.floor(remaining / 60)} min ${String(remaining % 60).padStart(2, "0")} s`;
    element.textContent = remaining > 0
      ? text(`Cette lune sera close dans ${duration}.`, `This Moon closes in ${duration}.`)
      : text("La lune est close. Nous attendons les nouvelles.", "The Moon is closed. We await the news.");
  };
  update();
  window.setInterval(update, 1000);
});

// A scheduled revision offers a refresh without discarding an unfinished form.
if (document.querySelector("[data-deadline]") && document.body.dataset.stateUrl) {
  const revision = Number(document.body.dataset.revision);
  window.setInterval(async () => {
    try {
      const response = await fetch(document.body.dataset.stateUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      const payload = await response.json();
      if (payload.game.revision !== revision && !document.querySelector("#refresh-notice")) {
        const notice = document.createElement("div");
        notice.id = "refresh-notice";
        notice.className = "notice";
        const link = document.createElement("a");
        link.href = window.location.href;
        link.textContent = text("De nouvelles lettres nous sont parvenues. Reprendre le livre à ce jour.", "New letters have arrived. Open the book at the present day.");
        notice.append(link);
        document.querySelector("#main").prepend(notice);
      }
    } catch { /* A transient failure leaves the current page usable. */ }
  }, 15000);
}
