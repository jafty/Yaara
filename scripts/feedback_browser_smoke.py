"""Post-playtest form/news regressions on a disposable loopback application.

This script creates disposable users and games in the configured development
database. It intentionally refuses non-loopback servers. Missing optional artwork
does not establish visual acceptance; captures document the rendered controls.
"""

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yaara.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from simulation import engine, services  # noqa: E402
from simulation.models import Report  # noqa: E402


def fixture(language):
    user = get_user_model().objects.create_user(f"feedback-{language}-{secrets.token_hex(6)}")
    login = Client()
    login.force_login(user)
    forms = services.create_game(user, "Feedback forms", opponents="passive")
    forms.state["cities"]["c3"]["watch"] = 1
    engine.confirm_order(
        forms.state,
        "p2",
        {"kind": "raid", "target": "c3", "contributions": {"c4": 20}},
        "browser-incoming",
    )
    engine.advance_month(forms.state, "browser-departure")
    forms.state["cities"]["c3"]["stock"] = 50000
    forms.save()
    news = services.create_game(user, "Feedback news", opponents="passive")
    news.state["month"] = 2
    news.state["cities"]["c1"]["stock"] = 0
    news.save()
    Report.objects.filter(game=news).delete()
    for index in range(2):
        Report.objects.create(
            game=news,
            recipient="p1",
            month=1,
            kind="battle",
            title=f"Feedback report {index}",
            body=" ".join(["Observation conservée pour notre maison."] * 100),
        )
    native = services.create_game(user, "Native feedback", opponents="passive")
    return user, login.session.session_key, forms, news, native


def logged_context(browser, base, session, language, *, javascript=True, init_script=None):
    context = browser.new_context(
        locale=language,
        java_script_enabled=javascript,
        viewport={"width": 1440, "height": 1000},
    )
    context.add_cookies(
        [
            {"name": settings.SESSION_COOKIE_NAME, "value": session, "url": base},
            {"name": "django_language", "value": language, "url": base},
        ]
    )
    if init_script:
        context.add_init_script(init_script)
    return context


def notification_count(page, unread):
    badge = page.locator(".alerts-trigger")
    expect(badge).to_have_attribute("data-news-count", str(unread))
    alerts = int(badge.get_attribute("data-alert-count"))
    assert alerts > 0
    expect(badge.locator("[data-notification-count]")).to_have_text(str(unread + alerts))
    return alerts


def back_to_map(page):
    page.locator(".panel-close").click()
    expect(page.locator(".mail-panel")).to_have_count(0)
    expect(page.locator(".map-link")).to_be_visible()


def run_forms(browser, base, session, language, game, artifacts, javascript):
    context = logged_context(browser, base, session, language, javascript=javascript)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    url = f"{base}/games/{game.pk}/"
    form_url = f"{url}?tab=map&city=c4&action=expedition"
    page.goto(form_url)
    origin = page.locator('[data-origin="c3"]')
    origin.locator('input[type="number"]').fill("20")
    if javascript:
        expect(origin.locator("[data-origin-warning]")).not_to_be_empty()
    submit = page.locator('button[type="submit"][form="expedition-form"]')
    expect(submit).to_be_enabled()
    submit.click()
    expect(page.locator('input[name="payload"]')).to_have_count(1)
    page.goto(form_url)
    page.locator('[data-origin="c3"] input[type="number"]').fill("19")
    page.locator('button[type="submit"][form="expedition-form"]').click()
    expect(page.locator('.sheet-feedback[role="alert"]')).to_be_visible()
    expect(page.locator('[data-origin="c3"] input[type="number"]')).to_have_value("19")
    page.screenshot(path=str(artifacts / f"feedback-rejection-{language}-{javascript}.png"))
    if javascript:
        page.goto(f"{url}?tab=domain#turn-page")
        page.locator('form[action$="/advance/"] button').click()
        expect(page.locator(".map-workspace")).to_be_visible()
        expect(page.locator(".notice.success, .notice.info")).to_have_count(0)
    assert not errors, errors
    context.close()


def run_oversized_news(browser, base, session, language, game, artifacts):
    context = logged_context(browser, base, session, language)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base}/games/{game.pk}/?tab=map")
    notification_count(page, 2)
    # A report taller than its scroll pane still becomes read at its heading.
    page.add_style_tag(content=".letter-entry { min-height: 1500px; }")
    page.locator(".alerts-trigger").click()
    expect(page.locator(".mail-panel")).to_be_visible()
    article = page.locator(".letter-entry").first
    assert article.bounding_box()["height"] > page.locator(".sheet-body").bounding_box()["height"]
    notification_count(page, 1)
    assert "unread-report" not in (article.get_attribute("class") or "").split()
    highlighted = page.locator(".mail-alert-count")
    expect(highlighted).to_be_visible()
    assert highlighted.evaluate("el => getComputedStyle(el).backgroundColor") != "rgba(0, 0, 0, 0)"
    page.screenshot(path=str(artifacts / f"feedback-news-oversized-{language}.png"))
    back_to_map(page)
    notification_count(page, 1)
    page.reload()
    notification_count(page, 1)
    assert not errors, errors
    context.close()


def run_restricted_storage(browser, base, session, language, game, both_denied):
    storage_names = ["localStorage", "sessionStorage"] if both_denied else ["localStorage"]
    init = (
        """
        delete window.IntersectionObserver;
        for (const name of %s) Object.defineProperty(window, name, {
          configurable: true,
          get() { throw new DOMException('Storage unavailable', 'SecurityError'); }
        });
    """
        % storage_names
    )
    context = logged_context(browser, base, session, language, init_script=init)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base}/games/{game.pk}/?tab=mail")
    notification_count(page, 2)
    read = page.locator("[data-read-report]").first
    expect(read).to_be_visible()
    read.click()
    notification_count(page, 1)
    back_to_map(page)
    notification_count(page, 1)
    page.locator(".alerts-trigger").click()
    notification_count(page, 1)
    page.reload()
    # With both browser stores blocked, a document reload necessarily loses memory.
    notification_count(page, 2 if both_denied else 1)
    assert not errors, errors
    context.close()


def main():
    base = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    if urlsplit(base).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Feedback smoke only permits a disposable loopback application.")
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    fixtures = [(language, fixture(language)) for language in ("fr", "en")]
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"),
                args=["--no-sandbox"],
            )
            for language, (_, session, forms, news, native) in fixtures:
                run_forms(browser, base, session, language, forms, artifacts, True)
                run_forms(browser, base, session, language, native, artifacts, False)
                run_oversized_news(browser, base, session, language, news, artifacts)
                run_restricted_storage(browser, base, session, language, news, False)
                run_restricted_storage(browser, base, session, language, news, True)
                print(f"Feedback browser checks passed: {language}", flush=True)
            browser.close()
    finally:
        for _, (user, *_) in fixtures:
            user.delete()
    print("Both storage APIs blocked: receipts survive enhanced navigation, not full reload.")
    print("Artwork/font requests were not acceptance assertions; inspect final assets separately.")


if __name__ == "__main__":
    main()
