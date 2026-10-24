"""Self-selected houses use transactional admission, never shared seat credentials."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse

from simulation import multiplayer, services
from simulation.models import Participant
from simulation.rules import RuleError
from tests.cases import case
from tests.stubs import FixedClock
from tests.test_application import concurrent_calls

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
    pytest.mark.usefixtures("test_static_storage"),
]


@pytest.fixture
def operator(user, django_user_model):
    user.user_permissions.add(Permission.objects.get(codename="manage_multiplayer_games"))
    return django_user_model.objects.get(pk=user.pk)


@pytest.fixture
def room(operator):
    return multiplayer.create_shared(operator, "Choose your house", play_window="Saturday UTC")


def claim(room, actor, name, **kwargs):
    return multiplayer.choose_seat(
        multiplayer.recruitment_token(room),
        actor,
        name,
        kwargs.pop("claim_key", uuid.uuid4()),
        **kwargs,
    )


@case("recruit-landing", "Recruitment: GET lists available territory without claiming")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_landing(room, language):
    client = Client()
    client.cookies["django_language"] = language
    response = client.get(reverse("shared_recruit", args=[multiplayer.recruitment_token(room)]))
    assert response.status_code == 200
    assert response.context["spots_left"] == 3
    assert b'"seed"' not in response.content
    assert b'name="house_name"' in response.content
    assert not room.memberships.exists()
    assert b"private, no-store" in response.headers["Cache-Control"].encode()


@case("recruit-choose-territory", "Recruitment: selected house owns its actual starting territory")
@pytest.mark.parametrize("actor", ["p1", "p2", "p3"])
def test_choose(room, actor):
    user = claim(room, actor, "House <Cedar>")
    room.refresh_from_db()
    assert services.membership(room, user) == actor
    assert room.state["players"][actor]["name"] == "House <Cedar>"
    assert not user.has_usable_password()
    assert room.lobby_status == "waiting" and room.deadline is None


@case("recruit-invalid-name", "Recruitment: invalid house names leave admission unchanged")
@pytest.mark.parametrize(
    "name", ["", "   ", "a" * 81, "House\nCedar"], ids=["empty", "spaces", "too-long", "multiline"]
)
def test_invalid_name(room, name):
    before = room.state
    with pytest.raises(RuleError):
        claim(room, "p1", name)
    room.refresh_from_db()
    assert not room.memberships.exists() and room.state == before


@case("recruit-duplicate-name", "Recruitment: house names are unique ignoring case and spaces")
def test_duplicate_name(room):
    claim(room, "p1", "Cedar")
    with pytest.raises(RuleError):
        claim(room, "p2", " cedar ")
    assert room.memberships.count() == 1


@case("recruit-occupied", "Recruitment: a common link cannot authenticate an occupied seat")
def test_occupied(room):
    original = claim(room, "p1", "Cedar")
    with pytest.raises(RuleError):
        claim(room, "p1", "Intruder")
    assert room.memberships.get(actor="p1").user_id == original.pk


@case("recruit-invalid-seat", "Recruitment: unknown territory cannot create an identity")
def test_invalid_seat(room):
    with pytest.raises(RuleError):
        claim(room, "p9", "Cedar")
    assert not room.memberships.exists()


@case("recruit-claim-replay", "Recruitment: repeated delivery returns the same house")
def test_replay(room):
    key = uuid.uuid4()
    first = claim(room, "p1", "Cedar", claim_key=key)
    assert claim(room, "p1", "Cedar", claim_key=key).pk == first.pk
    assert room.memberships.count() == 1


@case("recruit-one-known-player", "Recruitment: one authenticated player cannot take two houses")
def test_known_player(room):
    first = claim(room, "p1", "Cedar")
    with pytest.raises(RuleError):
        claim(room, "p2", "Oak", user=first)
    assert room.memberships.count() == 1


@case("recruit-start-at-capacity", "Recruitment: third admission starts once with a full interval")
def test_auto_start(room, monkeypatch):
    instant = datetime(2030, 1, 1, 12, 9, 59, tzinfo=timezone.utc)
    monkeypatch.setattr(services.timezone, "now", FixedClock(instant))
    claim(room, "p1", "Cedar")
    claim(room, "p2", "Oak")
    room.refresh_from_db()
    assert room.lobby_status == "waiting" and room.paused
    key = uuid.uuid4()
    claim(room, "p3", "Palm", claim_key=key)
    room.refresh_from_db()
    assert room.lobby_status == "running" and not room.paused
    assert room.deadline == instant + timedelta(minutes=10)
    assert room.reports.filter(kind="calendar").count() == 3
    claim(room, "p3", "Palm", claim_key=key)
    room.refresh_from_db()
    assert room.deadline == instant + timedelta(minutes=10)
    assert room.reports.filter(kind="calendar").count() == 3


@case("recruit-legacy-manual-start", "Recruitment: existing rooms retain operator start")
def test_legacy(operator):
    room = multiplayer.create_shared(operator, "Legacy", auto_start=False)
    for i in range(1, 4):
        claim(room, f"p{i}", f"House {i}")
    room.refresh_from_db()
    assert room.lobby_status == "waiting" and multiplayer.can_start(room)


@case("recruit-blocked-room", "Recruitment: cancelled or suspended recruitment admits nobody")
@pytest.mark.parametrize("blocked", ["cancelled", "revoked", "rotated"])
def test_blocked(operator, room, blocked):
    token = multiplayer.recruitment_token(room)
    if blocked == "cancelled":
        multiplayer.cancel_shared(operator, room.pk)
    elif blocked == "revoked":
        multiplayer.revoke_invitation(operator, room.pk, "p1")
    else:
        multiplayer.rotate_recruitment(operator, room.pk)
    with pytest.raises((RuleError, PermissionDenied)):
        multiplayer.choose_seat(token, "p1", "Cedar", uuid.uuid4())
    assert not room.memberships.exists()


@case("recruit-csrf", "Recruitment: a name and territory are claimed only by CSRF protected POST")
def test_csrf(room):
    client = Client(enforce_csrf_checks=True)
    url = reverse("shared_recruit", args=[multiplayer.recruitment_token(room)])
    response = client.get(url)
    assert client.post(url, {"actor": "p1", "house_name": "Cedar"}).status_code == 403
    response = client.post(
        url,
        {
            "actor": "p1",
            "house_name": "Cedar",
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        },
    )
    assert response.status_code == 302 and room.memberships.count() == 1
    lobby = client.get(response.url)
    assert lobby.status_code == 200 and lobby.context["spots_left"] == 2
    assert "Cedar" in lobby.content.decode()


@case(
    "recruit-poll-safe-counts",
    "Recruitment: polling reveals counts/names but no return credentials",
)
def test_poll(room):
    claim(room, "p2", "Cedar")
    response = Client().get(
        reverse("shared_recruit_state", args=[multiplayer.recruitment_token(room)])
    )
    data = response.json()
    assert data["spots_left"] == 2 and data["occupied"] == 1 and data["capacity"] == 3
    assert data["houses"]["p2"] == "Cedar"
    assert not {"token", "email", "revision", "seed", "state"}.intersection(data)


@case(
    "recruit-race-one-seat", "Recruitment: two concurrent choices cannot share or overwrite a house"
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_choice(room):
    token = multiplayer.recruitment_token(room)

    def choose(name):
        try:
            multiplayer.choose_seat(token, "p1", name, uuid.uuid4(), user=AnonymousUser())
            return "joined"
        except RuleError:
            return "occupied"

    assert sorted(concurrent_calls([lambda: choose("Cedar"), lambda: choose("Oak")])) == [
        "joined",
        "occupied",
    ]
    assert Participant.objects.filter(game=room).count() == 1


@case("recruit-race-replay", "Recruitment: concurrent duplicate submissions create one identity")
@pytest.mark.django_db(transaction=True)
def test_concurrent_replay(room):
    token, key = multiplayer.recruitment_token(room), uuid.uuid4()
    results = concurrent_calls([lambda: multiplayer.choose_seat(token, "p3", "Cedar", key).pk] * 2)
    assert results[0] == results[1] and room.memberships.count() == 1


@case("recruit-race-final-spot", "Recruitment: competing final admissions start exactly once")
@pytest.mark.django_db(transaction=True)
def test_final_race(room):
    claim(room, "p1", "Cedar")
    claim(room, "p2", "Oak")
    results = concurrent_calls(
        [lambda: claim(room, "p3", "Palm"), lambda: claim(room, "p3", "Willow")]
    )
    assert sum(isinstance(result, RuleError) for result in results) == 1
    room.refresh_from_db()
    assert room.lobby_status == "running" and room.memberships.count() == 3
    assert room.reports.filter(kind="calendar").count() == 3


@case(
    "recruit-rotated-claim-key",
    "Recruitment: rotating private credentials invalidates admission replay",
)
def test_claim_rotation(operator, room):
    key = uuid.uuid4()
    claim(room, "p1", "Cedar", claim_key=key)
    multiplayer.issue_invitation(operator, room.pk, "p1")
    with pytest.raises(PermissionDenied):
        claim(room, "p1", "Cedar", claim_key=key)
    assert room.memberships.count() == 1


@case("recruit-name-frozen", "Recruitment: names become immutable when the room starts")
def test_name_frozen(room):
    seat = claim(room, "p1", "Cedar")
    multiplayer.rename_house(seat, room.pk, "Blue Cedar")
    claim(room, "p2", "Oak")
    claim(room, "p3", "Palm")
    with pytest.raises(RuleError):
        multiplayer.rename_house(seat, room.pk, "Changed after start")
    room.refresh_from_db()
    assert room.state["players"]["p1"]["name"] == "Blue Cedar"


@case("recruit-guest-handoff", "Recruitment: choosing a house preserves the original guest solo")
def test_guest_handoff(room):
    client = Client()
    client.get(reverse("home"))
    solo = client.post(reverse("guest_start"), {"start_key": client.session["guest_start_key"]}).url
    url = reverse("shared_recruit", args=[multiplayer.recruitment_token(room)])
    client.get(url)
    response = client.post(url, {"actor": "p2", "house_name": "Guest Cedar"})
    assert response.status_code == 302
    lobby = client.get(response.url)
    assert "Guest Cedar" in lobby.content.decode() and lobby.context["return_url"]
    assert client.post(reverse("guest_restore")).url == solo


@case(
    "recruit-http-replay", "Recruitment: repeated native submissions reopen the same selected house"
)
def test_http_replay(room):
    client = Client()
    url = reverse("shared_recruit", args=[multiplayer.recruitment_token(room)])
    client.get(url)
    first = client.post(url, {"actor": "p2", "house_name": "Cedar"})
    second = client.post(url, {"actor": "p2", "house_name": "Cedar"})
    assert first.url == second.url and room.memberships.count() == 1


@case(
    "recruit-restored-final-invite",
    "Recruitment: a full room starts when its suspended invitation is restored",
)
def test_restore_invitation(operator, room):
    claim(room, "p1", "Cedar")
    multiplayer.revoke_invitation(operator, room.pk, "p1")
    claim(room, "p2", "Oak")
    claim(room, "p3", "Palm")
    room.refresh_from_db()
    assert room.lobby_status == "waiting" and room.deadline is None
    multiplayer.issue_invitation(operator, room.pk, "p1")
    room.refresh_from_db()
    assert room.lobby_status == "running" and room.deadline
