"""Specified combat outcomes, observations and noncombat damage."""

from copy import deepcopy
from dataclasses import dataclass

import pytest

from simulation import engine
from simulation.narration import observed_losses
from tests.cases import case

pytestmark = pytest.mark.logic


@dataclass
class RaidDraw:
    chance: int = 99
    discovery: int = 0
    victims: int = 0
    family: str = "watch"

    def shuffle(self, items):
        pass

    def choice(self, values):
        return (
            40
            if isinstance(values[0], int)
            else self.family
            if self.family in values
            else values[0]
        )

    def randrange(self, stop):
        return self.discovery if stop == 4 else self.chance

    def randint(self, first, last):
        assert first <= self.victims <= last
        return self.victims

    def sample(self, population, count):
        return list(population)[:count]


def raid_state(monkeypatch, draw, men=100):
    monkeypatch.setattr(engine, "random_stream", lambda *args: draw)
    state = engine.new_state(opponents="passive", economy_version=4)
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": men}}, "raid"
    )
    return state


@case(
    "strategy-building-damage",
    "Prompt F: one eligible exterior asset, discovery chance, no retroactive effects",
)
@pytest.mark.parametrize(
    "watch,shelter,chance,discovery,family,damaged",
    [
        (1, 0, 0, 0, "watch", ["watch"]),
        (0, 1, 0, 0, "shelter", ["shelter"]),
        (1, 1, 0, 1, "shelter", []),
        (1, 1, 20, 0, "watch", []),
        (0, 0, 0, 0, "watch", []),
    ],
)
def test_building_damage(monkeypatch, watch, shelter, chance, discovery, family, damaged):
    """Given finished watch {watch} and shelter {shelter} with draws {chance}/{discovery}.
    When a victorious raid selects {family} after calculating its combat and crop loss.
    Then only {damaged} is damaged and the original protection applies to that raid.
    """
    state = raid_state(monkeypatch, RaidDraw(chance, discovery, 0, family))
    target = state["cities"]["c4"]
    target.update(watch=watch, shelter=shelter, tax=1000000)
    engine.advance_month(state, "damage")
    engine.advance_month(state, "damage")
    assert target["damaged_works"] == damaged
    assert (target["watch"], target["shelter"]) == (watch, shelter)
    assert state["expeditions"][0]["loot"] == (120000 if shelter else 150000)
    assert target["raid_protected_until"] == 5


@case(
    "strategy-noncombat-victims",
    "Prompt E: sampling excludes engaged and absent residents and removes each person once",
)
def test_noncombat_victims(monkeypatch):
    """Given forty engaged defenders, fifty absent Faithful and ten unengaged Faithful.
    When agricultural damage also kills one sampled unengaged resident.
    Then population falls once for each of two combat deaths and one noncombat death.
    """
    state = raid_state(monkeypatch, RaidDraw(victims=1))
    target = state["cities"]["c4"]
    engine.confirm_order(
        state, "p2", {"kind": "raid", "target": "c7", "contributions": {"c4": 50}}, "absent"
    )
    engine.advance_month(state, "victims")
    # The fixed watch mobilizes all but ten of the fifty present Faithful.
    target["watch"] = 2
    # Sixty percent of fifty engages thirty, with two half-up military casualties.
    state["expeditions"][1]["status"] = "returning"
    before = target["population"]
    engine.advance_month(state, "victims")
    assert before - target["population"] == 2
    assert target["military_deaths"] == 1
    assert target["civilian_deaths"] == 1
    assert target["fideles"] == 48
    assert engine.absent(state, "c4") == 50


@case(
    "strategy-loss-observation",
    "Prompt K: stable qualitative bands, no observations without reliable witnesses",
)
@pytest.mark.parametrize(
    "dead,witnesses,word",
    [
        (0, 10, "aucune"),
        (1, 10, "Quelques"),
        (4, 10, "Quelques"),
        (5, 10, "sensibles"),
        (14, 10, "sensibles"),
        (15, 10, "durement"),
        (29, 10, "durement"),
        (30, 10, "très lourdes"),
        (80, 0, "ne peuvent"),
        (10, 9, "ne peuvent"),
    ],
)
def test_observed_losses(dead, witnesses, word):
    """Given {dead} enemy casualties and {witnesses} returning witnesses.
    When a recipient observation is narrated.
    Then it uses the qualitative band containing {word} without a numeric casualty count.
    """
    text = observed_losses(dead, witnesses)
    assert word in text
    assert not any(character.isdigit() for character in text)


@case(
    "strategy-opening-capture",
    "Owner October 22: reserve management matters even behind initial defenses",
)
@pytest.mark.parametrize(
    "men,stock,siege,owner,integrity",
    [
        (150, 300000, 0, "p1", 100),
        (150, 500000, 0, "p2", 100),
        (300, 600000, 0, "p2", 100),
        (300, 600000, 1, "p1", 50),
    ],
)
def test_opening_capture(men, stock, siege, owner, integrity):
    """Given 100 locals, forty relief, initial walls and {stock} Measures.
    When {men} attackers with siege level {siege} arrive after an affordable departure.
    Then the city belongs to {owner} with integrity {integrity} and no famine-only civilian deaths.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    state["cities"]["c4"]["stock"] = stock
    for origin in ("c1", "c2", "c3"):
        state["cities"][origin]["siege"] = siege
    contributions = (
        {"c1": 100, "c2": men - 100} if men == 150 else {"c1": 100, "c2": 100, "c3": 100}
    )
    engine.confirm_order(
        state, "p1", {"kind": "capture", "target": "c4", "contributions": contributions}, "capture"
    )
    engine.advance_month(state, "opening")
    engine.advance_month(state, "opening")
    target = state["cities"]["c4"]
    assert (target["owner"], target["integrity"], target["civilian_deaths"]) == (
        owner,
        integrity,
        0,
    )
    assert target["stock"] == (100000 if men == 300 and not siege else 600000 if siege else 0)
    engine.advance_month(state, "opening")
    assert state["expeditions"][0]["status"] == "completed"


@case(
    "strategy-relief-under-attack",
    "Follow-up: a city facing capture in this resolution exports no relief",
)
def test_relief_under_attack():
    """Given two friendly cities facing simultaneous capture attempts.
    When automatic relief is allocated from the frozen precombat state.
    Then neither threatened city exports defenders and the third contributes only twenty percent.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    missions = [
        {
            "id": "one",
            "kind": "capture",
            "target": "c4",
            "actor": "p1",
            "cohorts": {"c1": 100},
            "combativity": 100,
        },
        {
            "id": "two",
            "kind": "capture",
            "target": "c5",
            "actor": "p3",
            "cohorts": {"c7": 100},
            "combativity": 100,
        },
    ]
    before = deepcopy(state)
    relief = engine.relief_allocations(state, missions, sorted(state["cities"]))
    assert {item["origin"] for item in relief} == {"c6"}
    assert sum(item["count"] for item in relief) == 20
    assert state == before


@case(
    "strategy-interception-boundary",
    "Prompt D: retreat interception follows effective surveillance at strict probability thresholds",
)
@pytest.mark.parametrize(
    "watch,draw,dead", [(0, 9, 4), (0, 10, 0), (1, 19, 4), (1, 20, 0), (2, 29, 4), (2, 30, 0)]
)
def test_interception(monkeypatch, watch, draw, dead):
    """Given twenty raiders facing a stronger defense and watch level {watch}.
    When the prescribed interception draw is {draw}.
    Then {dead} raiders die and target losses alone determine whether respite begins.
    """
    state = raid_state(monkeypatch, RaidDraw(chance=draw), men=20)
    state["cities"]["c4"]["watch"] = watch
    engine.advance_month(state, "retreat")
    engine.advance_month(state, "retreat")
    assert state["expeditions"][0]["cohorts"]["c1"] == 20 - dead
    assert state["cities"]["c4"]["tax"] == 200000
    assert state["cities"]["c4"]["raid_protected_until"] == 0


@case(
    "strategy-relief-outside-raid",
    "Prompt E: relief abroad cannot be counted among local noncombat residents",
)
def test_relief_outside_raid():
    """Given 101 relief fighters abroad among a city's 600 registered inhabitants.
    When a raid with crop damage calculates losses among the 499 residents still at home.
    Then the two-per-thousand bound rounds down to zero and no absent person can die here.
    """
    from simulation.rules import RaidResult

    state = engine.new_state()
    target = state["cities"]["c1"]
    target.update(population=600, fideles=0)

    class ZeroBound(RaidDraw):
        def randint(self, first, last):
            assert (first, last) == (0, 0)
            return 0

    result = engine.raid_aftermath(
        state, target, 100, 0, RaidResult("success", 0, 0, 1, 0), ZeroBound(), relief_away=101
    )
    assert result == (0, None)
    assert target["population"] == 600
