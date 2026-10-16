from simulation.engine import new_state


def rich_state(version="V1"):
    state = new_state(version, opponents="passive", calendar_version=1)
    for city in state["cities"].values():
        city["stock"] = 2_400_000
    return state
