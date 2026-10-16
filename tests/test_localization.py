"""Language and completed-event variations, independent of storage and HTTP."""

import json

import pytest

from simulation import engine
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "locale-core-french",
    "Language decision: core observations remain French regardless of UI language",
)
def test_core_observation_remains_french():
    """Given no defenders.
    When the core reports an encounter.
    Then its default remains French."""
    assert engine.observation(0, 20, 2) == "Nos survivants n’ont rencontré aucun défenseur."


@case(
    "locale-report-replay",
    "Language decision: stored recipient reports render in either language without replaying rules",
)
def test_report_can_be_rendered_after_json_roundtrip():
    """Given a completed work.
    When its report is stored.
    Then either language can render the same facts."""
    from simulation.messages import render

    state = rich_state()
    engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "store")
    events = []
    for _ in range(5):
        current, _ = engine.advance_month(state, "language")
        events.extend(current)
    report = next(event for event in events if event["kind"] == "work")
    content = json.loads(json.dumps(report["content"]))
    assert "ont agrandi le grenier" in render(content["body"], "fr")
    assert "have enlarged the granary" in render(content["body"], "en")
    assert state["cities"]["c1"]["storage"] == 1


@case(
    "narration-completed-work",
    "RP decision: completed works use passé composé; proposed works retain the infinitive",
)
@pytest.mark.parametrize(
    "kind,level,expected",
    [
        pytest.param("irrigation", 1, "ont aménagé les premiers canaux", id="first-canals"),
        pytest.param("irrigation", 2, "ont étendu le réseau de canaux", id="extended-canals"),
        pytest.param("storage", 1, "ont agrandi le grenier", id="granary"),
        pytest.param("storage", 2, "ont érigé des silos", id="silos"),
        pytest.param("walls", 1, "ont érigé une enceinte de terre crue", id="earth-wall"),
        pytest.param("walls", 2, "ont élevé une grande enceinte", id="great-wall"),
        pytest.param("repair", 1, "ont réparé l’enceinte de terre crue", id="earth-repair"),
        pytest.param("repair", 2, "ont réparé la grande enceinte", id="great-repair"),
    ],
)
def test_completed_work_uses_past_tense(kind, level, expected):
    """Given a work kind and level.
    When it finishes.
    Then the scribe describes a completed act."""
    from simulation.narration import completed_work_phrase, work_phrase

    assert completed_work_phrase(kind, level) == expected
    assert not work_phrase(kind, level).startswith("ont ")


@case(
    "narration-started-work",
    "RP decision: departure describes work as begun, without claiming it is complete",
)
def test_started_work_describes_a_beginning():
    """Given a confirmed granary project.
    When its departure month is closed.
    Then its report describes work begun and the granary is not yet enlarged.
    """
    state = rich_state()
    engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "store")
    events, _ = engine.advance_month(state, "language")
    report = next(
        event for event in events if event["kind"] == "order" and event["recipient"] == "p1"
    )
    assert "Les travaux des greniers ont commencé." in report["body"]
    assert state["cities"]["c1"]["storage"] == 0
