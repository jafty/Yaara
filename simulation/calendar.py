"""Pure calendar compatibility for elapsed-month saves and open-Moon reigns."""


def open_calendar(state):
    return state.get("calendar_version", 1) == 2


def closing_moon(state):
    return state["month"] if open_calendar(state) else state["month"] + 1


def closed_moon(state):
    return state["month"] - int(open_calendar(state) and state["status"] != "finished")
