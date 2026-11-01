"""Paired offline observations of three declared heuristics, not balanced human play.

Run: uv run python scripts/evaluate_consolidation.py --seeds 100
Each seed rotates early expansion, patient counterexpansion and seasonal raiding
through all three positions, under saved strategy 2, revised strategy 3, and the
explicit strategy-3 wall experiment. Policies receive owned state, public roads,
owners and walls, and recipient reports. Only the observer reads hidden state.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation import engine  # noqa: E402
from simulation.calendar import closed_moon  # noqa: E402
from simulation.rules import (  # noqa: E402
    RuleError,
    allocate,
    integrity_fraction,
    tax_yield,
    work_prices,
)

POLICIES = ("early", "patient", "raider")
SCENARIOS = {"baseline": 2, "consolidation": 3, "active_walls": 3}
CAPTURE_OUTCOMES = {"unopposed", "surrender", "assault", "shortage"}
WORK_KINDS = ("irrigation", "walls", "forge", "watch", "storage", "shelter", "transport", "siege")


def observe(state, actor, reports):
    """Construct the policy boundary explicitly; opponent private fields never cross it."""
    funds, people = engine.reservations(state)
    busy = engine.busy_cities(state)
    owned = {}
    for city in engine.owned_cities(state, actor):
        city_id = city["id"]
        frozen = state.get("strategy_version", 1) >= 3 and engine.consolidating(state, city)
        owned[city_id] = {
            **{kind: city[kind] for kind in WORK_KINDS},
            "population": city["population"],
            "stock": city["stock"],
            "tax": city["tax"],
            "capacity": engine.capacity(city, state["economy_version"]),
            "funds": 0 if frozen else city["stock"] - funds[city_id],
            "men": engine.deployable_fideles(state, city_id) - people[city_id],
            "busy": city_id in busy,
            "frozen": frozen,
            "integrity": integrity_fraction(city.get("integrity", 100)),
            "damaged_works": list(city.get("damaged_works", [])),
        }
    return {
        "actor": actor,
        "moon": state["month"],
        "end": state["config"]["reign_months"],
        "owned": owned,
        "public": {
            key: {"owner": city["owner"], "walls": city["walls"]}
            for key, city in state["cities"].items()
        },
        "links": [list(edge) for edge in state["links"]],
        "components": {
            city_id: sorted(engine.connected_component(state, city_id)) for city_id in owned
        },
        "eligible": {
            key: sorted(engine.eligible_origins(state, actor, key))
            for key, city in state["cities"].items()
            if city["owner"] != actor
        },
        "convoys": [
            {"origin": convoy["origin"], "target": convoy["target"], "cargo": convoy["cargo"]}
            for convoy in state.get("convoys", [])
            if convoy["actor"] == actor and convoy["status"] != "completed"
        ],
        "reports": [
            {
                "kind": report["kind"],
                "moon": report["moon"],
                "city": report.get("content", {}).get("city_id"),
                "scene": report.get("content", {}).get("scene", ""),
            }
            for report in reports
            if report["recipient"] == actor
        ],
    }


def frontier(view, city_id):
    return any(
        view["public"][second if first == city_id else first]["owner"] != view["actor"]
        for first, second in view["links"]
        if city_id in (first, second)
    )


def reserve(view, city_id, policy):
    return (
        150000
        if policy == "early"
        else 500000
        if policy == "patient" and frontier(view, city_id)
        else 250000
    )


def expedition_proposals(view, kind, policy, seed):
    targets = sorted(view["eligible"])
    engine.random_stream(seed, view["moon"], f"evaluation-target:{view['actor']}").shuffle(targets)
    if kind == "capture":
        targets.sort(key=lambda key: view["public"][key]["walls"])
    for target in targets:
        sources = view["eligible"][target]
        if kind == "raid":
            sources = sorted(sources, key=lambda key: (-view["owned"][key]["men"], key))
            for origin in sources:
                city = view["owned"][origin]
                if city["men"] >= 75 and city["funds"] - 65000 >= reserve(view, origin, policy):
                    yield {"kind": "raid", "target": target, "contributions": {origin: 60}}
                    break
            continue
        components = {tuple(view["components"][origin]) for origin in sources}
        for component in sorted(components):
            budgets = {
                origin: min(
                    max(0, view["owned"][origin]["men"] - 15),
                    max(
                        0,
                        (view["owned"][origin]["funds"] - reserve(view, origin, policy) - 50000)
                        // 2000,
                    ),
                )
                for origin in component
            }
            total = min(240, sum(budgets.values()))
            if total >= 150:
                yield {
                    "kind": "capture",
                    "target": target,
                    "contributions": {
                        key: value for key, value in allocate(total, budgets).items() if value
                    },
                }


def supply_proposals(view, policy):
    threatened = {
        report["city"]
        for report in view["reports"]
        if report["moon"] >= view["moon"] - 6
        and (report["kind"] == "warning" or report["scene"].startswith("received-capture"))
    }
    supplying = {convoy["target"] for convoy in view["convoys"]}
    busy_origins = {convoy["origin"] for convoy in view["convoys"]}
    for target in sorted(threatened & view["owned"].keys() - supplying):
        city = view["owned"][target]
        need = city["population"] * 1000 - city["stock"]
        if need <= 0:
            continue
        for origin in sorted(view["owned"], key=lambda key: -view["owned"][key]["funds"]):
            if (
                origin == target
                or origin in busy_origins
                or origin not in view["components"][target]
            ):
                continue
            source = view["owned"][origin]
            fee = [10, 7, 5][source["transport"]]
            cargo = min(
                500000, need, (source["funds"] - reserve(view, origin, policy)) * 100 // (100 + fee)
            )
            if cargo >= 100000:
                yield {"kind": "convoy", "origin": origin, "target": target, "cargo": cargo}


def construction_proposals(view, policy):
    candidates = []
    prices = work_prices(4)
    for city_id, city in view["owned"].items():
        if city["busy"] or city["frozen"]:
            continue
        border = frontier(view, city_id)
        priorities = []
        if city["irrigation"] == 0:
            priorities.append((0, "irrigation"))
        if border and city["walls"] == 0:
            priorities.append((1 if policy == "patient" else 3, "walls"))
        if city["forge"] < 2:
            priorities.append((2 + city["forge"], "forge"))
        if border and city["watch"] == 0:
            priorities.append((4, "watch"))
        if city["stock"] + city["tax"] > city["capacity"] and city["storage"] < 3:
            priorities.append((1, "storage"))
        if city["irrigation"] < 3:
            priorities.append((5 + city["irrigation"], "irrigation"))
        if border and city["walls"] < 2:
            priorities.append((8, "walls"))
        if border and city["shelter"] == 0:
            priorities.append((8, "shelter"))
        if city["integrity"] < 100:
            priorities.append((2, "repair"))
        if city["forge"] == 2:
            priorities.append((9, "forge"))
        if policy != "patient" and city["siege"] < 1:
            priorities.append((10, "siege"))
        for priority, kind in priorities:
            if kind in city["damaged_works"] or (kind == "walls" and city["integrity"] < 100):
                continue
            level = city["walls"] if kind == "repair" else city[kind] + 1
            cost, duration = (
                (20000, 2) if kind == "repair" and level == 0 else prices[kind][level - 1]
            )
            # Irrigation must have time to repay its cost after completion.
            payback = [20, 27, 22][level - 1] if kind == "irrigation" else 0
            if view["moon"] + duration + payback > view["end"]:
                continue
            if city["funds"] - cost >= reserve(view, city_id, policy):
                candidates.append((priority, city_id, kind))
    for _, city_id, kind in sorted(set(candidates)):
        yield {"kind": kind, "cities": [city_id]}


def proposals(view, policy, seed, decision_every=1):
    """Fixed choices are public and reproducible; no target private state enters a policy."""
    if policy == "patient":
        yield from supply_proposals(view, policy)
    seasonal_window = any(
        (view["moon"] - 1 + offset) % 12 in (4, 7, 10) for offset in range(min(12, decision_every))
    )
    if policy == "raider" and seasonal_window:
        yield from expedition_proposals(view, "raid", policy, seed)
    if view["moon"] >= {"early": 1, "patient": 25, "raider": 49}[policy]:
        yield from expedition_proposals(view, "capture", policy, seed)
    yield from construction_proposals(view, policy)


def record_raid_absence(state, ledger):
    """Measure the same pre-departure absence used by that Moon's levy accrual."""
    for mission in state["expeditions"]:
        if mission["kind"] != "raid" or mission["status"] == "completed":
            continue
        lost = sum(
            count * tax_yield(state["cities"][origin]["irrigation"], 4)
            for origin, count in mission["cohorts"].items()
            if origin not in mission.get("detached_origins", [])
            and origin not in mission.get("arrived_origins", [])
            and state["cities"][origin]["owner"] == mission["actor"]
        )
        ledger[mission["id"]] = ledger.get(mission["id"], 0) + lost


def raid_ledger(state, actor, absence):
    orders = {order["id"]: order for order in state["orders"]}
    totals = Counter(
        {
            "settled_raids": 0,
            "unsettled_raids": 0,
            "settled_raid_fees": 0,
            "settled_raid_loot": 0,
            "settled_raid_absence": 0,
        }
    )
    for mission in state["expeditions"]:
        if mission["actor"] != actor or mission["kind"] != "raid":
            continue
        if mission["status"] != "completed":
            totals["unsettled_raids"] += 1
            continue
        totals["settled_raids"] += 1
        totals["settled_raid_fees"] += orders[mission["id"]]["cost"]
        totals["settled_raid_loot"] += mission.get("recovered_loot", 0)
        totals["settled_raid_absence"] += absence.get(mission["id"], 0)
    totals["settled_raid_net_after_fees"] = (
        totals["settled_raid_loot"] - totals["settled_raid_fees"]
    )
    totals["settled_raid_net_after_absence"] = (
        totals["settled_raid_net_after_fees"] - totals["settled_raid_absence"]
    )
    return dict(totals)


def record_validation_failure(counts, state, actor, spec, error):
    """Classify observed rejections without feeding another house's orders to a policy."""
    if spec["kind"] != "capture" or "Une autre expédition est déjà engagée" not in str(error):
        return
    counts["capture_target_exclusivity_rejections"] += 1
    blocking = next(
        order
        for order in state["orders"]
        if order["kind"] in ("raid", "capture")
        and order["target"] == spec["target"]
        and order["status"] in ("confirmed", "active")
    )
    counts["capture_rejections_pending_" + blocking["kind"]] += 1
    counts[
        "capture_rejections_own_pending"
        if blocking["actor"] == actor
        else "capture_rejections_enemy_pending"
    ] += 1


def evaluate(seed, rotation, scenario, reign_months=120, decision_every=1):
    state = engine.new_state(
        opponents="passive",
        reign_months=reign_months,
        economy_version=4,
        strategy_version=SCENARIOS[scenario],
    )
    if scenario == "active_walls":
        state["config"]["experimental_active_walls"] = True
    policies = {
        actor: POLICIES[(index + rotation) % 3] for index, actor in enumerate(state["players"])
    }
    metrics = {actor: Counter() for actor in state["players"]}
    counts = Counter({"capture_target_exclusivity_rejections": 0})
    reports, absence, losses, captures = [], {}, [], []
    order_moons = {actor: [] for actor in state["players"]}
    while state["status"] == "active":
        moon = state["month"]
        for actor, policy in policies.items():
            if state["players"][actor]["eliminated"]:
                continue
            metrics[actor]["active_moons"] += 1
            if (moon - 1) % decision_every:
                continue
            metrics[actor]["decision_windows"] += 1
            view = observe(state, actor, reports)
            for attempt, spec in enumerate(proposals(view, policy, seed, decision_every)):
                metrics[actor]["validation_attempts"] += 1
                raid_target = spec["kind"] == "capture" and any(
                    order["kind"] == "raid"
                    and order["target"] == spec["target"]
                    and order["status"] in ("confirmed", "active")
                    for order in state["orders"]
                )
                try:
                    engine.confirm_order(state, actor, spec, f"eval-{actor}-{moon}-{attempt}")
                except RuleError as error:
                    metrics[actor]["validation_rejections"] += 1
                    record_validation_failure(counts, state, actor, spec, error)
                    continue
                metrics[actor]["accepted_orders"] += 1
                counts["capture_orders_accepted_on_raid_targets"] += raid_target
                order_moons[actor].append(moon)
                break
        record_raid_absence(state, absence)
        for mission in state["expeditions"]:
            if mission["kind"] == "occupation" and mission["status"] == "occupying":
                metrics[mission["actor"]]["occupation_missions_moons"] += 1
                metrics[mission["actor"]]["occupation_men_moons"] += sum(
                    mission["cohorts"].values()
                )
        if SCENARIOS[scenario] >= 3:
            for city in state["cities"].values():
                metrics[city["owner"]]["frozen_city_moons"] += engine.consolidating(state, city)
        owners = {key: city["owner"] for key, city in state["cities"].items()}
        city_counts = Counter(owners.values())
        events, audit = engine.advance_month(state, seed)
        reports = [report for report in reports if report["moon"] >= moon - 6]
        reports.extend({**event, "moon": moon} for event in events)
        for order in state["orders"]:
            if order.get("executed_month") == moon:
                metrics[order["actor"]]["executed_orders"] += 1
                metrics[order["actor"]]["spending_" + order["kind"]] += order["cost"]
        for city_id, city in state["cities"].items():
            if city["owner"] != owners[city_id]:
                captures.append({"moon": moon, "city": city_id, "actor": city["owner"]})
                losses.append(
                    {
                        "moon": moon,
                        "city": city_id,
                        "actor": owners[city_id],
                        "territory_before": city_counts[owners[city_id]],
                        "recovered_moon": None,
                    }
                )
        current = Counter(city["owner"] for city in state["cities"].values())
        for loss in losses:
            if (
                loss["recovered_moon"] is None
                and moon > loss["moon"]
                and current[loss["actor"]] >= loss["territory_before"]
            ):
                loss["recovered_moon"] = moon
        for outcome in audit["outcomes"].values():
            row = metrics[outcome["attacker"]]
            row["combat_" + outcome["kind"]] += 1
            row["attacker_deaths"] += outcome["attacker_deaths"]
            row["defender_deaths_inflicted"] += outcome["defender_deaths"]
            if outcome["kind"] == "capture":
                row["capture_" + outcome["outcome"]] += 1
                row["siege_food_imposed"] += outcome["food_used"]
                row["active_wall_deaths"] += outcome.get("active_wall_losses", 0)
                wall = state["cities"][outcome["target"]]["walls"]
                counts[f"wall_{wall}_capture_{outcome['outcome']}"] += 1
        counts["raid_arrivals_protected"] += sum(
            event["title"] == "Pillage impossible" for event in events
        )
    standings = engine.standings(state)
    winner_count = sum(row["rank"] == 1 for row in standings)
    for row in standings:
        actor = row["actor"]
        metrics[actor].update(raid_ledger(state, actor, absence))
        metrics[actor]["cities"] = row["cities"]
        metrics[actor]["win_share"] = 1 / winner_count if row["rank"] == 1 else 0
        metrics[actor]["full_conquest"] = row["cities"] == 9
        metrics[actor]["city_losses"] = sum(loss["actor"] == actor for loss in losses)
        metrics[actor]["recoveries"] = sum(
            loss["actor"] == actor and loss["recovered_moon"] is not None for loss in losses
        )
        metrics[actor]["recovered_after_loss"] = metrics[actor]["recoveries"] > 0
        metrics[actor]["won_after_city_loss"] = bool(
            metrics[actor]["city_losses"] and metrics[actor]["win_share"]
        )
        active_moons = metrics[actor]["active_moons"]
        metrics[actor]["orders_per_active_moon"] = metrics[actor]["accepted_orders"] / active_moons
        dates = [0, *order_moons[actor], active_moons + 1]
        metrics[actor]["longest_moons_without_order"] = max(
            second - first - 1 for first, second in zip(dates, dates[1:])
        )
    return {
        "seed": seed,
        "rotation": rotation,
        "scenario": scenario,
        "strategy_version": SCENARIOS[scenario],
        "policies": policies,
        "last_closed_moon": closed_moon(state),
        "first_capture": captures[0] if captures else None,
        "captures": captures,
        "losses": losses,
        "metrics": {key: dict(value) for key, value in metrics.items()},
        "order_moons": order_moons,
        "counts": dict(counts),
        "standings": standings,
    }


def summarize(runs):
    rows = []
    for scenario in sorted({run["scenario"] for run in runs}):
        sample = [run for run in runs if run["scenario"] == scenario]
        for policy in POLICIES:
            observations = [
                run["metrics"][actor]
                for run in sample
                for actor in run["policies"]
                if run["policies"][actor] == policy
            ]
            keys = set().union(*(row.keys() for row in observations))
            first_captures = [
                run["first_capture"]["moon"]
                for run in sample
                if run["first_capture"] is not None
                and run["policies"][run["first_capture"]["actor"]] == policy
            ]
            rows.append(
                {
                    "scenario": scenario,
                    "policy": policy,
                    "games": len(observations),
                    "first_capture_games": len(first_captures),
                    "mean_first_capture_moon": mean(first_captures) if first_captures else None,
                    "means": {
                        key: mean(row.get(key, 0) for row in observations) for key in sorted(keys)
                    },
                }
            )
    return rows


def compare(seeds=100, scenarios=tuple(SCENARIOS), reign_months=120, decision_every=1):
    root = Path(__file__).resolve().parent.parent
    provenance = {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in (
            "scripts/evaluate_consolidation.py",
            "simulation/engine.py",
            "simulation/rules.py",
            "simulation/tactics.py",
        )
    }
    runs = [
        evaluate(
            f"consolidation-observation-{seed}", rotation, scenario, reign_months, decision_every
        )
        for seed in range(seeds)
        for rotation in range(3)
        for scenario in scenarios
    ]
    return {
        "format": "yaara-consolidation-evaluation",
        "version": 1,
        "source_sha256": provenance,
        "seeds": seeds,
        "reign_months": reign_months,
        "decision_every": decision_every,
        "policies": {
            "early": "Capture from Moon 1; 150k local reserve; then works.",
            "patient": "Capture from Moon 25; 500k frontier reserve; recipient-report supply; then works.",
            "raider": "Seasonal raids after Moons 4/7/10; capture from 49; 250k reserve; then works.",
        },
        "limitations": [
            "Fixed heuristics are not optimal players or evidence of human balance.",
            "Cyclic rotations cover every policy-position pair; they are not independent human games.",
            "Absence is accrued levy forgone, not necessarily treasury loss when harvest overflows.",
            "Unsettled raid loot is excluded from settled net; deaths are reported separately.",
            "No historical coefficient or human playtest is established by this experiment.",
        ],
        "metric_definitions": {
            "recoveries": "Each lost territory count regained on a later closed Moon; repeated losses count separately.",
            "recovered_after_loss": "A house recovered at least one previous territory count after a loss.",
            "occupation_men_moons": "Men physically assigned at Moon opening, before automatic release; includes their release Moon.",
            "frozen_city_moons": "Cities whose treasury is unavailable at the decision window before closure.",
            "settled_raid_absence": "Levy foregone during actual absence from still-owned origins; excludes detached or arrived cohorts.",
            "capture_target_exclusivity_rejections": "All target-reservation rejections, separately classified by pending raid/capture and own/enemy order.",
        },
        "summary": summarize(runs),
        "runs": runs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--decision-every", type=int, default=1)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/consolidation-comparison.json")
    )
    args = parser.parse_args()
    if args.seeds < 1 or args.decision_every < 1:
        parser.error("seeds and decision-every must be positive")
    result = compare(args.seeds, decision_every=args.decision_every)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"runs": len(result["runs"]), "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
