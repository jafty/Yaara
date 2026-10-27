"use strict";

let pageTimers = [];
let headerObserver = null;
let sheetExpanded = false;
function sizeSheet(expanded) {
  const workspace = document.querySelector(".map-workspace");
  const button = workspace?.querySelector("[data-sheet-expand]");
  if (!button) return;
  sheetExpanded = expanded;
  workspace.classList.toggle("is-expanded", expanded);
  const coversMap =
    expanded ||
    getComputedStyle(workspace.querySelector(".context-sheet")).position === "absolute";
  const map = workspace.querySelector(".realm-map");
  map.inert = coversMap;
  document.querySelector(".reign-header").inert = coversMap;
  if (coversMap) map.setAttribute("aria-hidden", "true");
  else map.removeAttribute("aria-hidden");
  button.setAttribute("aria-expanded", String(expanded));
  const label = expanded
    ? gettext("Réduire le panneau")
    : gettext("Agrandir le panneau");
  button.setAttribute("aria-label", label);
  button.title = label;
}
function measureHeader() {
  const header = document.querySelector(".reign-header");
  if (!header) return;
  const height =
    getComputedStyle(header).position === "sticky"
      ? header.getBoundingClientRect().height
      : 0;
  document.documentElement.style.setProperty("--header-height", `${height}px`);
}
function folioFragment() {
  if (!location.hash || document.querySelector(".map-workspace")) return null;
  return document.getElementById(decodeURIComponent(location.hash.slice(1)));
}
function alignFolioFragment() {
  measureHeader();
  const target = folioFragment();
  if (target) target.scrollIntoView({ block: "start", behavior: "instant" });
}
function initializePage() {
  pageTimers.forEach(window.clearInterval);
  pageTimers = [];
  if (headerObserver) headerObserver.disconnect();
  const expand = document.querySelector("[data-sheet-expand]");
  if (expand) {
    if (!document.querySelector(".panel-close")) sheetExpanded = false;
    expand.hidden = false;
    sizeSheet(sheetExpanded);
    expand.addEventListener("click", () => sizeSheet(!sheetExpanded));
  }
  const header = document.querySelector(".reign-header");
  if (header) {
    measureHeader();
    headerObserver = new ResizeObserver(() => {
      measureHeader();
      if (document.querySelector("[data-sheet-expand]"))
        sizeSheet(sheetExpanded);
      const target = folioFragment();
      if (!target) return;
      const top = target.getBoundingClientRect().top;
      if (top >= 0 && top < header.getBoundingClientRect().bottom)
        alignFolioFragment();
    });
    headerObserver.observe(header);
  }

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
      const shortfall =
        form.dataset.localFunding === "true"
          ? selected.reduce(
              (sum, input) => sum + Number(input.dataset.shortfall),
              0,
            )
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
                ? gettext(
                    "Il manque %(amount)s Mesures dans les cités choisies.",
                  )
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
    const kinds = [
      ...document.querySelectorAll('input[name="kind"][type="radio"]'),
    ];
    const form = targetSelect.closest("form");
    const plan = form.closest(".context-sheet") || form;
    const rows = [...document.querySelectorAll(".contribution")];
    const format = new Intl.NumberFormat(document.documentElement.lang);
    const updateTotals = () => {
      const counts = rows.map((row) => {
        const value = Number(row.querySelector("input").value || 0);
        return Number.isSafeInteger(value) && value > 0 ? value : 0;
      });
      const total = rows.reduce((sum, row, index) => sum + counts[index], 0);
      drawDraftRoute(targetSelect.value, rows, counts);
      const kind = kinds.find((input) => input.checked).value;
      const price = prices[kind];
      const cost = price.base + total * price.per_person;
      plan.querySelector("[data-carry-limit]").textContent = format.format(
        rows.reduce(
          (sum, row, index) => sum + counts[index] * Number(row.dataset.carry),
          0,
        ),
      );
      plan.querySelector("[data-loot-preview]").hidden = kind !== "raid";
      form.querySelector(".loot-preview").hidden = kind !== "raid";
      document.querySelector("#army-total").textContent = format.format(total);
      document.querySelector("#army-cost").textContent = format.format(cost);
      // Match the server's whole-Measure Hamilton allocation and city-ID tie order.
      const fees = counts.map((count) =>
        total ? Math.floor((price.base * count) / total) : 0,
      );
      const ranked = rows
        .map((row, index) => ({
          index,
          id: row.dataset.origin,
          remainder: total ? (price.base * counts[index]) % total : 0,
        }))
        .sort((a, b) => b.remainder - a.remainder || a.id.localeCompare(b.id));
      if (total) {
        const remaining = price.base - fees.reduce((sum, fee) => sum + fee, 0);
        ranked.slice(0, remaining).forEach((row) => {
          fees[row.index] += 1;
        });
      }
      let shortfall = 0;
      rows.forEach((row, index) => {
        const chargeForOrigin = fees[index] + counts[index] * price.per_person;
        const remainingStock = Number(row.dataset.freeStock) - chargeForOrigin;
        const need =
          Math.max(0, Number(row.dataset.present) - counts[index]) * 500;
        const reserves = row.querySelector(".origin-reserves");
        if (reserves) {
          reserves.textContent = interpolate(
            gettext(
              "Après départ : %(remaining)s Mesures libres ; besoin d’un mois de siège : %(need)s.",
            ),
            {
              remaining: format.format(remainingStock),
              need: format.format(need),
            },
            true,
          );
          row.querySelector("[data-origin-warning]").textContent =
            remainingStock < need
              ? gettext(
                  "Attention : moins d’un mois de réserves de siège après ce départ.",
                )
              : "";
        }
        const note = row.querySelector(".origin-funding");
        if (!note) return;
        const charge = fees[index] + counts[index] * price.per_person;
        const available = Number(row.dataset.freeStock);
        const missing = Math.max(0, charge - available);
        shortfall += missing;
        note.textContent =
          interpolate(
            gettext(
              "Part : %(charge)s · Disponibles : %(available)s Mesures.",
            ),
            {
              charge: format.format(charge),
              available: format.format(available),
            },
            true,
          ) +
          (missing
            ? " " +
              interpolate(
                gettext("Il manque %(amount)s Mesures dans cette cité."),
                { amount: format.format(missing) },
                true,
              )
            : "");
      });
      if (form.dataset.localFunding !== "true") {
        shortfall = Math.max(0, cost - Number(form.dataset.freeStock));
      }
      plan.querySelector("[data-expedition-budget]").textContent = shortfall
        ? interpolate(
            gettext(
              "Il manque %(amount)s Mesures pour cette expédition. Aucun moyen n’est réservé.",
            ),
            { amount: format.format(shortfall) },
            true,
          )
        : "";
      const breakEven = form.querySelector("[data-raid-break-even]");
      breakEven.hidden = kind !== "raid";
      breakEven.textContent = interpolate(
        gettext(
          "Il faudra conserver au moins %(amount)s Mesures de butin pour rembourser cette expédition.",
        ),
        { amount: format.format(cost) },
        true,
      );
      const help = document.querySelector("#mission-help");
      help.textContent =
        interpolate(
          gettext("Minimum : %(minimum)s Fidèles."),
          { minimum: price.minimum },
          true,
        ) +
        (total < price.minimum
          ? " " +
            interpolate(
              gettext("Encore %(count)s à mobiliser."),
              { count: price.minimum - total },
              true,
            )
          : "");
    };
    const updateOrigins = () => {
      const eligible = origins[targetSelect.value] || [];
      rows.forEach((row) => {
        const input = row.querySelector("input");
        input.disabled = !eligible.includes(row.dataset.origin);
        row
          .querySelectorAll(
            "[data-contingent-controls] button",
          )
          .forEach((control) => {
            control.disabled = input.disabled || Number(input.max) === 0;
          });
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
    kinds.forEach((input) => input.addEventListener("change", updateTotals));
    rows.forEach((row) =>
      row.querySelector("input").addEventListener("input", updateTotals),
    );
    rows.forEach((row) => {
      const controls = row.querySelector("[data-contingent-controls]");
      if (!controls) return;
      const number = row.querySelector('input[type="number"]');
      const setCount = (value) => {
        number.value = Math.max(0, Math.min(Number(number.max), value));
        updateTotals();
      };
      controls.querySelectorAll("[hidden]").forEach((control) => {
        control.hidden = false;
      });
      controls.querySelectorAll("[data-adjust]").forEach((button) => {
        button.addEventListener("click", () =>
          setCount(Number(number.value || 0) + Number(button.dataset.adjust)),
        );
      });
      controls
        .querySelector("[data-maximum]")
        .addEventListener("click", () => setCount(Number(number.max)));
    });
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
    pageTimers.push(window.setInterval(update, 1000));
  });

  // A scheduled revision offers a refresh without discarding an unfinished form.
  if (
    document.querySelector("[data-deadline]") &&
    document.body.dataset.stateUrl
  ) {
    const revision = Number(document.body.dataset.revision);
    pageTimers.push(
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
            (
              document.querySelector(".workspace-notices") ||
              document.querySelector("#main")
            ).prepend(notice);
          }
        } catch {
          /* A transient failure leaves the current page usable. */
        }
      }, 15000),
    );
  }

  // A draft uses only the public road graph and own contributions. Server review is authoritative.
  function drawDraftRoute(targetId, rows, counts) {
    const graphElement = document.querySelector("#map-graph");
    const layer = document.querySelector("#draft-route");
    if (!graphElement || !layer) return;
    const graph = JSON.parse(graphElement.textContent);
    layer.replaceChildren();
    document
      .querySelectorAll(".draft-road")
      .forEach((edge) => edge.classList.remove("draft-road"));
    const contributions = Object.fromEntries(
      rows
        .map((row, i) => [row.dataset.origin, counts[i]])
        .filter(([, count]) => count > 0),
    );
    if (!Object.keys(contributions).length) return;
    const adjacent = graph.links.flatMap(([a, b]) =>
      a === targetId ? [b] : b === targetId ? [a] : [],
    );
    const candidates = adjacent
      .filter((id) => graph.owned.includes(id))
      .map((id) => {
        const reached = new Set([id]);
        const todo = [id];
        while (todo.length) {
          const current = todo.shift();
          for (const [a, b] of graph.links) {
            const neighbor = a === current ? b : b === current ? a : null;
            if (
              neighbor &&
              graph.owned.includes(neighbor) &&
              !reached.has(neighbor)
            ) {
              reached.add(neighbor);
              todo.push(neighbor);
            }
          }
        }
        return { id, reached };
      })
      .filter((candidate) =>
        Object.keys(contributions).every((id) => candidate.reached.has(id)),
      )
      .sort(
        (a, b) =>
          (contributions[b.id] || 0) - (contributions[a.id] || 0) ||
          a.id.localeCompare(b.id),
      );
    if (!candidates.length) return;
    const departure = candidates[0];
    const origin = graph.cities.find((city) => city.id === departure.id);
    const target = graph.cities.find((city) => city.id === targetId);
    for (const edge of document.querySelectorAll(".map-connection")) {
      if (
        departure.reached.has(edge.dataset.first) &&
        departure.reached.has(edge.dataset.second)
      )
        edge.classList.add("draft-road");
    }
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const dx = target.x - origin.x,
      dy = target.y - origin.y;
    const distance = Math.hypot(dx, dy);
    const inset = Math.min(45, distance / 4) / Math.max(distance, 1);
    path.setAttribute(
      "d",
      `M ${origin.x + dx * inset} ${origin.y + dy * inset} L ${target.x - dx * inset} ${target.y - dy * inset}`,
    );
    path.setAttribute("class", "march-line");
    path.setAttribute("marker-end", "url(#march-tip)");
    layer.append(path);
  }

  // Read receipts are browser-local preferences; reports and unresolved alerts stay untouched.
  const mailbox = document.querySelector("[data-mail-key]");
  if (mailbox) {
    const key = `yaara-read:${mailbox.dataset.mailKey}`;
    let read;
    try {
      read = new Set(JSON.parse(localStorage.getItem(key) || "[]"));
    } catch {
      read = new Set();
    }
    mailbox.querySelectorAll("[data-read-report]").forEach((button) => {
      const article = document.getElementById(button.dataset.readReport);
      if (read.has(article.id)) return;
      article.classList.add("unread-report");
      button.hidden = false;
      button.addEventListener("click", () => {
        read.add(article.id);
        try {
          localStorage.setItem(key, JSON.stringify([...read]));
        } catch {
          /* Optional preference. */
        }
        article.classList.remove("unread-report");
        button.hidden = true;
      });
    });
  }
}
initializePage();

// Same-document hashes and font reflow can follow a change in header height.
document.fonts.ready.then(alignFolioFragment);
window.addEventListener("hashchange", alignFolioFragment);
window.addEventListener("resize", () => sizeSheet(sheetExpanded));

// Context links keep the cartographic surface mounted as the application's home.
// Native URLs remain fully usable with JavaScript disabled or a failed request.
let contextRequest = null;
let renderedURL = location.pathname + location.search;
async function openContext(url, push = true) {
  if (contextRequest) contextRequest.abort();
  const previousCity = new URL(location.href).searchParams.get("city");
  const controller = new AbortController();
  contextRequest = controller;
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      window.location.assign(url);
      return;
    }
    const next = new DOMParser().parseFromString(
      await response.text(),
      "text/html",
    );
    if (controller.signal.aborted) return;
    if (!next.querySelector(".map-workspace")) {
      window.location.assign(url);
      return;
    }
    const currentSheet = document.querySelector(".context-sheet");
    const nextSheet = next.querySelector(".context-sheet");
    const reducedMotion = matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (
      currentSheet &&
      nextSheet &&
      ["city-sheet", "mail-panel"].some(
        (kind) =>
          currentSheet.classList.contains(kind) &&
          nextSheet.classList.contains(kind),
      )
    ) {
      currentSheet.replaceChildren(...nextSheet.childNodes);
      currentSheet.className = nextSheet.className + " sheet-retained";
      nextSheet.replaceWith(currentSheet);
      if (!reducedMotion)
        currentSheet
          .querySelector(".sheet-body")
          .animate([{ opacity: 0.65 }, { opacity: 1 }], {
            duration: 150,
            easing: "ease-out",
          });
    } else if (currentSheet && !reducedMotion) {
      await currentSheet.animate(
        [
          { opacity: 1, transform: "translateY(0)" },
          { opacity: 0, transform: "translateY(8px)" },
        ],
        { duration: 120, easing: "ease-in" },
      ).finished;
      if (controller.signal.aborted) return;
    }
    const currentMap = document.querySelector(".map-workspace > .realm-map");
    const map = next.querySelector(".map-workspace > .realm-map");
    if (currentMap && map) {
      // Keep decoded artwork mounted between views of the same authorized snapshot.
      if (currentMap.dataset.mapRevision === map.dataset.mapRevision) {
        const cities = currentMap.querySelectorAll(".map-city");
        map.querySelectorAll(".map-city").forEach((city, index) => {
          for (const attribute of ["href", "aria-current"]) {
            if (city.hasAttribute(attribute))
              cities[index].setAttribute(
                attribute,
                city.getAttribute(attribute),
              );
            else cities[index].removeAttribute(attribute);
          }
        });
        const roads = currentMap.querySelectorAll(".map-connection");
        map.querySelectorAll(".map-connection").forEach((road, index) => {
          roads[index].setAttribute("class", road.getAttribute("class"));
        });
        currentMap.querySelector("#draft-route").replaceChildren();
      } else {
        currentMap.replaceChildren(...map.childNodes);
        currentMap.dataset.mapRevision = map.dataset.mapRevision;
      }
      map.replaceWith(currentMap);
    }
    document.querySelector("#main").replaceWith(next.querySelector("#main"));
    document
      .querySelector(".reign-header")
      .replaceWith(next.querySelector(".reign-header"));
    const currentCalendar = document.querySelector(".moon-banner");
    const nextCalendar = next.querySelector(".moon-banner");
    if (currentCalendar) currentCalendar.remove();
    if (nextCalendar) {
      document.querySelector(".reign-header").after(nextCalendar);
    }
    document.body.className = next.body.className;
    document.body.dataset.revision = next.body.dataset.revision;
    document.title = next.title;
    if (push) history.pushState({ yaaraContext: true }, "", url);
    renderedURL =
      new URL(url, location.href).pathname + new URL(url, location.href).search;
    initializePage();
    const hash = new URL(url, location.href).hash;
    const focus = hash
      ? document.getElementById(decodeURIComponent(hash.slice(1)))
      : document.querySelector("#context-title");
    if (focus && focus.getClientRects().length) {
      focus.setAttribute("tabindex", "-1");
      focus.focus({ preventScroll: true });
      const body = focus.closest(".sheet-body");
      if (body)
        body.scrollTop =
          focus.getBoundingClientRect().top -
          body.getBoundingClientRect().top -
          12;
    } else {
      const cities = [...document.querySelectorAll(".map-city")];
      const city =
        cities.find(
          (link) =>
            new URL(link.getAttribute("href"), location.href).searchParams.get(
              "city",
            ) === previousCity,
        ) || cities[0];
      if (city) city.focus({ preventScroll: true });
    }
  } catch (error) {
    if (error.name !== "AbortError") window.location.assign(url);
  }
}
document.addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (
    !link ||
    event.defaultPrevented ||
    event.button ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey ||
    link.getAttribute("target") ||
    link.hasAttribute("download")
  )
    return;
  const url = new URL(link.getAttribute("href"), location.href);
  if (
    url.origin !== location.origin ||
    url.pathname !== location.pathname ||
    !document.querySelector(".map-workspace")
  )
    return;
  const tab = url.searchParams.get("tab") || "map";
  if (!["map", "mail"].includes(tab)) return;
  if (url.search === location.search && url.hash) return;
  event.preventDefault();
  openContext(url.href);
});
window.addEventListener("popstate", () => {
  if (location.pathname + location.search === renderedURL) return;
  if (document.querySelector(".map-workspace"))
    openContext(location.href, false);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || event.defaultPrevented) return;
  if (sheetExpanded) {
    sizeSheet(false);
    document.querySelector("[data-sheet-expand]")?.focus({ preventScroll: true });
    event.preventDefault();
    return;
  }
  const close = document.querySelector(".map-workspace .panel-close");
  if (close) {
    event.preventDefault();
    openContext(new URL(close.getAttribute("href"), location.href).href);
  }
});
