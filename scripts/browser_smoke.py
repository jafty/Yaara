"""Real bilingual browser journeys against a disposable local server/database."""

import os
import secrets
import shutil
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
artifacts = Path("artifacts")
artifacts.mkdir(exist_ok=True)


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "The page overflows horizontally"
    )


with sync_playwright() as playwright:
    executable = os.getenv("CHROMIUM_PATH") or shutil.which("chromium")
    browser = playwright.chromium.launch(executable_path=executable, headless=True)
    for language in ("fr", "en"):
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        context.add_cookies([{"name": "django_language", "value": language, "url": base_url}])
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        en = language == "en"
        username = "browser_" + secrets.token_hex(5)
        password = secrets.token_urlsafe(24)
        page.goto(base_url + "/accounts/signup/")
        page.locator("#id_username").fill(username)
        page.locator("#id_password1").fill(password)
        page.locator("#id_password2").fill(password)
        page.locator(".stack-form button").click()
        expect(
            page.get_by_role(
                "heading", name="Every reign, a story." if en else "Chaque règne, une histoire."
            )
        ).to_be_visible()
        assert page.locator(".sidebar").count() == 1
        page.goto(base_url + "/games/new/")
        page.locator("#id_title").fill("The Amber Chronicles" if en else "Les chroniques d’Ambre")
        page.locator("#id_opponents").select_option("passive")
        page.locator(".game-setup button").click()
        expect(
            page.get_by_role(
                "heading",
                name="Your house council" if en else "Le conseil de votre maison",
            )
        ).to_be_visible()
        game_url = page.url
        expect(page.locator("#recent-letters")).to_be_visible()
        expect(page.locator("#upcoming-heading")).to_be_visible()
        assert page.locator(".house-accounts").count() == 0
        assert page.locator(".bookmarks a").count() == 3
        page.locator('.bookmarks a[href$="?tab=constructions"]').click()
        expect(
            page.get_by_role("heading", name="Works" if en else "Chantiers", exact=True)
        ).to_be_visible()
        page.goto(game_url)
        assert page.locator("article.city-entry").count() == 3
        assert page.locator(".sidebar, .stats-strip, img, table").count() == 0
        assert page.locator(".city-entry details").count() == 0
        expect(page.locator("body")).to_have_css("background-color", "rgb(253, 251, 247)")
        expect(page.locator(".dateline")).to_contain_text("Moon 1" if en else "Lune 1")
        page.screenshot(path=str(artifacts / f"domain-desktop-{language}.png"), full_page=True)
        page.locator('.bookmarks a[href$="?tab=constructions"]').click()
        # Local forges keep the same atomic multi-city draft/seal/cancel workflow.
        forge = page.locator("#work-forge")
        forge.locator("summary").click()
        forge.locator('input[value="c1"]').check()
        forge.locator('input[value="c2"]').check()
        expect(forge.locator("[data-work-cost]")).to_have_text(
            "1,200,000" if en else "1\u202f200\u202f000"
        )
        forge.locator('button[type="submit"]').click()
        expect(page.locator(".decree-reading")).to_contain_text(
            "reinforced equipment" if en else "équipement renforcé"
        )
        expect(page.locator('.bookmarks a[aria-current="page"]')).to_have_attribute(
            "data-section", "constructions"
        )
        page.locator(".wax-seal").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "600,000" if en else "600\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "1,800,000" if en else "1\u00a0800\u00a0000"
        )
        canals = page.locator("#work-irrigation")
        canals.locator("summary").click()
        canals.locator('input[value="c1"]').check()
        expect(canals.locator("[data-budget-note]")).to_have_text(
            "This work needs 600,000 more Measures."
            if en
            else "Il manque 600\u202f000 Mesures pour cet ouvrage."
        )
        work = page.locator("#work-storage")
        work.locator("summary").click()
        work.locator("[data-select-cities]").click()
        expect(work.locator("[data-city-count]")).to_have_text("3")
        expect(work.locator("[data-work-cost]")).to_have_text(
            "1,500,000" if en else "1\u202f500\u202f000"
        )
        work.locator("[data-clear-cities]").click()
        expect(work.locator("[data-city-count]")).to_have_text("0")
        work.locator('input[value="c1"]').check()
        work.locator('input[value="c2"]').check()
        expect(work.locator("[data-city-count]")).to_have_text("2")
        expect(work.locator("[data-work-cost]")).to_have_text(
            "1,000,000" if en else "1\u202f000\u202f000"
        )
        work.locator('button[type="submit"]').click()
        expect(page.locator(".decree-reading")).to_contain_text("Qasr")
        expect(page.locator(".decree-reading")).to_contain_text("Tamesh")
        expect(page.locator(".unsealed-leaf")).to_contain_text(
            "Unsealed draft" if en else "Brouillon sans sceau"
        )
        # The footer language action reopens the same signed, read-only draft.
        for selected_language in ("fr" if en else "en", language):
            page.locator("#language").select_option(selected_language)
            page.locator(".language-switch button").click()
            expect(page.locator(".unsealed-leaf")).to_contain_text(
                "Unsealed draft" if selected_language == "en" else "Brouillon sans sceau"
            )
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "1,800,000" if en else "1\u00a0800\u00a0000"
        )
        page.screenshot(
            path=str(artifacts / f"decree-letter-desktop-{language}.png"), full_page=True
        )
        page.locator(".wax-seal").click()
        expect(page.locator(".orders-register")).to_contain_text("Confirmed" if en else "Confirmé")
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "800,000" if en else "800\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".orders-register")).to_contain_text("Cancelled" if en else "Annulé")
        page.locator('.bookmarks a[data-section="wars"]').click()
        assert page.locator(".map-city").count() == 9
        assert page.locator(".map-road").count() == 0
        page.locator('.map-city[href*="city=c4"]').click()
        assert page.locator("[data-local-accounts]").count() == 0
        expect(page.locator("#map-context")).to_contain_text("Sefra")
        page.screenshot(path=str(artifacts / f"map-context-desktop-{language}.png"), full_page=True)
        page.locator('[data-expedition-kind="capture"]').click()
        expect(page.locator("#mission-kind")).to_have_value("capture")
        expect(page.locator("#mission-target")).to_have_value("c4")
        page.locator("#mission-kind").select_option("raid")
        page.locator('input[name="men_c3"]').fill("45")
        expect(page.locator("#army-cost")).to_contain_text("132,500" if en else "132\u202f500")
        page.locator(".expedition-form button").click()
        expect(
            page.get_by_role("heading", name="The people committed" if en else "Les hommes engagés")
        ).to_be_visible()
        page.locator(".wax-seal").click()
        assert page.locator(".map-engaged").count() == 1
        page.screenshot(path=str(artifacts / f"decrees-desktop-{language}.png"), full_page=True)
        for moon in range(1, 4):
            page.locator('.bookmarks a[data-section="domain"]').click()
            page.locator("#turn-page button.primary-action").click()
            expect(page.locator(".dateline")).to_contain_text(
                f"Moon {moon + 1}" if en else f"Lune {moon + 1}"
            )
        page.locator('.bookmarks a[href$="?tab=wars"]').click()
        expect(
            page.get_by_role("heading", name="Expeditions" if en else "Expéditions", exact=True)
        ).to_be_visible()
        page.locator('.bookmarks a[data-section="domain"]').click()
        page.locator('a[href="?tab=letters"]').click()
        for title in (
            ("Return to Namar", "Successful raid at Sefra")
            if en
            else ("Retour à Namar", "Pillage réussi à Sefra")
        ):
            expect(
                page.locator(".correspondence").get_by_role("heading", name=title)
            ).to_be_visible()
        expect(page.locator(".correspondence")).to_contain_text(
            "Our survivors say they encountered between"
            if en
            else "Nos survivants disent avoir rencontré entre"
        )
        page.screenshot(path=str(artifacts / f"letters-desktop-{language}.png"), full_page=True)
        # Switching the same persisted letters translates their bodies too.
        page.locator("#language").select_option("fr" if en else "en")
        page.locator(".language-switch button").click()
        expect(page.locator(".correspondence")).to_contain_text(
            "J’ai fait inscrire le retour" if en else "I have recorded the return"
        )
        page.locator("#language").select_option(language)
        page.locator(".language-switch button").click()
        page.goto(game_url)
        state = page.request.get(game_url + "state/").json()
        assert "seed" not in state["game"]
        assert all("stock" not in city for city in state["view"]["cities"] if not city["owned"])
        page.goto(game_url + "?tab=city&city=c2")
        expect(page.locator("[data-local-accounts]")).to_be_visible()
        page.locator('a[href="?tab=decrees&city=c2"]').click()
        expect(page.locator('#work-storage input[value="c2"]')).to_be_checked()
        expect(page.locator('#work-storage input[value="c1"]')).not_to_be_checked()
        page.goto(game_url + "?tab=city&city=c4")
        assert page.locator("[data-local-accounts]").count() == 0
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            for suffix in (
                "",
                "?tab=city&city=c2",
                "?tab=letters",
                "?tab=constructions",
                "?tab=wars",
                "?tab=decrees&action=expedition",
            ):
                page.goto(game_url + suffix)
                no_overflow(page)
                assert page.locator(".reign-header").bounding_box()["height"] < 130
                for link in page.locator(".bookmarks a").all():
                    box = link.bounding_box()
                    assert box["height"] >= 44 and box["width"] >= 44
                if suffix in ("", "?tab=constructions", "?tab=wars"):
                    if suffix == "?tab=wars":
                        for city in page.locator(".map-city").all():
                            box = city.bounding_box()
                            assert box["height"] >= 44 and box["width"] >= 44
                    folio = {"": "council", "?tab=constructions": "works", "?tab=wars": "map"}[
                        suffix
                    ]
                    page.screenshot(
                        path=str(artifacts / f"{folio}-mobile-{width}-{language}.png"),
                        full_page=True,
                    )
            page.screenshot(
                path=str(artifacts / f"decrees-mobile-{width}-{language}.png"), full_page=True
            )
        # Native checklists and read-only previews also work without JavaScript.
        plain = browser.new_context(
            storage_state=context.storage_state(),
            java_script_enabled=False,
            viewport={"width": 320, "height": 844},
        )
        plain_page = plain.new_page()
        plain_page.goto(game_url + "?tab=constructions")
        plain_forge = plain_page.locator("#work-forge")
        plain_forge.locator("summary").click()
        plain_forge.locator('input[value="c1"]').check()
        plain_forge.locator('button[type="submit"]').click()
        expect(plain_page.locator(".unsealed-leaf")).to_be_visible()
        plain_page.goto(game_url + "?tab=wars")
        plain_page.locator('.map-city[href*="city=c4"]').click()
        expect(plain_page.locator("#map-context")).to_contain_text("Sefra")
        no_overflow(plain_page)
        plain_page.screenshot(
            path=str(artifacts / f"map-context-mobile-{language}.png"), full_page=True
        )
        plain_page.locator('[data-expedition-kind="raid"]').click()
        expect(plain_page.locator("#mission-target")).to_have_value("c4")
        expect(plain_page.locator("#mission-kind")).to_have_value("raid")
        plain.close()
        page.locator(".book-footer > form:last-child button").click()
        expect(page.locator("#id_username")).to_be_visible()
        page.locator("#id_username").fill(username)
        page.locator("#id_password").fill(password)
        page.locator(".stack-form button").click()
        assert not errors, errors
        context.close()
    browser.close()
print(
    "Browser smoke passed in French and English: three destinations, public map, local batch forges, affordability, select-all/clear, city folios, draft/seal/cancel, raid/return, translated letters, privacy, compact mobile header, touch targets, logout/login."
)
