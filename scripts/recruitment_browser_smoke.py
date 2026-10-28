"""Real recruitment journeys against a disposable local server and PostgreSQL.

Run with BASE_URL=http://127.0.0.1:8000 and DATABASE_URL for that server.
Creates disposable users/games; never run against production.
"""

import os
import re
import secrets
import shutil
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ARTIFACTS = Path("artifacts/recruitment")


def context_for(browser, language, javascript=True):
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, java_script_enabled=javascript
    )
    context.add_cookies([{"name": "django_language", "value": language, "url": BASE_URL}])
    return context


def check_layout(page):
    def assert_fit(label):
        if not page.evaluate("document.documentElement.scrollWidth <= innerWidth"):
            page.screenshot(path=str(ARTIFACTS / f"overflow-{label}.png"), full_page=True)
            overflow = page.locator("body *").evaluate_all(
                "elements => elements.filter(el => el.getBoundingClientRect().right > innerWidth)"
                ".map(el => ({tag:el.tagName, cls:el.className, text:el.textContent.slice(0, 80)})).slice(0, 12)"
            )
            raise AssertionError(f"{page.url} {label}: {overflow}")

    for width in (320, 390, 1440):
        page.set_viewport_size({"width": width, "height": 844})
        assert_fit(str(width))
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    assert_fit("large-text")
    page.evaluate("document.documentElement.style.removeProperty('font-size')")


def state_for(page, game_url):
    response = page.request.get(game_url + "state/")
    assert response.status == 200
    return response.json()


def work_order(page, game_url, city, seal=True):
    page.goto(game_url + "?tab=constructions&action=irrigation")
    page.locator(f'input[name="cities"][value="{city}"]').check()
    page.locator("form[data-work-form] button[type=submit]").click()
    expect(page.locator(".review-panel")).to_be_visible()
    expect(page.locator('.decree-reading input[name="payload"]')).to_have_count(1)
    if seal:
        page.locator(".decree-reading > form button[type=submit]").click()


def guest_journey(browser, language, javascript=True):
    context = context_for(browser, language, javascript)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE_URL + "/")
    expect(page.locator("[data-guest-entry]")).to_be_visible()
    check_layout(page)
    page.screenshot(path=str(ARTIFACTS / f"entry-{language}.png"), full_page=True)
    page.locator('form[action="/play/"] button[type=submit]').focus()
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/games/[0-9a-f-]+/"))
    game_url = page.url.split("?")[0]
    expect(page.locator("[data-guest-access]")).to_be_visible()
    initial = state_for(page, game_url)["view"]
    assert len(initial["owned_cities"]) == 3 and initial["available_stock"] == 2_700_000
    check_layout(page)
    page.screenshot(path=str(ARTIFACTS / f"first-council-{language}.png"), full_page=True)
    outsider = context_for(browser, language)
    assert outsider.request.get(game_url + "state/", max_redirects=0).status in (302, 403, 404)
    outsider.close()
    work_order(page, game_url, "c1")
    assert state_for(page, game_url)["view"]["sealed_count"] == 1
    page.goto(game_url)
    expect(page.locator('a[href*="#turn-page"]').first).to_be_visible()
    for _ in range(4):
        page.goto(game_url + "?tab=domain#turn-page")
        page.locator('form[action$="/advance/"] button').click()
    result = state_for(page, game_url)["view"]
    assert next(city for city in result["owned_cities"] if city["id"] == "c1")["irrigation"] == 1
    page.goto(game_url)
    page.screenshot(
        path=str(ARTIFACTS / f"guest-result-{language}-{javascript}.png"), full_page=True
    )
    page.locator('a[href^="/save/"]').first.click()
    check_layout(page)
    page.screenshot(path=str(ARTIFACTS / f"save-{language}.png"), full_page=True)
    username = "recruitment_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    page.locator("input[name=username]").fill(username)
    page.locator("input[name=password1]").fill(password)
    page.locator("input[name=password2]").fill(password)
    page.locator("form:has(input[name=password1]) button[type=submit]").click()
    page.wait_for_url(re.compile(re.escape(game_url)))
    assert state_for(page, game_url)["view"]["open_moon"] == result["open_moon"]
    expect(page.locator("[data-guest-access]")).to_have_count(0)
    page.goto(game_url + "?tab=domain")
    page.locator('form[action="/accounts/logout/"] button').click()
    page.goto(BASE_URL + "/accounts/login/")
    page.locator("input[name=username]").fill(username)
    page.locator("input[name=password]").fill(password)
    page.locator("form:has(input[name=password]) button[type=submit]").click()
    page.goto(game_url)
    assert state_for(page, game_url)["view"]["open_moon"] == result["open_moon"]
    assert not errors, errors
    context.close()
    print(f"Guest journey passed: language={language}, JavaScript={javascript}", flush=True)


def operator_identity():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yaara.settings")
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    username = "operator_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    user = get_user_model().objects.create_user(username=username, password=password)
    user.user_permissions.add(Permission.objects.get(codename="manage_multiplayer_games"))
    return username, password


def login_operator(page, operator):
    page.goto(BASE_URL + "/accounts/login/")
    page.locator("input[name=username]").fill(operator[0])
    page.locator("input[name=password]").fill(operator[1])
    page.locator("form:has(input[name=password]) button[type=submit]").click()


def create_room(admin):
    admin.goto(BASE_URL + "/manage/")
    admin.locator("input[name=title]").fill("Three houses " + secrets.token_hex(4))
    admin.locator('[name="play_window"]').fill("Today: a supervised browser acceptance session")
    admin.locator('[name="reign_months"]').select_option("120")
    admin.locator('[name="interval_minutes"]').select_option("10")
    admin.locator("form:has(input[name=title]) button[type=submit]").click()
    admin.wait_for_url(re.compile(r"/manage/[0-9a-f-]+/"))
    room_url = admin.url
    check_layout(admin)
    invitations = [
        urljoin(BASE_URL, admin.locator(f'[data-invite-seat="p{seat}"]').get_attribute("href"))
        for seat in (1, 2, 3)
    ]
    admin.context.grant_permissions(["clipboard-read", "clipboard-write"])
    for index, invitation in enumerate(invitations):
        field = admin.locator("[data-invitation-url]").nth(index)
        expect(field).to_have_value(invitation)
        field.focus()
        field.press("ControlOrMeta+A")
        field.press("ControlOrMeta+C")
        assert admin.evaluate("navigator.clipboard.readText()") == invitation
    return (
        room_url,
        invitations,
        urljoin(BASE_URL, admin.locator("[data-recruitment-link]").get_attribute("href")),
    )


def multiplayer_journey(browser, language, operator):
    admin_context = context_for(browser, language)
    admin = admin_context.new_page()
    login_operator(admin, operator)
    room_url, invitations, recruitment = create_room(admin)
    players = []
    for seat, invitation in enumerate(invitations, 1):
        context = context_for(browser, language, javascript=seat != 3)
        page = context.new_page()
        page.goto(recruitment)
        expect(page.locator("[data-spots-left]")).to_have_text(str(4 - seat))
        check_layout(page)
        page.screenshot(
            path=str(ARTIFACTS / f"choose-house-{language}-p{seat}.png"), full_page=True
        )
        observer_context = None
        if seat == 1:
            observer_context = context_for(browser, language)
            observer = observer_context.new_page()
            observer.goto(recruitment)
            observer.locator('input[name=actor][value="p1"]').check()
            observer.locator("input[name=house_name]").fill("A name worth keeping")
        page.locator(f'input[name=actor][value="p{seat}"]').check()
        page.locator("input[name=house_name]").fill(f"House Cedar {language} {seat}")
        page.locator("[data-recruitment-form] button").click()
        if observer_context is not None:
            expect(observer.locator('input[name=actor][value="p1"]')).to_be_disabled(timeout=10000)
            expect(observer.locator("input[name=house_name]")).to_have_value("A name worth keeping")
            expect(observer.locator("[data-spots-left]")).to_have_text("2")
            observer_context.close()
        if seat < 3:
            page.wait_for_url(re.compile(r"/games/[0-9a-f-]+/lobby/"))
            expect(page.locator("[data-shared-lobby]")).to_be_visible()
            expect(page.locator("[data-spots-left]")).to_have_text(str(3 - seat))
        else:
            page.wait_for_url(re.compile(r"/games/[0-9a-f-]+/$"))
        assert page.locator("input[type=password]").count() == 0
        check_layout(page)
        page.screenshot(path=str(ARTIFACTS / f"lobby-{language}-p{seat}.png"), full_page=True)
        players.append((context, page))
    game_url = players[-1][1].url
    assert admin.request.get(game_url + "state/", max_redirects=0).status in (403, 404)
    expect(admin.locator("[data-spots-left]")).to_have_text("0", timeout=10000)
    admin.screenshot(path=str(ARTIFACTS / f"operator-ready-{language}.png"), full_page=True)
    for _, page in players:
        page.bring_to_front()
        page.wait_for_url(re.compile(re.escape(game_url) + r"(?:\?.*)?$"), timeout=20000)
        expect(page.locator(".reign-header a[data-section]")).to_have_count(3)
        assert page.locator('form[action$="/advance/"]').count() == 0
        assert page.locator('form[action$="/pause/"]').count() == 0
        page.locator('.reign-header a[data-section="domain"]').click()
        page.locator('a[href$="/email/"]').click()
        expect(page.locator("[data-email-preferences]")).to_be_visible()
        expect(page.locator('[name="raid"]')).not_to_be_checked()
        check_layout(page)
        page.screenshot(path=str(ARTIFACTS / f"email-preferences-{language}.png"), full_page=True)
        page.goto(game_url)
    for seat, (_, page) in enumerate(players, 1):
        view = state_for(page, game_url)["view"]
        assert {city["id"] for city in view["owned_cities"]} == {
            f"c{index}" for index in range((seat - 1) * 3 + 1, seat * 3 + 1)
        }
        assert "combativity" not in str(view)
    first, second = players[0][1], players[1][1]
    work_order(second, game_url, "c4", seal=False)
    second_before = state_for(second, game_url)["game"]["revision"]
    work_order(first, game_url, "c1")
    assert state_for(second, game_url)["game"]["revision"] == second_before
    second.locator(".decree-reading > form button[type=submit]").click()
    assert state_for(second, game_url)["view"]["sealed_count"] == 1
    assert state_for(first, game_url)["view"]["sealed_count"] == 1
    for seat, invitation in enumerate(invitations, 1):
        resumed_context = context_for(browser, language, javascript=seat != 3)
        resumed = resumed_context.new_page()
        resumed.goto(invitation)
        if seat == 3:
            resumed.locator("form[data-seat-entry] button[type=submit]").click()
        resumed.wait_for_url(re.compile(re.escape(game_url) + r"(?:\?.*)?$"))
        assert {city["id"] for city in state_for(resumed, game_url)["view"]["owned_cities"]} == {
            f"c{index}" for index in range((seat - 1) * 3 + 1, seat * 3 + 1)
        }
        check_layout(resumed)
        resumed.screenshot(
            path=str(ARTIFACTS / f"multiplayer-return-{language}-p{seat}.png"), full_page=True
        )
        resumed_context.close()
    for context, _ in players:
        context.close()
    admin_context.close()
    print(f"Three-house multiplayer journey passed: language={language}", flush=True)


def identity_handoff_journey(browser, operator):
    """Seat credentials preserve a guest trial without conveying operator privileges."""
    admin_context = context_for(browser, "en")
    admin = admin_context.new_page()
    login_operator(admin, operator)
    room_url, invitations, _recruitment = create_room(admin)
    admin.goto(invitations[0])
    admin.wait_for_url(re.compile(r"/games/[0-9a-f-]+/lobby/"))
    game_url = admin.url.removesuffix("lobby/")
    assert admin.request.get(room_url, max_redirects=0).status == 200

    guest_context = context_for(browser, "en", javascript=False)
    guest = guest_context.new_page()
    guest.goto(BASE_URL + "/")
    guest.locator('form[action="/play/"] button[type=submit]').click()
    guest.wait_for_url(re.compile(r"/games/[0-9a-f-]+/"))
    solo_url = guest.url.split("?")[0]
    work_order(guest, solo_url, "c1")
    guest.goto(invitations[1])
    guest.locator("form[data-seat-entry] button[type=submit]").click()
    expect(guest.locator("[data-shared-lobby]")).to_be_visible()
    guest.locator("[data-guest-restore] button").click()
    guest.wait_for_url(solo_url)
    assert state_for(guest, solo_url)["view"]["sealed_count"] == 1
    guest.goto(invitations[1])
    guest.locator("form[data-seat-entry] button[type=submit]").click()
    expect(guest.locator("[data-shared-lobby]")).to_be_visible()

    third_context = context_for(browser, "en")
    third = third_context.new_page()
    third.goto(invitations[2])
    third.wait_for_url(re.compile(re.escape(game_url) + r"(?:\?.*)?$"))
    admin.goto(game_url)
    assert {city["id"] for city in state_for(admin, game_url)["view"]["owned_cities"]} == {
        "c1",
        "c2",
        "c3",
    }

    bearer_context = context_for(browser, "en")
    bearer = bearer_context.new_page()
    bearer.goto(invitations[0])
    bearer.wait_for_url(re.compile(re.escape(game_url) + r"(?:\?.*)?$"))
    assert bearer.request.get(BASE_URL + "/manage/", max_redirects=0).status == 403
    assert {city["id"] for city in state_for(bearer, game_url)["view"]["owned_cities"]} == {
        "c1",
        "c2",
        "c3",
    }
    assert bearer.request.get(solo_url + "state/", max_redirects=0).status in (403, 404)
    guest.reload()
    guest.wait_for_url(re.compile(re.escape(game_url) + r"(?:\?.*)?$"))
    guest.locator("[data-guest-restore] button").click()
    guest.wait_for_url(solo_url)
    assert state_for(guest, solo_url)["view"]["sealed_count"] == 1
    for context in (admin_context, guest_context, third_context, bearer_context):
        context.close()
    print("Operator identity and original guest trial handoffs passed", flush=True)


def main():
    assert urlparse(BASE_URL).hostname in {"127.0.0.1", "localhost"}, "Disposable local server only"
    assert "postgres" in os.environ.get("DATABASE_URL", ""), "Use disposable PostgreSQL"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    operator = operator_identity()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_PATH") or shutil.which("chromium"), headless=True
        )
        for language in ("fr", "en"):
            guest_journey(browser, language)
        guest_journey(browser, "en", javascript=False)
        for language in ("fr", "en"):
            multiplayer_journey(browser, language, operator)
        identity_handoff_journey(browser, operator)
        browser.close()
    print(
        "Recruitment journeys passed in French and English: guest order/result/account/return; "
        "operator-created room, three passwordless invitees, automatic lobby-to-game transition, "
        "private previews, own-house access, return links, operator/guest identity preservation, "
        "no-JavaScript fallback and responsive layout."
    )


if __name__ == "__main__":
    main()
