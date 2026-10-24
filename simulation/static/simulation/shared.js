const seatEntry = document.querySelector("[data-seat-entry]");
if (seatEntry) seatEntry.requestSubmit();

const waitingRoom = document.querySelector("[data-shared-lobby], [data-shared-operator]");
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
      const startButton = document.querySelector("[data-shared-start]");
      if (startButton) startButton.disabled = !state.can_start;
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
