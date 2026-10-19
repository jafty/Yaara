"use strict";

document.querySelectorAll("[data-busy-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  });
});

// One shared checklist supports the same work in any number of cities.
document.querySelectorAll("[data-work-form]").forEach((form) => {
  const choices = [
    ...form.querySelectorAll('input[name="cities"]:not(:disabled)'),
  ];
  const controls = form.querySelector(".batch-controls");
  const format = new Intl.NumberFormat(document.documentElement.lang);
  const update = () => {
    const selected = choices.filter((input) => input.checked);
    const total = selected.reduce(
      (sum, input) => sum + Number(input.dataset.cost),
      0,
    );
    const remaining = Number(form.dataset.freeStock) - total;
    const shortfall = form.dataset.localFunding === "true"
      ? selected.reduce((sum, input) => sum + Number(input.dataset.shortfall), 0)
      : Math.max(0, -remaining);
    controls.querySelector("[data-city-count]").textContent = format.format(
      selected.length,
    );
    controls.querySelector("[data-work-cost]").textContent =
      format.format(total);
    controls.querySelector("[data-budget-note]").textContent =
      shortfall > 0
        ? interpolate(
            form.dataset.localFunding === "true"
              ? gettext("Il manque %(amount)s Mesures dans les cités choisies.")
              : gettext("Il manque %(amount)s Mesures pour cet ouvrage."),
            { amount: format.format(shortfall) },
            true,
          )
        : interpolate(
            gettext("Après réservation : %(amount)s Mesures libres."),
            { amount: format.format(remaining) },
            true,
          );
  };
  controls.hidden = false;
  controls
    .querySelector("[data-select-cities]")
    .addEventListener("click", () => {
      choices.forEach((input) => {
        input.checked = true;
      });
      update();
    });
  controls
    .querySelector("[data-clear-cities]")
    .addEventListener("click", () => {
      choices.forEach((input) => {
        input.checked = false;
      });
      update();
    });
  choices.forEach((input) => input.addEventListener("change", update));
  update();
});

const targetSelect = document.querySelector("#mission-target");
if (targetSelect) {
  const origins = JSON.parse(
    document.querySelector("#attack-origins").textContent,
  );
  const prices = JSON.parse(
    document.querySelector("#expedition-prices").textContent,
  );
  const kind = document.querySelector("#mission-kind");
  const form = targetSelect.closest("form");
  const rows = [...document.querySelectorAll(".contribution")];
  const format = new Intl.NumberFormat(document.documentElement.lang);
  const updateTotals = () => {
    const counts = rows.map(row => {
      const value = Number(row.querySelector("input").value || 0);
      return Number.isSafeInteger(value) && value > 0 ? value : 0;
    });
    const total = rows.reduce(
      (sum, row, index) => sum + counts[index],
      0,
    );
    const price = prices[kind.value];
    const cost = price.base + total * price.per_person;
    document.querySelector("#army-total").textContent = format.format(total);
    document.querySelector("#army-cost").textContent = format.format(
      cost,
    );
    // Match the server's whole-Measure Hamilton allocation and city-ID tie order.
    const fees = counts.map(count => total ? Math.floor(price.base * count / total) : 0);
    const ranked = rows.map((row, index) => ({
      index, id: row.dataset.origin,
      remainder: total ? (price.base * counts[index]) % total : 0,
    })).sort((a, b) => b.remainder - a.remainder || a.id.localeCompare(b.id));
    if (total) {
      const remaining = price.base - fees.reduce((sum, fee) => sum + fee, 0);
      ranked.slice(0, remaining).forEach(row => { fees[row.index] += 1; });
    }
    let shortfall = 0;
    rows.forEach((row, index) => {
      const note = row.querySelector(".origin-funding");
      if (!note) return;
      const charge = fees[index] + counts[index] * price.per_person;
      const available = Number(row.dataset.freeStock);
      const missing = Math.max(0, charge - available);
      shortfall += missing;
      note.textContent = interpolate(
        gettext("Part de cette cité : %(charge)s Mesures ; disponibles : %(available)s."),
        { charge: format.format(charge), available: format.format(available) }, true,
      ) + (missing ? " " + interpolate(
        gettext("Il manque %(amount)s Mesures dans cette cité."),
        { amount: format.format(missing) }, true,
      ) : "");
    });
    if (form.dataset.localFunding !== "true") {
      shortfall = Math.max(0, cost - Number(form.dataset.freeStock));
    }
    form.querySelector("[data-expedition-budget]").textContent = shortfall
      ? interpolate(
          gettext("Il manque %(amount)s Mesures pour cette expédition. Aucun moyen n’est réservé."),
          { amount: format.format(shortfall) }, true,
        )
      : "";
    document.querySelector("#mission-help").textContent = interpolate(
      gettext(
        "Il faut au moins %(minimum)s Fidèles. Départ à la clôture de cette lune, combat à la suivante, retour une lune après le combat. Le butin ne sera disponible qu’au retour.",
      ),
      { minimum: price.minimum },
      true,
    );
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
          ? gettext(
              "Ces hommes ne peuvent rejoindre cette frontière par nos terres.",
            )
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
    const duration = `${Math.floor(remaining / 60)} min ${String(remaining % 60).padStart(2, "0")} s`;
    element.textContent =
      remaining > 0
        ? interpolate(
            gettext("Cette lune sera close dans %(duration)s."),
            { duration },
            true,
          )
        : gettext("La lune est close. Nous attendons les nouvelles.");
  };
  update();
  window.setInterval(update, 1000);
});

// A scheduled revision offers a refresh without discarding an unfinished form.
if (
  document.querySelector("[data-deadline]") &&
  document.body.dataset.stateUrl
) {
  const revision = Number(document.body.dataset.revision);
  window.setInterval(async () => {
    try {
      const response = await fetch(document.body.dataset.stateUrl, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      const payload = await response.json();
      if (
        payload.game.revision !== revision &&
        !document.querySelector("#refresh-notice")
      ) {
        const notice = document.createElement("div");
        notice.id = "refresh-notice";
        notice.className = "notice";
        const link = document.createElement("a");
        link.href = window.location.href;
        link.textContent = gettext(
          "De nouvelles lettres nous sont parvenues. Reprendre le livre à ce jour.",
        );
        notice.append(link);
        document.querySelector("#main").prepend(notice);
      }
    } catch {
      /* A transient failure leaves the current page usable. */
    }
  }, 15000);
}
