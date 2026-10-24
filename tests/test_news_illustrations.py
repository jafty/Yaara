"""Recipient-specific combat artwork follows the actual resolved encounter."""

from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.messages import describe, message, render
from simulation.models import Report
from simulation.narration import STARTED_ACTION_PHRASES
from tests.builders import rich_state
from tests.cases import case
from tests.stubs import FixedRandom


@case(
    "news-completed-work-artwork",
    "Owner: completed works show their recorded building in Council and full letters without rewriting archives",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("tab", ["domain", "letters"])
@pytest.mark.parametrize(
    "phrase,scene",
    [
        (message("ont achevé {work}", work=message("Rigoles et petites digues")), "irrigation"),
        (message("ont achevé {work}", work=message("Premiers canaux")), "irrigation"),
        (message("ont achevé {work}", work=message("Grand réseau hydraulique")), "irrigation"),
        (message("ont achevé {work}", work=message("Greniers supplémentaires")), "storage"),
        (message("ont achevé {work}", work=message("Ensemble de silos")), "storage"),
        (message("ont achevé {work}", work=message("Grands magasins")), "storage"),
        (message("ont achevé {work}", work=message("Petit arsenal")), "forge"),
        (message("ont achevé {work}", work=message("Ateliers d’armement")), "forge"),
        (message("ont achevé {work}", work=message("Grand arsenal")), "forge"),
        (message("ont achevé {work}", work=message("Palissades de bois")), "walls"),
        (message("ont achevé {work}", work=message("Palais renforcé")), "walls"),
        (message("ont achevé {work}", work=message("Murailles")), "walls"),
        (message("ont achevé {work}", work=message("Postes de veille")), "watch"),
        (message("ont achevé {work}", work=message("Tours de guet")), "watch"),
        (message("ont achevé {work}", work=message("Réserves souterraines")), "shelter"),
        (message("ont achevé {work}", work=message("Dépôts renforcés")), "shelter"),
        (message("ont achevé {work}", work=message("Ateliers de bât")), "transport"),
        (message("ont achevé {work}", work=message("Train de transport")), "transport"),
        (message("ont achevé {work}", work=message("Échelles d’assaut")), "siege"),
        (message("ont achevé {work}", work=message("Béliers")), "siege"),
        (message("ont restauré {work}", work=message("Défenses de la cité")), "walls"),
        (message("ont restauré {work}", work=message("Murailles")), "walls"),
        (message("ont restauré {work}", work=message("Tours de guet")), "watch"),
        (message("ont restauré {work}", work=message("Dépôts renforcés")), "shelter"),
        (message("ont aménagé la forge"), "forge"),
        (message("ont renforcé la forge"), "forge"),
        (message("ont aménagé les premiers canaux"), "irrigation"),
        (message("ont étendu le réseau de canaux"), "irrigation"),
        (message("ont agrandi le grenier"), "storage"),
        (message("ont érigé des silos"), "storage"),
        (message("ont érigé une enceinte de terre crue"), "walls"),
        (message("ont élevé une grande enceinte"), "walls"),
        (message("ont réparé l’enceinte de terre crue"), "walls"),
        (message("ont réparé la grande enceinte"), "walls"),
        (None, "forge"),
    ],
    ids=[
        "irrigation-1",
        "irrigation-2",
        "irrigation-3",
        "storage-1",
        "storage-2",
        "storage-3",
        "forge-1",
        "forge-2",
        "forge-3",
        "walls-1",
        "walls-2",
        "walls-3",
        "watch-1",
        "watch-2",
        "shelter-1",
        "shelter-2",
        "transport-1",
        "transport-2",
        "siege-1",
        "siege-2",
        "repair-initial-defenses",
        "repair-walls",
        "repair-watch",
        "repair-shelter",
        "legacy-forge-1",
        "legacy-forge-2",
        "legacy-irrigation-1",
        "legacy-irrigation-2",
        "legacy-storage-1",
        "legacy-storage-2",
        "legacy-walls-1",
        "legacy-walls-2",
        "legacy-repair-1",
        "legacy-repair-2",
        "legacy-equipment",
    ],
)
def test_completed_work_artwork(user, language, tab, phrase, scene):
    game = services.create_game(user, "Completed artwork", opponents="passive")
    title = (
        message("Travaux achevés à {p0}", p0="Qasr")
        if phrase is not None
        else message("La forge a achevé son œuvre")
    )
    body = message(
        "Les équipes de {p0} {p1}. L’ouvrage est désormais en service ; j’en tiendrai compte dans les registres à venir.",
        p0="Qasr",
        p1=phrase or message("Original equipment body"),
    )
    report = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="work",
        title=title,
        body=body,
        content={"title": describe(title), "body": describe(body)},
    )
    saved = deepcopy(report.content)
    # Today's buildings must not replace the historical completed building.
    game.state["cities"]["c1"].update(irrigation=3, storage=3, forge=3, walls=3)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id]), {"tab": tab}).content.decode()
    assert f'class="illustration illustration-{scene}"' in html
    report.refresh_from_db()
    assert report.content == saved


@case(
    "news-completion-neutral-fallback",
    "Owner: unidentified completion archives retain neutral artwork",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize(
    "variation", ["original", "unknown", "unknown-building", "plain-body", "other-kind"]
)
def test_completion_neutral_fallback(user, variation):
    game = services.create_game(user, "Completion archives", opponents="passive")
    body = (
        message("Original body")
        if variation != "other-kind"
        else message(
            "Les équipes de {p0} {p1}. L’ouvrage est désormais en service ; j’en tiendrai compte dans les registres à venir.",
            p0="Qasr",
            p1=message("ont aménagé la forge"),
        )
    )
    content = {"title": describe(message("Original title")), "body": describe(body)}
    if variation == "original":
        content = {}
    elif variation == "unknown-building":
        content["body"] = describe(
            message(
                "Les équipes de {p0} {p1}. L’ouvrage est désormais en service ; j’en tiendrai compte dans les registres à venir.",
                p0="Qasr",
                p1=message("ont achevé {work}", work=message("Unknown building")),
            )
        )
    elif variation == "plain-body":
        content["body"] = "Original body"
    Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="letter" if variation == "other-kind" else "work",
        title="Original title",
        body=body,
        content=content,
    )
    client = Client()
    client.force_login(user)
    html = client.get(reverse("game", args=[game.id]), {"tab": "letters"}).content.decode()
    scene = "letter" if variation == "other-kind" else "work"
    assert f'class="illustration illustration-{scene}"' in html


@case(
    "news-action-start-artwork",
    "Owner: launched actions use contextual beginning scenes in Council and full letters, including older headings",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("tab", ["domain", "letters"])
@pytest.mark.parametrize("heading", ["action", "historical"])
@pytest.mark.parametrize(
    "kind,scene",
    [
        ("raid", "start-army"),
        ("capture", "start-army"),
        ("storage", "start-storage"),
        ("forge", "start-forge"),
        ("equipment", "start-forge"),
        ("walls", "start-walls"),
        ("repair", "start-walls"),
        ("irrigation", "start-irrigation"),
        ("watch", "start-watch"),
        ("shelter", "start-shelter"),
        ("transport", "start-transport"),
        ("siege", "start-siege"),
    ],
)
def test_action_start_artwork_http(user, language, tab, heading, kind, scene):
    game = services.create_game(user, "Action artwork", opponents="passive", economy_version=3)
    phrase = STARTED_ACTION_PHRASES[kind]
    title = phrase if heading == "action" else message("Votre décret entre en vigueur")
    body = message(
        "{p0} J’ai fait prélever {p1} Mesures dans les greniers qui les avaient promises. Les nouvelles vous seront rapportées à leur échéance.",
        p0=phrase,
        p1="200 000",
    )
    report = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="order",
        title=title,
        body=body,
        content={"title": describe(title), "body": describe(body)},
    )
    original = deepcopy(report.content)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": tab})
    assert page.status_code == 200
    assert f'class="illustration illustration-{scene}"' in page.content.decode()
    assert render(original["title"], language) in page.content.decode()
    report.refresh_from_db()
    assert report.content == original


@case(
    "news-action-start-artwork-fallback",
    "Owner: unstarted or unrecognized decrees keep neutral artwork without guessing an action",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize(
    "variation",
    ["sealed", "cancelled", "invalidated", "original", "unknown", "plain-body", "other-kind"],
)
def test_action_start_artwork_fallback(user, variation):
    game = services.create_game(user, "Neutral artwork", opponents="passive", economy_version=3)
    title = message(
        {
            "sealed": "Décret scellé",
            "cancelled": "Décret retiré",
            "invalidated": "Ordre invalidé",
        }.get(variation, "Original title")
    )
    body = message("Original body")
    if variation == "other-kind":
        title = STARTED_ACTION_PHRASES["raid"]
    content = {} if variation == "original" else {"title": describe(title), "body": describe(body)}
    if variation == "plain-body":
        content["body"] = "Original body"
    Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="letter" if variation == "other-kind" else "order",
        title=title,
        body=body,
        content=content,
    )
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]), {"tab": "letters"})
    assert page.status_code == 200
    assert 'class="illustration illustration-letter"' in page.content.decode()


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
    game = services.create_game(user, "News artwork", opponents="passive", economy_version=3)
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
    assert (
        page.content.decode().count(f'class="illustration illustration-{scene}" aria-hidden="true"')
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
    game = services.create_game(user, "Archive", opponents="passive", economy_version=3)
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
            "Our people have departed to plunder the villages.",
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
    state = (
        engine.new_state(opponents="passive", economy_version=3)
        if kind != "equipment"
        else rich_state()
    )
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
