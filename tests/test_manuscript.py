import json
import re
import uuid
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import engine, services
from simulation.models import Report
from simulation.narration import work_effect
from simulation.projections import player_view
from tests.cases import case


@pytest.mark.logic
@case(
    "narration-repair-effect",
    "Decree preview: repairs restore the wall's current protection without implying an upgrade",
)
def test_repair_effect_preserves_wall_level():
    """Given a repair to an existing wall.
    When its effect is described for a decree.
    Then the scribe promises restoration of the current level rather than an upgrade.
    """
    assert (
        work_effect("repair", 2)
        == "L’enceinte retrouvera toute la protection de son niveau actuel."
    )


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "bulk-decree-from-realm",
    "City action directive: select several cities on a family page, then seal one atomic order",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_bulk_decree_from_realm(user, language):
    game = services.create_game(
        user, "Bulk works", opponents="passive", map_version=1, economy_version=1
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(
        reverse("game", args=[game.id]), {"tab": "constructions", "action": "storage"}
    )
    forms = re.findall(r"<form\b.*?</form>", page.content.decode(), re.S)
    storage = next((form for form in forms if 'value="storage"' in form), "")
    assert "data-work-form" in storage
    assert len(re.findall(r'name="cities"', storage)) == 3
    preview = client.post(
        reverse("preview", args=[game.id]), {"kind": "storage", "cities": ["c1", "c3"]}
    )
    assert preview.status_code == 200
    assert preview.context["order"]["cost"] == 1_000_000
    assert {task["name"] for task in preview.context["tasks"]} == {"Qasr", "Namar"}
    game.refresh_from_db()
    assert not game.state["orders"]
    result = client.post(
        reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]}
    )
    assert result.status_code == 302
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert {task["city"] for task in game.state["orders"][0]["tasks"]} == {"c1", "c3"}
    assert sum(engine.reservations(game.state)[0].values()) == 1_000_000


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "bulk-decree-busy-city",
    "City action directive: a family batch excludes teams already reserved by another decree",
)
def test_bulk_decree_busy_city(user):
    game = services.create_game(
        user, "Busy team", opponents="passive", map_version=1, economy_version=1
    )
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c1"]}, uuid.uuid4(), 1)
    client = Client()
    client.force_login(user)
    page = client.get(
        reverse("game", args=[game.id]), {"tab": "constructions", "action": "storage"}
    )
    forms = re.findall(r"<form\b.*?</form>", page.content.decode(), re.S)
    storage = next((form for form in forms if 'value="storage"' in form), "")
    assert re.search(r'<input\b[^>]*name="cities"[^>]*value="c1"[^>]*disabled', storage)


@pytest.mark.logic
@case("moon-first", "UI revision: new reigns open at Moon 1 with twelve closures to harvest")
def test_first_moon():
    """Given a new passive reign.
    When its initial calendar is projected.
    Then Moon 1 is open and twelve closures remain before the first harvest."""
    state = engine.new_state(opponents="passive", map_version=1, economy_version=1)
    assert state["month"] == 1
    view = player_view(state, "p1")
    assert (view["open_moon"], view["closed_moon"], view["harvest_in"]) == (1, 0, 12)
    assert view["harvest_moon"] == 12


@pytest.mark.logic
@case(
    "moon-departure",
    "UI revision: sealing in Moon 1 departs on its closure, combats in 2, returns in 3",
)
def test_moon_departure():
    """Given a raid sealed during Moon 1.
    When that Moon closes.
    Then it departs in Moon 1, fights in Moon 2 and returns in Moon 3."""
    state = engine.new_state(opponents="passive", map_version=1, economy_version=1)
    order = engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    assert order["execute_month"] == 1
    engine.advance_month(state, "seed")
    assert state["month"] == 2
    mission = state["expeditions"][0]
    assert (mission["departure_month"], mission["combat_month"], mission["return_month"]) == (
        1,
        2,
        3,
    )


@pytest.mark.logic
@case("moon-harvest", "UI revision: Moon 12 pays twelve intervals and Moon 13 starts year two")
def test_moon_harvest():
    """Given a new passive V0 reign.
    When twelve Moons close.
    Then exactly twelve tax intervals are paid and Moon 13 opens year two."""
    state = engine.new_state("V0", opponents="passive", map_version=1, economy_version=1)
    for _ in range(11):
        engine.advance_month(state, "seed")
    assert state["cities"]["c1"]["stock"] == 600_000
    assert player_view(state, "p1")["harvest_in"] == 1
    engine.advance_month(state, "seed")
    assert state["cities"]["c1"]["stock"] == 1_800_000
    view = player_view(state, "p1")
    assert (view["open_moon"], view["year"], view["year_month"]) == (13, 2, 1)


@pytest.mark.logic
@case(
    "moon-finish", "UI revision: a 24-Moon reign closes exactly 24 times and retains its final date"
)
def test_moon_finish():
    """Given a passive reign lasting twenty-four Moons.
    When twenty-four closures are processed.
    Then the result is fixed at Moon 24 with no remaining intervals."""
    state = engine.new_state(
        "V0", reign_months=24, opponents="passive", map_version=1, economy_version=1
    )
    for _ in range(24):
        engine.advance_month(state, "seed")
    view = player_view(state, "p1")
    assert state["result"]["month"] == 24
    assert view["finished"] and view["closed_moon"] == 24 and view["remaining"] == 0


@pytest.mark.logic
@case("moon-legacy", "UI revision: schema-one saves retain their zero-based simulation schedule")
def test_legacy_calendar():
    """Given a save without a calendar-version marker.
    When an order is prepared and a month advances.
    Then the original zero-based admission and one-based departure timing remain intact."""
    state = engine.new_state(
        calendar_version=1, opponents="passive", map_version=1, economy_version=1
    )
    state.pop("calendar_version", None)
    assert state["month"] == 0
    order = engine.prepare_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "work")
    assert order["execute_month"] == 1
    engine.advance_month(state, "seed")
    assert state["month"] == 1 and state["cities"]["c1"]["tax"] == 100_000


@pytest.mark.journey
@case(
    "moon-calendar-equivalence",
    "UI revision: open-Moon dates preserve the established bot, economic and combat sequence",
)
def test_calendar_equivalence():
    legacy = engine.new_state(reign_months=24, calendar_version=1, map_version=1, economy_version=1)
    current = engine.new_state(reign_months=24, map_version=1, economy_version=1)
    for _ in range(24):
        engine.bot_orders(legacy, "calendar-equivalence")
        engine.bot_orders(current, "calendar-equivalence")
        old_events, old_audit = engine.advance_month(legacy, "calendar-equivalence")
        new_events, new_audit = engine.advance_month(current, "calendar-equivalence")
        assert new_audit == old_audit
        assert new_events == old_events
        for field in ("cities", "orders", "works", "expeditions", "result"):
            assert current[field] == legacy[field], field


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "moon-tick-retry",
    "UI revision: Moon 1 closure retries stay idempotent under the open-Moon calendar",
)
def test_moon_tick_retry(user):
    game = services.create_game(
        user, "Moons", opponents="passive", map_version=1, economy_version=1
    )
    first, executed = services.tick(game.id, 1, user)
    assert executed
    repeated, executed = services.tick(game.id, 1, user)
    game.refresh_from_db()
    assert repeated.pk == first.pk and not executed
    assert game.state["month"] == 2 and game.state["cities"]["c1"]["tax"] == 100_000
    assert Report.objects.get(game=game, kind="welcome").month == 1


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "city-folio-privacy",
    "UI revision: city pages show only owned accounts and reject unknown city IDs",
)
@pytest.mark.parametrize(
    "city,status,private", [("c1", 200, True), ("c4", 200, False), ("missing", 404, False)]
)
def test_city_folio_privacy(user, game, city, status, private):
    client = Client()
    client.force_login(user)
    response = client.get(reverse("game", args=[game.id]), {"tab": "city", "city": city})
    assert response.status_code == status
    if status == 200:
        assert (b"data-local-accounts" in response.content) == private
        assert b"data-foreign-city" not in response.content or not private


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "bilingual-saved-report",
    "UI revision: persisted recipient reports render in the selected language without mutation",
)
@pytest.mark.parametrize(
    "language,title", [("fr", "Décret scellé"), ("en", "Decree sealed")], ids=["french", "english"]
)
def test_bilingual_saved_report(user, language, title):
    game = services.create_game(
        user, "Bilingual", opponents="passive", map_version=1, economy_version=1
    )
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c1"]}, uuid.uuid4(), 1)
    stored = list(Report.objects.filter(game=game).values())
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("game", args=[game.id]), {"tab": "letters"})
    assert response.status_code == 200
    assert title in response.content.decode()
    assert f'lang="{language}"' in response.content.decode()
    assert list(Report.objects.filter(game=game).values()) == stored
    projection = client.get(reverse("state", args=[game.id])).json()
    assert "combativity" not in json.dumps(projection)


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "draft-language-switch",
    "UI revision: switching languages preserves an unsealed draft without reserving resources",
)
def test_draft_language_switch(user):
    game = services.create_game(
        user, "Draft", opponents="passive", map_version=1, economy_version=1
    )
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]), {"kind": "storage", "cities": ["c2"]}
    )
    payload = response.context["payload"]
    client.cookies["django_language"] = "en"
    response = client.get(reverse("preview", args=[game.id]), {"payload": payload})
    assert response.status_code == 200
    assert "Unsealed draft" in response.content.decode()
    assert response.context["payload"] == payload
    game.refresh_from_db()
    assert game.state["orders"] == [] and game.revision == 0


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("test_static_storage")
@case(
    "draft-reopen-rejected",
    "UI revision: foreign, tampered and stale draft links do not reveal or confirm orders",
)
@pytest.mark.parametrize("scenario", ["foreign", "tampered", "stale"])
def test_draft_reopen_rejected(user, scenario):
    game = services.create_game(
        user, "Draft", opponents="passive", map_version=1, economy_version=1
    )
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]), {"kind": "storage", "cities": ["c2"]}
    )
    payload = response.context["payload"]
    target = game
    if scenario == "foreign":
        target = services.create_game(
            user, "Other", opponents="passive", map_version=1, economy_version=1
        )
    elif scenario == "tampered":
        payload += "tampered"
    else:
        services.tick(game.id, 1, user)
    response = client.get(reverse("preview", args=[target.id]), {"payload": payload})
    assert response.status_code == 302
    game.refresh_from_db()
    assert not game.state["orders"]


@pytest.mark.integration
@pytest.mark.django_db
@case(
    "moon-scheduler",
    "UI revision: scheduled closures use the open Moon and retain pause and deadline guarantees",
)
@pytest.mark.parametrize("scenario", ["early", "due", "late", "paused"])
def test_open_moon_scheduler(user, scenario):
    game = services.create_game(
        user, "Scheduled", mode="scheduled", opponents="passive", map_version=1, economy_version=1
    )
    if scenario in ("due", "late"):
        game.deadline = timezone.now() - timedelta(seconds=2 if scenario == "due" else 1200)
        game.save(update_fields=["deadline"])
    elif scenario == "paused":
        services.toggle_pause(user, game.id)
    call_command("tick_due")
    game.refresh_from_db()
    assert game.state["month"] == (2 if scenario == "due" else 1)
    assert game.ticks.count() == int(scenario == "due")
    assert game.paused == (scenario in ("late", "paused"))
