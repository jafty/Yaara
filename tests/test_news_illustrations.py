"""Recipient-specific combat artwork follows the actual resolved encounter."""

from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.messages import render
from simulation.models import Report
from tests.builders import rich_state
from tests.cases import case
from tests.stubs import FixedRandom


def combat_news(monkeypatch, kind, outcome):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())
    state = rich_state()
    state["links"] = [["c3", "c4"]]
    target = state["cities"]["c4"]
    target.update(fideles=100, walls=0)
    if kind == "raid":
        target["fideles"] = {"success": 100, "empty-success": 100, "defeat": 200, "rout": 300}[
            outcome
        ]
        if outcome == "empty-success":
            target["stock"] = 0
        count = 45
    else:
        count = 100
        if outcome in ("held", "shortage"):
            target.update(walls=2, stock=500000 if outcome == "held" else 499999)
            state["players"]["p1"]["equipment"] = 1
        elif outcome in ("defeat", "rout"):
            target["fideles"] = 200 if outcome == "defeat" else 300
        elif outcome == "assault":
            target["fideles"] = 80
        elif outcome == "surrender":
            target["fideles"] = 50
        else:
            target["fideles"] = 0
    engine.confirm_order(
        state, "p1", {"kind": kind, "target": "c4", "contributions": {"c3": count}}, "news"
    )
    engine.advance_month(state, "fixed")
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    return state, events


@case(
    "news-combat-artwork-outcome",
    "Owner artwork: raid and capture results select distinct offensive and received scenes",
)
@pytest.mark.logic
@pytest.mark.parametrize(
    "kind,outcome,expected",
    [
        ("raid", "success", "success"),
        ("raid", "empty-success", "success"),
        ("raid", "defeat", "failure"),
        ("raid", "rout", "failure"),
        ("capture", "unopposed", "success"),
        ("capture", "surrender", "success"),
        ("capture", "assault", "success"),
        ("capture", "shortage", "success"),
        ("capture", "held", "failure"),
        ("capture", "defeat", "failure"),
        ("capture", "rout", "failure"),
    ],
)
def test_combat_artwork(monkeypatch, kind, outcome, expected):
    """Given a {kind} encounter with the prescribed {outcome} outcome.
    When combat resolves and each recipient's letter is composed.
    Then both scenes identify their perspective and the attacker's {expected} without exposing combat strength.
    """
    state, events = combat_news(monkeypatch, kind, outcome)
    battles = {event["recipient"]: event for event in events if event["kind"] == "battle"}
    assert battles["p1"]["content"]["scene"] == f"offensive-{kind}-{expected}"
    assert battles["p2"]["content"]["scene"] == f"received-{kind}-{expected}"
    assert set(battles["p2"]["content"]) == {"title", "body", "scene"}
    assert all("scene" not in event["content"] for event in events if event["kind"] != "battle")
    if outcome == "empty-success":
        assert state["expeditions"][0]["loot"] == 0
    if kind == "capture":
        assert state["cities"]["c4"]["owner"] == ("p1" if expected == "success" else "p2")


@case(
    "news-combat-artwork-bilingual",
    "Owner: Council keeps thumbnails and full reports show complete large images in both languages",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("tab", ["domain", "letters"])
@pytest.mark.parametrize("recipient,direction", [("p1", "offensive"), ("p2", "received")])
@pytest.mark.parametrize(
    "kind,outcome,expected",
    [
        ("raid", "success", "success"),
        ("raid", "rout", "failure"),
        ("capture", "surrender", "success"),
        ("capture", "held", "failure"),
    ],
)
def test_combat_artwork_http(
    user, monkeypatch, language, tab, recipient, direction, kind, outcome, expected
):
    game = services.create_game(user, "News artwork", opponents="passive")
    game.state, events = combat_news(monkeypatch, kind, outcome)
    game.memberships.update(actor=recipient)
    services.persist(game, events)
    saved = list(game.reports.values("id", "content", "title", "body"))
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": tab})
    assert page.status_code == 200
    scene = f"{direction}-{kind}-{expected}"
    size = " illustration-small" if tab == "domain" else ""
    assert (
        page.content.decode().count(
            f'class="illustration illustration-{scene}{size}" aria-hidden="true"'
        )
        == 1
    )
    other = "received" if direction == "offensive" else "offensive"
    assert f"illustration-{other}-{kind}" not in page.content.decode()
    assert list(game.reports.values("id", "content", "title", "body")) == saved


@case(
    "news-combat-artwork-archive-fallback",
    "Owner artwork: older and unknown reports keep generic artwork without guessing results",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("variation", ["original", "structured", "unknown-scene", "other-kind"])
def test_archive_artwork(user, variation):
    game = services.create_game(user, "Archive", opponents="passive")
    content = {
        "title": {"template": "Old title", "values": {}},
        "body": {"template": "Old body", "values": {}},
    }
    if variation == "original":
        content = {}
    elif variation == "unknown-scene":
        content["scene"] = "unrecognized"
    elif variation == "other-kind":
        content["scene"] = "offensive-raid-success"
    report = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="work" if variation == "other-kind" else "battle",
        title="Original title",
        body="Original body",
        content=content,
    )
    original = deepcopy(content)
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]), {"tab": "letters"})
    scene = "work" if variation == "other-kind" else "raid"
    assert f'class="illustration illustration-{scene}"' in page.content.decode()
    report.refresh_from_db()
    assert report.content == original


@case("launched-action-heading", "Owner: departure headings identify the action in both languages")
@pytest.mark.logic
@pytest.mark.parametrize(
    "kind,french,english",
    [
        (
            "raid",
            "Nos hommes sont partis piller les villages.",
            "Our people have departed to raid the villages.",
        ),
        (
            "capture",
            "Nos hommes sont partis conquérir la cité.",
            "Our people have departed to capture the city.",
        ),
        ("irrigation", "Les travaux des canaux ont commencé.", "Work on the canals has begun."),
        ("storage", "Les travaux des greniers ont commencé.", "Work on the granaries has begun."),
        ("forge", "Les travaux des forges ont commencé.", "Work on the forges has begun."),
        (
            "walls",
            "Les travaux des fortifications ont commencé.",
            "Work on the fortifications has begun.",
        ),
        (
            "repair",
            "Les réparations de l’enceinte ont commencé.",
            "Repairs to the wall have begun.",
        ),
        (
            "equipment",
            "Les maîtres de la forge ont commencé leur ouvrage.",
            "The masters of the forge have begun their work.",
        ),
        ("watch", "Les travaux de surveillance ont commencé.", "Work on surveillance has begun."),
        (
            "shelter",
            "Les travaux des réserves protégées ont commencé.",
            "Work on protected reserves has begun.",
        ),
        (
            "transport",
            "Les ateliers de transport ont commencé leur ouvrage.",
            "The transport workshops have begun their work.",
        ),
        (
            "siege",
            "La préparation du matériel de siège a commencé.",
            "Preparation of siege equipment has begun.",
        ),
    ],
    ids=[
        "raid",
        "capture",
        "irrigation",
        "storage",
        "forge",
        "walls",
        "repair",
        "equipment",
        "watch",
        "shelter",
        "transport",
        "siege",
    ],
)
def test_launched_action_heading(kind, french, english):
    """Given a sealed {kind} order.
    When the order starts at Moon closure.
    Then its report heading names the launched action in French and English.
    """
    state = engine.new_state(opponents="passive") if kind != "equipment" else rich_state()
    for city in state["cities"].values():
        city["stock"] = 2_400_000
    if kind == "repair":
        state["cities"]["c1"].update(walls=1, damaged=True)
    if kind in ("raid", "capture"):
        spec = {"kind": kind, "target": "c4", "contributions": {"c3": 80}}
    else:
        spec = {"kind": kind, "cities": ["c1"]}
    engine.confirm_order(state, "p1", spec, "heading")
    events, _ = engine.advance_month(state, "heading")
    event = next(event for event in events if event["kind"] == "order")
    assert event["title"] == french
    assert render(event["content"]["title"], "en") == english
