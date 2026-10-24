const seatEntry = document.querySelector("[data-seat-entry]");
if (seatEntry) seatEntry.requestSubmit();

const waitingRoom = document.querySelector("[data-shared-lobby], [data-shared-operator], [data-shared-recruit]");
if (waitingRoom) {
  window.setInterval(async () => {
    try {
      const response = await fetch(waitingRoom.dataset.statusUrl, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) return;
      const state = await response.json();
      if (waitingRoom.hasAttribute("data-shared-lobby")) {
        if (state.started) window.location.replace(state.url);
        else if (state.cancelled) window.location.reload();
      }
      if (waitingRoom.hasAttribute("data-shared-operator") && waitingRoom.dataset.waiting === "true" && (state.started || state.cancelled)) window.location.reload();
      const startButton = document.querySelector("[data-shared-start]");
      if (startButton) startButton.disabled = !state.can_start;
      document.querySelectorAll("[data-spots-occupied]").forEach((element) => { element.textContent = state.occupied; });
      document.querySelectorAll("[data-spots-left]").forEach((element) => { element.textContent = state.spots_left; });
      document.querySelectorAll("[data-seat-house]").forEach((element) => { element.textContent = state.houses[element.dataset.seatHouse]; });
      if (waitingRoom.hasAttribute("data-shared-recruit")) {
        const status = waitingRoom.querySelector("[data-shared-status]");
        waitingRoom.querySelectorAll('input[name="actor"]').forEach((input) => {
          input.disabled = state.started || state.cancelled || !state.available.includes(input.value);
          if (input.disabled && input.checked) {
            input.checked = false;
            status.textContent = status.dataset.taken;
          }
        });
        if (state.started || state.cancelled) {
          const submit = waitingRoom.querySelector('button[type="submit"]');
          if (submit) submit.disabled = true;
          status.textContent = status.dataset.closed;
        }
      }
      document.querySelectorAll("[data-seat-state]").forEach((seat) => {
        seat.textContent = state.seats[seat.dataset.seatState]
          ? seat.dataset.joined
          : seat.dataset.waiting;
      });
    } catch {
      // The native refresh link remains available after a connection failure.
    }
  }, 2000);
}
