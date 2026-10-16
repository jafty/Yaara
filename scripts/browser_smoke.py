"""Exercise a real browser against a local server; creates one disposable account.

Usage: BASE_URL=http://127.0.0.1:8000 uv run python scripts/browser_smoke.py
CHROMIUM_PATH can select a system Chromium; otherwise Playwright's browser is used.
"""

import os
import secrets
import shutil
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
artifacts = Path("artifacts")
artifacts.mkdir(exist_ok=True)
username = "browser_" + secrets.token_hex(5)
password = secrets.token_urlsafe(24)

with sync_playwright() as playwright:
    executable = os.getenv("CHROMIUM_PATH") or shutil.which("chromium")
    browser = playwright.chromium.launch(executable_path=executable, headless=True)
    page = browser.new_page(
        viewport={"width": 1440, "height": 1100}, device_scale_factor=1, locale="fr-FR"
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url + "/accounts/signup/")
    page.locator("#id_username").fill(username)
    page.locator("#id_password1").fill(password)
    page.locator("#id_password2").fill(password)
    page.get_by_role("button", name="Créer mon compte").click()
    expect(page.get_by_role("heading", name="Chaque règne, une histoire.")).to_be_visible()
    assert page.locator(".sidebar").count() == 1, "The pre-game interface is retained"
    page.goto(base_url + "/games/new/")
    page.locator("#id_title").fill("Les chroniques d’Ambre")
    page.locator("#id_opponents").select_option("passive")
    page.get_by_role("button", name="Apposer mon sceau").click()
    expect(page.get_by_role("heading", name="Les terres sous votre sceau")).to_be_visible()
    game_url = page.url
    assert page.locator(".city-entry").count() == 3
    assert page.locator(".sidebar, .stats-strip, svg, img").count() == 0
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 255, 255)")
    city_leaf = page.locator("#city-c2")
    city_leaf.locator("summary").click()
    expect(city_leaf.locator(".unfolded")).to_be_visible()
    expect(city_leaf).to_contain_text("1\u00a0000 habitants")
    city_leaf.locator("summary").click()
    page.screenshot(path=str(artifacts / "domain-desktop.png"), full_page=True)
    # No enemy population or stock in the JSON response.
    state = page.request.get(game_url + "state/").json()
    assert "seed" not in state["game"]
    assert all("stock" not in city for city in state["view"]["cities"] if not city["owned"])
    page.get_by_role("link", name="Décrets", exact=True).click()
    work = page.locator(".decree-choice").filter(has=page.locator('input[value="storage"]'))
    work.locator("summary").click()
    work.locator('input[type="checkbox"][value="c1"]').check()
    work.get_by_role("button", name="Faire relire ce décret").click()
    expect(page.locator(".decree-reading")).to_be_visible()
    expect(page.get_by_role("heading", name="La part demandée aux greniers")).to_be_visible()
    page.screenshot(path=str(artifacts / "decree-letter-desktop.png"), full_page=True)
    page.get_by_role("button", name="Sceller ce décret").click()
    expect(page.locator(".orders-register")).to_contain_text("Confirmé")
    page.locator(".orders-register").get_by_role("button", name="Retirer ce décret").click()
    expect(page.locator(".orders-register")).to_contain_text("Annulé")
    # Confirm and resolve a raid through actual forms and three manual ticks.
    page.locator("#expedition > summary").click()
    page.locator("#mission-target").select_option("c4")
    page.locator('input[name="men_c3"]').fill("45")
    expect(page.locator("#army-cost")).to_contain_text("132")
    page.get_by_role("button", name="Faire relire l’ordre d’expédition").click()
    expect(page.get_by_role("heading", name="Les hommes engagés")).to_be_visible()
    page.get_by_role("button", name="Sceller ce décret").click()
    page.screenshot(path=str(artifacts / "decrees-desktop.png"), full_page=True)
    for month in range(1, 4):
        page.get_by_role("button", name=f"Clore le mois {month}", exact=True).click()
        expect(page.locator(".dateline")).to_contain_text(f"mois {month}")
    page.get_by_role("link", name="Correspondance", exact=True).click()
    for title in ("Retour à Namar", "Pillage réussi à Sefra"):
        letter = page.locator(".letter-entry").filter(has=page.locator("summary", has_text=title))
        if letter.get_attribute("open") is None:
            letter.locator("summary").click()
        expect(letter.locator(".letter-text")).to_be_visible()
    expect(page.locator(".correspondence")).to_contain_text(
        "Nos survivants disent avoir rencontré entre"
    )
    page.screenshot(path=str(artifacts / "letters-desktop.png"), full_page=True)
    page.goto(game_url)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(artifacts / "domain-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Mobile page overflows horizontally"
    )
    page.get_by_role("link", name="Décrets", exact=True).click()
    page.locator("#expedition > summary").click()
    page.locator("#mission-target").select_option("c4")
    page.locator('input[name="men_c3"]').fill("20")
    page.screenshot(path=str(artifacts / "decrees-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        page.evaluate(
            "[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 20).map(e => [e.tagName, e.className, e.getBoundingClientRect().right])"
        )
    )
    page.reload()
    expect(page.locator(".orders-register")).to_contain_text("Achevé")
    page.set_viewport_size({"width": 320, "height": 700})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    # Language selection persists across requests; translated reports keep the same facts.
    page.locator("#language").select_option("en")
    page.get_by_role("button", name="Choisir", exact=True).click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_role("heading", name="What you will dictate")).to_be_visible()
    expect(page.locator(".orders-register")).to_contain_text("Completed")
    page.locator("#expedition > summary").click()
    page.locator("#mission-target").select_option("c4")
    expect(page.locator("#mission-help")).to_contain_text("Our people will try to take")
    page.get_by_role("link", name="Letters", exact=True).click()
    expect(page.locator(".correspondence")).to_contain_text(
        "Our survivors say they encountered between"
    )
    page.get_by_role("link", name="Decrees", exact=True).click()
    work = page.locator(".decree-choice").filter(has=page.locator('input[value="storage"]'))
    work.locator("summary").click()
    work.locator('input[type="checkbox"][value="c2"]').check()
    work.get_by_role("button", name="Have this decree read back").click()
    expect(
        page.get_by_role("heading", name="The share requested from the granaries")
    ).to_be_visible()
    page.get_by_role("button", name="Seal this decree").click()
    for month in range(4, 9):
        page.get_by_role("button", name=f"Close month {month}", exact=True).click()
    page.get_by_role("link", name="Letters", exact=True).click()
    expect(page.locator(".correspondence")).to_contain_text("have enlarged the granary")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#language").select_option("fr")
    page.get_by_role("button", name="Choose", exact=True).click()
    expect(page.locator("html")).to_have_attribute("lang", "fr")
    expect(page.locator(".correspondence")).to_contain_text("ont agrandi le grenier")
    page.get_by_role("button", name="Quitter", exact=True).click()
    expect(page.get_by_role("heading", name="Entrer dans Yaara")).to_be_visible()
    page.locator("#id_username").fill(username)
    page.locator("#id_password").fill(password)
    page.get_by_role("button", name="Reprendre mon règne").click()
    expect(page.get_by_role("heading", name="Les chroniques d’Ambre")).to_be_visible()
    assert not errors, errors
    browser.close()
print(
    "Browser smoke passed: signup, persistence, build preview/cancel, raid/return, privacy, desktop/mobile, French/English selection and reports, completed-work tense, logout/login."
)
