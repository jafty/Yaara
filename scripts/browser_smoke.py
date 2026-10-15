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
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url + "/accounts/signup/")
    page.locator("#id_username").fill(username)
    page.locator("#id_password1").fill(password)
    page.locator("#id_password2").fill(password)
    page.get_by_role("button", name="Créer mon compte").click()
    expect(page.get_by_role("heading", name="Chaque règne, une histoire.")).to_be_visible()
    page.goto(base_url + "/games/new/")
    page.locator("#id_title").fill("Les chroniques d’Ambre")
    page.locator("#id_opponents").select_option("passive")
    page.get_by_role("button", name="Apposer mon sceau").click()
    expect(page.get_by_role("heading", name="Votre domaine.")).to_be_visible()
    game_url = page.url
    assert page.locator("svg .map-city").count() == 9
    page.screenshot(path=str(artifacts / "domain-desktop.png"), full_page=True)
    # No enemy population or stock in the JSON response.
    state = page.request.get(game_url + "state/").json()
    assert "seed" not in state["game"]
    assert all("stock" not in city for city in state["view"]["cities"] if not city["owned"])
    page.get_by_role("link", name="Décrets", exact=True).click()
    work = page.locator(".work-form").filter(has=page.locator('input[value="storage"]'))
    work.locator('input[type="checkbox"][value="c1"]').check()
    work.get_by_role("button", name="Préparer le décret").click()
    expect(page.get_by_role("heading", name="Les termes du décret")).to_be_visible()
    page.get_by_role("button", name="Sceller ce décret").click()
    expect(page.locator(".orders-panel")).to_contain_text("Confirmé")
    page.locator(".orders-panel").get_by_role("button", name="Annuler").click()
    expect(page.locator(".orders-panel")).to_contain_text("Annulé")
    # Confirm and resolve a raid through actual forms and three manual ticks.
    page.locator("#mission-target").select_option("c4")
    page.locator('input[name="men_c3"]').fill("45")
    expect(page.locator("#army-cost")).to_contain_text("132")
    page.get_by_role("button", name="Examiner l’expédition").click()
    expect(page.get_by_role("heading", name="Les hommes engagés")).to_be_visible()
    page.get_by_role("button", name="Sceller ce décret").click()
    page.screenshot(path=str(artifacts / "decrees-desktop.png"), full_page=True)
    for month in range(1, 4):
        page.get_by_role("button", name="Passer au mois suivant").click()
        expect(page.locator(".calendar>strong")).to_contain_text(f"Mois {month}")
    page.get_by_role("link", name="Correspondance", exact=True).click()
    expect(page.get_by_role("heading", name="Retour à Namar")).to_be_visible()
    expect(page.get_by_role("heading", name="Pillage réussi à Sefra")).to_be_visible()
    page.screenshot(path=str(artifacts / "letters-desktop.png"), full_page=True)
    page.goto(game_url)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(artifacts / "domain-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Mobile page overflows horizontally"
    )
    page.get_by_role("link", name="Décrets", exact=True).click()
    page.screenshot(path=str(artifacts / "decrees-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        page.evaluate(
            "[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 20).map(e => [e.tagName, e.className, e.getBoundingClientRect().right])"
        )
    )
    page.reload()
    expect(page.locator(".orders-panel")).to_contain_text("Achevé")
    page.get_by_role("button", name="Quitter", exact=True).click()
    expect(page.get_by_role("heading", name="Entrer dans Yaara")).to_be_visible()
    page.locator("#id_username").fill(username)
    page.locator("#id_password").fill(password)
    page.get_by_role("button", name="Reprendre mon règne").click()
    expect(page.get_by_role("heading", name="Les chroniques d’Ambre")).to_be_visible()
    assert not errors, errors
    browser.close()
print(
    "Browser smoke passed: signup, persistence, build preview/cancel, raid/return, privacy, desktop/mobile, logout/login."
)
