"""Reproducible 120-Moon observations, not an assertion of balanced human play.

Uses ordinary bot commands and existing bot decisions for all three houses.
Only the starting stock changes between paired runs; saved rules are untouched.
Run: python scripts/evaluate_strategy.py --seeds 8 --output artifacts/strategy.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation import engine  # noqa: E402
from simulation.calendar import closed_moon  # noqa: E402
from simulation.rules import tax_yield  # noqa: E402


def evaluate(seed, starting_stock):
    state = engine.new_state(economy_version=4)
    for player in state["players"].values():
        player["bot"] = True
    for city in state["cities"].values():
        city["stock"] = starting_stock
    counts = Counter()
    gaps = dict.fromkeys(state["players"], 0)
    longest = dict.fromkeys(state["players"], 0)
    outcomes = {}
    first_capture = None
    while state["status"] == "active":
        moon = state["month"]
        engine.bot_orders(state, seed)
        # Annual economy runs before departures and returns. These are the men
        # and current yields whose absence actually reduces this Moon's levy.
        counts["production_foregone"] += sum(
            engine.absent(state, city["id"]) * tax_yield(city["irrigation"], 4)
            for city in state["cities"].values()
        )
        _, audit = engine.advance_month(state, seed)
        executed = [order for order in state["orders"] if order.get("executed_month") == moon]
        counts["executed_orders"] += len(executed)
        counts["fees_paid"] += sum(
            order["cost"] for order in executed if order["kind"] in ("raid", "capture")
        ) + sum(order["fee"] for order in executed if order["kind"] == "convoy")
        counts["repair_orders"] += sum(order["kind"].startswith("repair") for order in executed)
        counts["capture_departures"] += sum(order["kind"] == "capture" for order in executed)
        for actor in gaps:
            if state["players"][actor]["eliminated"]:
                continue
            gaps[actor] = (
                0 if any(order["actor"] == actor for order in executed) else gaps[actor] + 1
            )
            longest[actor] = max(longest[actor], gaps[actor])
        counts["crew_moons"] += sum(work["status"] == "active" for work in state["works"])
        for mission_id, outcome in audit["outcomes"].items():
            outcomes[mission_id] = outcome
            counts["combat_" + outcome["kind"]] += 1
            counts["destroyed_resources"] += outcome.get("destroyed", 0)
            counts["military_deaths"] += outcome["attacker_deaths"] + outcome["defender_deaths"]
            counts["noncombat_deaths"] += outcome["noncombat_deaths"]
            if outcome["kind"] == "capture":
                counts["siege_attempts"] += outcome["outcome"] in ("held", "shortage")
                counts["sieges_held"] += outcome["outcome"] == "held"
                counts["siege_food"] += outcome["food_used"]
                if outcome["outcome"] in ("unopposed", "surrender", "assault", "shortage"):
                    counts["cities_conquered"] += 1
                    first_capture = first_capture or moon
            else:
                counts["military_raid_wins"] += outcome["outcome"] in (
                    "success",
                    "contested_win",
                    "unopposed",
                )
                counts["exterior_damage"] += outcome["damaged_work"] is not None
    orders = {order["id"]: order for order in state["orders"]}
    counts["settled_raid_net"] = 0
    for mission in state["expeditions"]:
        if mission["kind"] == "raid" and mission["status"] == "completed":
            net = mission.get("recovered_loot", 0) - orders[mission["id"]]["cost"]
            counts["settled_raids"] += 1
            counts["profitable_raids"] += net > 0
            counts["settled_raid_net"] += net
    final_moon = closed_moon(state)
    late_works = [
        {
            "kind": work["kind"],
            "completion": work["finish_month"],
            "complete_moons_in_service": max(0, final_moon - work["finish_month"]),
            "levy_moons_at_new_yield": max(0, final_moon - work["finish_month"])
            if work["kind"] == "irrigation"
            else None,
        }
        for work in state["works"]
        if work["finish_month"] >= 96
    ]
    return {
        "seed": seed,
        "starting_stock": starting_stock,
        "last_closed_moon": final_moon,
        "first_capture_moon": first_capture,
        "counts": dict(counts),
        "longest_no_order_by_house": longest,
        "late_works": late_works,
        "standings": engine.standings(state),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("artifacts/strategy.json"))
    args = parser.parse_args()
    runs = [
        evaluate(f"strategic-observation-{index}", stock)
        for stock in (600000, 900000)
        for index in range(args.seeds)
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"economy_version": 4, "runs": runs}, ensure_ascii=False, indent=2)
    )
    for stock in (600000, 900000):
        sample = [run for run in runs if run["starting_stock"] == stock]
        totals = Counter()
        for run in sample:
            totals.update(run["counts"])
        print(
            json.dumps(
                {
                    "stock": stock,
                    "runs": len(sample),
                    "totals": dict(totals),
                    "first_captures": [run["first_capture_moon"] for run in sample],
                    "longest_no_order": max(
                        max(run["longest_no_order_by_house"].values()) for run in sample
                    ),
                }
            )
        )


if __name__ == "__main__":
    main()
