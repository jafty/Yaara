"""Construction effects remain readable at every completed stage."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.messages import localize
from simulation.narration import work_effect
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "works-forge-readable-effect",
    "Owner: forge descriptions explain attack, defence and departing equipment",
)
@pytest.mark.parametrize("level", [1, 2, 3])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_forge_effect(level, language):
    """Given a current-rule forge at level {level} viewed in {language}.
    When its effect is described.
    Then the prose explains local attack and defence without revealing combativity numbers.
    """
    effect = localize(work_effect("forge", level, 4), language)
    assert ("attaque et la défense" if language == "fr" else "attack and defence") in effect
    assert (
        "expéditions déjà parties" if language == "fr" else "Expeditions already underway"
    ) in effect
    assert not any(character.isdigit() for character in effect)


@case(
    "works-completed-effect",
    "Owner: maximum-level works retain an effect even without another upgrade",
)
@pytest.mark.parametrize(
    "kind,level,meaning",
    [
        ("irrigation", 3, "200"),
        ("storage", 3, "8\u202f100\u202f000"),
        ("forge", 3, "attaque et la défense"),
        ("walls", 3, "captures"),
        ("watch", 2, "60"),
        ("shelter", 2, "800"),
        ("transport", 2, "50"),
        ("siege", 2, "50"),
    ],
)
def test_completed_effect(kind, level, meaning):
    """Given a fully upgraded {kind} building at level {level}.
    When its construction-list entry is projected.
    Then its effect still explains {meaning} while further construction stays unavailable.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    state["cities"]["c1"][kind] = level
    before = deepcopy(state)
    work = next(row for row in player_view(state, "p1")["work_actions"] if row["kind"] == kind)
    entry = next(row for row in work["cities"] if row["id"] == "c1")
    assert entry["status"] == "completed" and not entry["available"]
    assert not entry["work_name"] and entry["cost"] == 0
    assert meaning in entry["benefit"]
    assert state == before
