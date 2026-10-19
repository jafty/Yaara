import json

import pytest

from simulation import engine
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "projection-private", "Design §26.2 Information: no opponent private fields in the projection"
)
@pytest.mark.parametrize(
    "field", ["population", "fideles", "stock", "tax", "irrigation", "storage", "works"]
)
def test_opponent_city_fields_are_private(field):
    """Given a player consulting an opponent city.
    When the public projection is built.
    Then the private field {field} is absent.
    """
    projection = player_view(engine.new_state(calendar_version=1, map_version=1), "p1")
    enemy = next(city for city in projection["cities"] if city["id"] == "c4")
    assert field not in enemy


@case("projection-ranking", "Design §26.2 Information: rankings hide opponent populations")
def test_ranking_hides_population():
    """Given the initial realm standings.
    When a player reads the ranking projection.
    Then no opponent population is disclosed.
    """
    projection = player_view(engine.new_state(calendar_version=1, map_version=1), "p1")
    assert all("population" not in rank for rank in projection["ranking"])


@case(
    "projection-secrets",
    "Design §26.2 Information: no internal orders or numerical combativity in JSON",
)
@pytest.mark.parametrize("secret", ["combativity", "secret-order", "cohorts", "seed"])
def test_serialized_projection_hides_internal_state(secret):
    """Given an opponent has a confirmed secret raid.
    When the player projection is serialized.
    Then the internal value {secret} is absent.
    """
    state = engine.new_state(calendar_version=1, map_version=1)
    engine.confirm_order(
        state, "p2", {"kind": "raid", "target": "c3", "contributions": {"c4": 45}}, "secret-order"
    )
    assert secret not in json.dumps(player_view(state, "p1"))


@case(
    "observation-undefended",
    "Information rule: equipment can only be observed on encountered defenders",
)
def test_no_defenders_does_not_reveal_equipment():
    """Given twenty survivors encountered no defenders.
    When their observation is reported.
    Then the report reveals no equipment.
    """
    assert engine.observation(0, 20, 2) == "Nos survivants n’ont rencontré aucun défenseur."


@case(
    "observation-survivors",
    "Information rule: no report without survivors; fewer than ten gives uncertain observations",
)
@pytest.mark.parametrize(
    "survivors,expected",
    [
        pytest.param(0, "Aucun survivant ne peut décrire les forces adverses.", id="none"),
        pytest.param(
            9, "Les rares survivants ne livrent que des observations incertaines.", id="below-ten"
        ),
    ],
)
def test_insufficient_survivors(survivors, expected):
    """Given {survivors} survivors from an encounter.
    When their observation is reported.
    Then the report is {expected}, with no precise enemy strength.
    """
    assert engine.observation(40, survivors, 2) == expected


@case(
    "observation-bands",
    "Information rule: ten survivors report a twenty-man band and qualitative equipment",
)
@pytest.mark.parametrize(
    "enemy,band",
    [
        pytest.param(19, "entre 0 et 19 hommes", id="below-band"),
        pytest.param(20, "entre 20 et 39 hommes", id="band-boundary"),
    ],
)
def test_observation_bands(enemy, band):
    """Given {enemy} encountered defenders and ten survivors.
    When their observation is reported.
    Then the report gives {band} and qualitative reinforced equipment.
    """
    report = engine.observation(enemy, 10, 1)
    assert band in report
    assert "équipement renforcé" in report


@case("projection-organic-atlas", "Owner UX: stable irregular city positions preserve public roads")
def test_organic_atlas():
    """Given the nine public oasis cities.
    When their atlas is projected for different rulers.
    Then positions are stable, safely spaced and include interior settlements.
    """
    state = engine.new_state(map_version=1)
    first = player_view(state, "p1")
    second = player_view(state, "p2")
    points = [(city["x"], city["y"]) for city in first["cities"]]
    assert points == [(city["x"], city["y"]) for city in second["cities"]]
    assert all(60 <= x <= 620 and 60 <= y <= 440 for x, y in points)
    assert all(
        (x - other_x) ** 2 + (y - other_y) ** 2 > 110**2
        for index, (x, y) in enumerate(points)
        for other_x, other_y in points[index + 1 :]
    )
    assert any(240 < x < 440 and 170 < y < 300 for x, y in points)
    assert len(first["links"]) == len(state["links"])
