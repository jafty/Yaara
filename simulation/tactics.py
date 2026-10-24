"""Pure frontier arithmetic and own-territory route selection."""

from fractions import Fraction

from .rules import losses


def enabled(state):
    return state.get("strategy_version", 1) >= 2


def field_result(first_count, first_strength, second_count, second_strength):
    if min(first_count, first_strength, second_count, second_strength) <= 0:
        raise ValueError("Field forces must be positive")
    engaged = min(first_count, second_count)
    first_stronger = first_strength >= second_strength
    ratio = Fraction(max(first_strength, second_strength), min(first_strength, second_strength))
    if ratio < Fraction(5, 4):
        dead = losses(engaged, Fraction(6, 100))
        return dead, dead, False, False, "contested"
    overwhelming = ratio >= 2
    strong_dead = 0 if overwhelming else losses(engaged, Fraction(2, 100))
    weak_dead = losses(engaged, Fraction(4 if overwhelming else 12, 100))
    first_dead, second_dead = (
        (strong_dead, weak_dead) if first_stronger else (weak_dead, strong_dead)
    )
    return (
        first_dead,
        second_dead,
        first_stronger,
        not first_stronger,
        "overwhelming" if overwhelming else "decisive",
    )


def launch_city(state, actor, target, contributions):
    adjacent = set()
    for first, second in state["links"]:
        if first == target:
            adjacent.add(second)
        elif second == target:
            adjacent.add(first)
    candidates = []
    for city_id in sorted(adjacent):
        if state["cities"][city_id]["owner"] != actor:
            continue
        reached, todo = {city_id}, [city_id]
        while todo:
            current = todo.pop()
            for first, second in state["links"]:
                neighbor = second if first == current else first if second == current else None
                if (
                    neighbor
                    and neighbor not in reached
                    and state["cities"][neighbor]["owner"] == actor
                ):
                    reached.add(neighbor)
                    todo.append(neighbor)
        if set(contributions) <= reached:
            candidates.append(city_id)
    return (
        min(candidates, key=lambda key: (-contributions.get(key, 0), key)) if candidates else None
    )
