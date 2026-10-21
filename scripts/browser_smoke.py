"""Real bilingual browser journeys against a disposable local server/database."""

import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
artifacts = Path("artifacts")
artifacts.mkdir(exist_ok=True)


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "The page overflows horizontally"
    )
    readable_hierarchy(page)
    for scene in page.locator(".illustration").all():
        box = scene.bounding_box()
        assert abs(box["width"] / box["height"] - 1.5) < 0.02
    if page.locator(".book-title").count():
        scannable_layout(page)


def readable_hierarchy(page):
    sizes = page.locator("main").evaluate("""root => {
      const visible = selector => [...root.querySelectorAll(selector)]
        .filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
        .map(el => parseFloat(getComputedStyle(el).fontSize));
      return {headings: visible('h1, h2, h3, [role="heading"]'),
              body: visible('p, legend, .ledger-figures dt, .ledger-figures dd, .work-transition, .work-benefit, .work-reason'),
              disclosures: visible('summary')};
    }""")
    if sizes["headings"] and sizes["body"]:
        assert min(sizes["headings"]) > max(sizes["body"]), sizes
    if sizes["disclosures"] and sizes["body"]:
        assert min(sizes["disclosures"]) >= max(sizes["body"]), sizes


def city_heading_starts_panel(page):
    """A city jump starts with its heading below the sticky resource header."""
    heading = page.locator("#context-title")
    expect(heading).to_be_in_viewport()
    # Browser-side timers do not run in the JavaScript-disabled journey.
    for _ in range(100):
        aligned = page.evaluate("""() => {
      const header = document.querySelector('.reign-header').getBoundingClientRect();
      const heading = document.querySelector('#context-title').getBoundingClientRect();
      const map = document.querySelector('.realm-map').getBoundingClientRect();
      const gap = heading.top - header.bottom;
      return gap >= 0 && gap <= 20 && map.bottom <= header.bottom;
    }""")
        if aligned:
            return
        page.wait_for_timeout(100)
    raise AssertionError("The city heading must be the first content below the header")


def scannable_layout(page):
    """The title remains readable and secondary actions stay below the folio."""
    title = page.locator(".book-title")
    assert title.evaluate("el => el.scrollWidth <= el.clientWidth")
    assert title.evaluate("el => getComputedStyle(el).whiteSpace") == "normal"
    expect(page.locator('.resource-ribbon [data-icon="moon"]')).to_have_count(1)
    expect(page.locator(".resource-ribbon .resource-value")).to_have_count(3)
    assert page.locator('.reign-header a[href*="tab="]').count() == 0
    tab = page.evaluate("new URL(location.href).searchParams.get('tab') || 'domain'")
    expected = tab if tab in ("domain", "wars", "constructions") else None
    active = page.locator('.bookmarks a[aria-current="page"]')
    expect(active).to_have_count(1 if expected else 0)
    if expected:
        expect(active).to_have_attribute("data-section", expected)
    for selector in (".council-links a", ".guide-index a"):
        links = page.locator(selector).all()
        for first, second in zip(links, links[1:]):
            a, b = first.bounding_box(), second.bounding_box()
            assert abs(a["x"] - b["x"]) < 1
            assert b["y"] >= a["y"] + a["height"]
    for note in page.locator(".notice, .marginal-note, .unsealed-leaf").all():
        assert note.evaluate("el => getComputedStyle(el).borderLeftWidth") == "0px"
        assert note.evaluate("el => getComputedStyle(el).boxShadow") != "none"


def illustration_asset(scene, filename):
    """Check the actual displayed local asset, including successful image decoding."""
    assert scene.evaluate(
        r"""async (el, filename) => {
          const background = getComputedStyle(el).backgroundImage;
          const url = background.match(/url\(["']?(.*?)["']?\)/)[1];
          const image = new Image();
          image.src = url;
          await image.decode();
          return new URL(url).pathname.endsWith('/' + filename)
            && image.naturalWidth > 0 && image.naturalHeight > 0;
        }""",
        filename,
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
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
        page.set_viewport_size({"width": 1440, "height": 1100})
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
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
        page.goto(base_url + "/games/new/")
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.locator("#id_title").fill("The Amber Chronicles" if en else "Les chroniques d’Ambre")
        page.locator("#id_opponents").select_option("passive")
        page.locator(".game-setup button").click()
        expect(
            page.get_by_role("heading", name="First steps" if en else "Premiers pas")
        ).to_be_visible()
        game_url = page.url.split("?")[0]
        for leaf in range(1, 5):
            expect(page.locator("[data-prologue-page]")).to_have_attribute(
                "data-prologue-page", str(leaf)
            )
            for width in (320, 390):
                page.set_viewport_size({"width": width, "height": 844})
                no_overflow(page)
                page.evaluate("document.documentElement.style.fontSize = '125%'")
                no_overflow(page)
                page.evaluate("document.documentElement.style.removeProperty('font-size')")
            if leaf == 2:
                for selected_language in ("fr" if en else "en", language):
                    page.locator("#language").select_option(selected_language)
                    page.locator(".language-switch button").click()
                    expect(page.locator("[data-prologue-page]")).to_have_attribute(
                        "data-prologue-page", "2"
                    )
            if leaf < 4:
                page.locator("[data-prologue-next]").focus()
                page.keyboard.press("Enter")
            else:
                page.screenshot(path=str(artifacts / f"prologue-{language}.png"), full_page=True)
                page.locator("[data-prologue-enter]").click()
        page.set_viewport_size({"width": 1440, "height": 1100})
        expect(
            page.get_by_role(
                "heading", name="Your house council" if en else "Le conseil de votre maison"
            )
        ).to_be_visible()
        expect(page.locator("#recent-letters")).to_be_visible()
        expect(page.locator("#upcoming-heading")).to_be_visible()
        links = page.locator(".council-links a").all()
        for first, second in zip(links, links[1:]):
            a, b = first.bounding_box(), second.bounding_box()
            assert b["x"] >= a["x"] + a["width"] + 10 or b["y"] >= a["y"] + a["height"]
        expect(page.locator(".ledger-summary dt")).to_have_count(3)
        assert page.locator(".house-accounts").count() == 0
        assert page.locator(".bookmarks a").count() == 3
        page.locator('.bookmarks a[href$="?tab=constructions"]').click()
        expect(
            page.get_by_role("heading", name="Works" if en else "Chantiers", exact=True)
        ).to_be_visible()
        assert page.locator("#works-heading").count() == 0
        expect(page.locator("#work-storage")).to_contain_text(
            "Additional granaries" if en else "Greniers supplémentaires"
        )
        expect(page.locator("#work-forge")).to_contain_text(
            "Small arsenal" if en else "Petit arsenal"
        )
        assert "Level " not in page.locator(".work-choices").inner_text()
        assert "Niveau " not in page.locator(".work-choices").inner_text()
        # A specific work has a native return path to the complete Works list.
        for family, filename in (
            ("irrigation", "yaara-atlas.png"),
            ("storage", "granary.jpg"),
            ("forge", "forge.jpg"),
            ("walls", "fortifications.jpg"),
            ("watch", "yaara-atlas.png"),
            ("shelter", "yaara-atlas.png"),
            ("transport", "yaara-atlas.png"),
            ("siege", "yaara-atlas.png"),
        ):
            page.goto(game_url + "?tab=constructions&action=" + family)
            illustration_asset(page.locator(".illustration"), filename)
            no_overflow(page)
        page.locator("[data-works-return]").focus()
        page.keyboard.press("Enter")
        expect(page.locator(".work-choices")).to_be_visible()
        readable_hierarchy(page)
        page.evaluate("document.documentElement.style.fontSize = '125%'")
        readable_hierarchy(page)
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.screenshot(path=str(artifacts / f"works-named-{language}.png"), full_page=True)
        page.goto(game_url)
        illustration_asset(page.locator(".illustration-council"), "council.jpg")
        assert page.locator(".city-entry").count() == 3
        for number in range(1, 4):
            thumbnail = page.locator(f"#city-c{number} .illustration-small")
            illustration_asset(thumbnail, "cityscapes.png")
            expect(thumbnail).to_have_attribute("aria-hidden", "true")
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        assert page.locator(".sidebar, .stats-strip, img, table").count() == 0
        assert page.locator(".city-entry details").count() == 0
        expect(page.locator("body")).to_have_css("background-color", "rgb(253, 251, 247)")
        expect(page.locator(".dateline")).to_have_count(0)
        expect(page.locator(".resource-ribbon")).to_contain_text("1")
        page.screenshot(path=str(artifacts / f"domain-desktop-{language}.png"), full_page=True)
        cityscapes = set()
        for number in range(1, 10):
            page.goto(game_url + f"?tab=city&city=c{number}")
            scene = page.locator(".illustration-city")
            expect(scene).to_have_class(
                f"illustration illustration-city illustration-city-c{number}"
            )
            illustration_asset(scene, "cityscapes.png")
            cityscapes.add(scene.evaluate("el => getComputedStyle(el).backgroundPosition"))
            no_overflow(page)
            page.screenshot(
                path=str(artifacts / f"city-c{number}-desktop-{language}.png"), full_page=True
            )
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                no_overflow(page)
                page.evaluate("document.documentElement.style.fontSize = '125%'")
                no_overflow(page)
                page.evaluate("document.documentElement.style.removeProperty('font-size')")
            page.set_viewport_size({"width": 1440, "height": 1100})
        assert len(cityscapes) == 9
        page.locator('.bookmarks a[href$="?tab=constructions"]').click()
        # Local forges keep the same atomic multi-city draft/seal/cancel workflow.
        page.goto(game_url + "?tab=constructions&action=forge")
        forge = page.locator("#work-forge")
        forge.locator('input[value="c1"]').check()
        forge.locator('input[value="c2"]').check()
        expect(forge.locator("[data-work-cost]")).to_have_text("300,000" if en else "300\u202f000")
        forge.locator('button[type="submit"]').click()
        expect(page.locator(".decree-reading")).to_contain_text("+10%" if en else "+10 %")
        expect(page.locator('.bookmarks a[aria-current="page"]')).to_have_count(0)
        page.locator(".wax-seal").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "1,500,000" if en else "1\u00a0500\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "1,800,000" if en else "1\u00a0800\u00a0000"
        )
        page.goto(game_url + "?tab=constructions&action=irrigation")
        canals = page.locator("#work-irrigation")
        canals.locator('input[value="c1"]').check()
        expect(canals.locator("[data-budget-note]")).to_have_text(
            "After reservation: 1,500,000 Measures available."
            if en
            else "Après réservation : 1\u202f500\u202f000 Mesures libres."
        )
        page.goto(game_url + "?tab=constructions&action=storage")
        work = page.locator("#work-storage")
        work.locator("[data-select-cities]").click()
        expect(work.locator("[data-city-count]")).to_have_text("3")
        expect(work.locator("[data-work-cost]")).to_have_text("600,000" if en else "600\u202f000")
        work.locator("[data-clear-cities]").click()
        expect(work.locator("[data-city-count]")).to_have_text("0")
        work.locator('input[value="c1"]').check()
        work.locator('input[value="c2"]').check()
        expect(work.locator("[data-city-count]")).to_have_text("2")
        expect(work.locator("[data-work-cost]")).to_have_text("400,000" if en else "400\u202f000")
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
            "1,400,000" if en else "1\u00a0400\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".orders-register")).to_have_count(0)
        page.locator('.bookmarks a[data-section="wars"]').click()
        assert page.locator(".map-city").count() == 9
        assert page.locator(".map-territory").count() == 9
        assert page.locator('[data-map-state="owned"]').count() == 3
        assert page.locator('[data-map-state="reachable"]').count() == 2
        assert page.locator('[data-map-state="unreachable"]').count() == 4
        expect(page.locator('.map-city[href*="city=c6"]')).to_have_attribute(
            "aria-label", re.compile("Out of reach" if en else "Hors de portée")
        )
        assert page.locator(".map-road").count() == 0
        expect(page.locator(".illustration")).to_have_count(0)
        page.locator('.map-city[href*="city=c4"]').focus()
        page.keyboard.press("Enter")
        assert page.locator("[data-local-accounts]").count() == 0
        expect(page.locator("#map-context")).to_contain_text("Sefra")
        city_heading_starts_panel(page)
        illustration_asset(page.locator("#map-context > .illustration"), "army-preparation.jpg")
        page.screenshot(path=str(artifacts / f"map-context-desktop-{language}.png"), full_page=True)
        page.locator('input[name="kind"][value="capture"]').check()
        expect(page.locator('input[name="kind"][value="capture"]')).to_be_checked()
        expect(page.locator("#map-context > .illustration")).to_have_class(
            "illustration illustration-army"
        )
        illustration_asset(page.locator("#map-context > .illustration"), "army-preparation.jpg")
        atlas = page.locator(".realm-map").bounding_box()
        panel = page.locator("#map-context").bounding_box()
        assert panel["y"] >= atlas["y"] + atlas["height"]
        assert panel["width"] >= atlas["width"] - 1
        expect(page.locator("#mission-target")).to_have_value("c4")
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("30")
        expect(page.locator("[data-expedition-budget]")).to_contain_text(
            "short" if en else "Il manque"
        )
        page.locator(".expedition-form button").click()
        expect(page.locator('input[name="kind"][value="capture"]')).to_be_checked()
        expect(page.locator("#mission-target")).to_have_value("c4")
        expect(page.locator('input[name="men_c1"]')).to_have_value("30")
        assert "tab=wars" in page.url and "action=expedition" in page.url
        page.locator('input[name="kind"][value="raid"]').check()
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("10")
        expect(page.locator("#army-cost")).to_have_text("95,000" if en else "95\u202f000")
        for origin, amount in (
            ("c1", "31,667" if en else "31\u202f667"),
            ("c2", "31,667" if en else "31\u202f667"),
            ("c3", "31,666" if en else "31\u202f666"),
        ):
            expect(page.locator(f'[data-origin="{origin}"] .origin-funding')).to_contain_text(
                amount
            )
        page.locator('input[name="men_c1"]').fill("0")
        page.locator('input[name="men_c2"]').fill("0")
        page.locator('input[name="men_c3"]').fill("45")
        expect(page.locator("#army-cost")).to_contain_text("132,500" if en else "132\u202f500")
        page.locator(".expedition-form button").click()
        expect(
            page.get_by_role("heading", name="The people committed" if en else "Les hommes engagés")
        ).to_be_visible()
        page.locator(".wax-seal").click()
        assert page.locator('[data-map-state="engaged"]').count() == 1
        page.screenshot(path=str(artifacts / f"decrees-desktop-{language}.png"), full_page=True)
        for moon in range(1, 4):
            page.locator('.bookmarks a[data-section="domain"]').click()
            page.locator("#turn-page button.primary-action").click()
            expect(page.locator(".resource-ribbon")).to_contain_text(str(moon + 1))
        page.locator('.bookmarks a[href$="?tab=wars"]').click()
        expect(
            page.get_by_role("heading", name="Expeditions" if en else "Expéditions", exact=True)
        ).to_be_visible()
        page.locator('.bookmarks a[data-section="domain"]').click()
        page.locator('a[href="?tab=letters"]').click()
        assert (
            page.locator('.letter-entry a[href="?tab=domain"]').count()
            == page.locator(".letter-entry").count()
        )
        for title in (
            ("Return to Namar", "Successful raid at Sefra")
            if en
            else ("Retour à Namar", "Pillage réussi à Sefra")
        ):
            expect(
                page.locator(".correspondence").get_by_role("heading", name=title)
            ).to_be_visible()
        expect(page.locator(".correspondence")).to_contain_text(
            "Paid cost of this raid: 132,500 Measures"
            if en
            else "Coût payé pour ce raid : 132\u202f500 Mesures"
        )
        expect(page.locator(".correspondence")).to_contain_text(
            "Namar: 132,500 Measures paid" if en else "Namar : 132\u202f500 Mesures payées"
        )
        expect(page.locator(".correspondence")).to_contain_text(
            "Final Measures balance:" if en else "Solde final des Mesures :"
        )
        expect(page.locator(".correspondence")).to_contain_text(
            "Our survivors say they encountered between"
            if en
            else "Nos survivants disent avoir rencontré entre"
        )
        illustration_asset(
            page.locator(".illustration-offensive-raid-success"), "offensive-raid-success.jpg"
        )
        expect(page.locator(".letter-entry > .illustration")).to_have_count(0)
        for letter in page.locator(".letter-entry").all():
            expect(letter.locator(".letter-heading .illustration-small")).to_have_count(1)
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
        page.screenshot(
            path=str(artifacts / f"letters-thumbnails-mobile-{language}.png"), full_page=True
        )
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        # HTTP cases cover every recipient/outcome; decode all eight CSS assets here.
        for direction in ("offensive", "received"):
            for kind in ("raid", "capture"):
                for outcome in ("success", "failure"):
                    scene_name = f"{direction}-{kind}-{outcome}"
                    page.locator("main").evaluate(
                        """(root, scene) => {
                          const el = document.createElement('div');
                          el.id = 'combat-artwork-check';
                          el.className = 'illustration illustration-' + scene;
                          el.setAttribute('aria-hidden', 'true');
                          root.append(el);
                        }""",
                        scene_name,
                    )
                    scene = page.locator("#combat-artwork-check")
                    illustration_asset(scene, scene_name + ".jpg")
                    assert (
                        scene.evaluate("el => getComputedStyle(el).backgroundSize") == "100% 100%"
                    )
                    box = scene.bounding_box()
                    assert abs(box["width"] / box["height"] - 1.5) < 0.02
                    scene.evaluate("el => el.remove()")
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
        page.locator("#work-storage").click()
        expect(page.locator('#work-storage input[value="c2"]')).to_be_checked()
        expect(page.locator('#work-storage input[value="c1"]')).not_to_be_checked()
        page.goto(game_url + "?tab=city&city=c4")
        assert page.locator("[data-local-accounts]").count() == 0
        # Complete one granary, then reserve another city's teams for a forge.
        # Storage now mixes completed infrastructure, ordinary granaries and busy teams.
        page.goto(game_url + "?tab=constructions")
        page.goto(game_url + "?tab=constructions&action=storage")
        storage = page.locator("#work-storage")
        storage.locator('input[value="c1"]').check()
        storage.locator('button[type="submit"]').click()
        page.locator(".wax-seal").click()
        for _ in range(5):
            page.locator('.bookmarks a[data-section="domain"]').click()
            page.locator("#turn-page button.primary-action").click()
        page.goto(game_url + "?tab=constructions")
        page.goto(game_url + "?tab=constructions&action=forge")
        forge = page.locator("#work-forge")
        forge.locator('input[value="c2"]').check()
        forge.locator('button[type="submit"]').click()
        page.locator(".wax-seal").click()
        page.goto(game_url + "?tab=constructions&action=storage")
        storage = page.locator("#work-storage")
        expect(storage.locator('input[value="c2"]')).to_be_disabled()
        expect(storage.locator('input[value="c1"]')).to_be_enabled()
        expect(storage.locator(".work-transition").first).to_have_text(
            "Additional granaries → Silo complex"
            if en
            else "Greniers supplémentaires → Ensemble de silos"
        )
        expect(storage.locator(".work-benefit").first).to_contain_text(
            "3,600,000 → 5,400,000" if en else "3\u202f600\u202f000 → 5\u202f400\u202f000"
        )
        assert storage.locator(".work-advice").count() == 0
        readable_hierarchy(page)
        page.screenshot(path=str(artifacts / f"works-mixed-desktop-{language}.png"), full_page=True)
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            for suffix in (
                "",
                "?tab=city&city=c2",
                "?tab=letters",
                "?tab=help",
                "?tab=prologue&page=3",
                "?tab=constructions",
                "?tab=wars",
                "?tab=decrees&action=expedition",
            ):
                page.goto(game_url + suffix)
                no_overflow(page)
                page.evaluate("document.documentElement.style.fontSize = '125%'")
                no_overflow(page)
                page.evaluate("document.documentElement.style.removeProperty('font-size')")
                assert page.locator(".reign-header").bounding_box()["height"] < 130
                assert (
                    page.locator("body").evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
                    == 16
                )
                if suffix == "?tab=constructions":
                    page.locator("#work-storage").click()
                    storage = page.locator("#work-storage")
                    for facts in storage.locator(".work-facts").all():
                        expect(facts.locator("dt")).to_have_count(3)
                    for choice in storage.locator(".city-choice").all():
                        assert choice.bounding_box()["height"] >= 44
                        assert (
                            choice.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") <= 16
                        )
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
        plain_page.goto(game_url + "?tab=help")
        expect(plain_page.locator("#victory")).to_be_visible()
        no_overflow(plain_page)
        plain_page.locator("[data-prologue-replay]").click()
        plain_page.locator("[data-prologue-next]").click()
        expect(plain_page.locator("[data-prologue-page]")).to_have_attribute(
            "data-prologue-page", "2"
        )
        plain_page.locator("[data-prologue-previous]").click()
        plain_page.locator("[data-prologue-skip]").click()
        illustration_asset(plain_page.locator("#city-c1 .illustration-small"), "cityscapes.png")
        plain_page.locator('.city-entry a[href*="city=c1"]').click()
        expect(plain_page.locator("[data-local-accounts]")).to_be_visible()
        expect(plain_page.locator(".illustration-city-c1")).to_be_visible()
        illustration_asset(plain_page.locator(".illustration-city-c1"), "cityscapes.png")
        no_overflow(plain_page)
        plain_page.goto(game_url + "?tab=constructions")
        plain_page.locator("#work-storage").click()
        plain_forge = plain_page.locator("#work-storage")
        plain_forge.locator('input[value="c1"]').check()
        plain_forge.locator('button[type="submit"]').click()
        expect(plain_page.locator(".notices")).to_contain_text(
            "The granary in Qasr needs" if en else "Le grenier de Qasr manque"
        )
        plain_page.goto(game_url + "?tab=constructions")
        plain_page.locator("#work-storage").click()
        plain_storage = plain_page.locator("#work-storage")
        plain_storage.locator('input[value="c3"]').check()
        plain_storage.locator('button[type="submit"]').click()
        expect(plain_page.locator(".unsealed-leaf")).to_be_visible()
        plain_page.goto(game_url + "?tab=wars")
        plain_page.locator('.map-city[href*="city=c4"]').click()
        expect(plain_page.locator("#map-context")).to_contain_text("Sefra")
        city_heading_starts_panel(plain_page)
        expect(plain_page.locator("#map-context > .illustration")).to_have_class(
            "illustration illustration-army"
        )
        no_overflow(plain_page)
        plain_page.screenshot(
            path=str(artifacts / f"map-context-mobile-{language}.png"), full_page=True
        )
        plain_page.locator('input[name="kind"][value="raid"]').check()
        expect(plain_page.locator("#mission-target")).to_have_value("c4")
        expect(plain_page.locator('input[name="kind"][value="raid"]')).to_be_checked()
        plain.close()
        # Spend exactly 600k per city on the first two arsenal tiers before harvest.
        page.goto(base_url + "/games/new/")
        page.locator("#id_title").fill("Empty granaries")
        page.locator("#id_opponents").select_option("passive")
        page.locator(".game-setup button").click()
        empty_url = page.url.split("?")[0]
        for tier in range(2):
            page.goto(empty_url + "?tab=constructions&action=forge")
            forge = page.locator("#work-forge")
            forge.locator("[data-select-cities]").click()
            forge.locator('button[type="submit"]').click()
            page.locator(".wax-seal").click()
            for _ in range(4 if tier == 0 else 1):
                page.goto(empty_url)
                page.locator("#turn-page button.primary-action").click()
        page.goto(empty_url + "?tab=wars&action=expedition&city=c4")
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("10")
        expect(page.locator("#army-cost")).to_have_text("95,000" if en else "95\u202f000")
        expect(page.locator("[data-expedition-budget]")).to_contain_text(
            "95,000" if en else "95\u202f000"
        )
        page.locator(".expedition-form button").click()
        expect(page.locator(".notices")).to_contain_text("Qasr")
        expect(page.locator('input[name="men_c1"]')).to_have_value("10")
        assert "action=expedition" in page.url
        empty = page.request.get(empty_url + "state/").json()["view"]
        assert empty["available_stock"] == 0 and empty["sealed_count"] == 0
        native = browser.new_context(
            storage_state=context.storage_state(),
            java_script_enabled=False,
            viewport={"width": 320, "height": 844},
        )
        native_page = native.new_page()
        native_page.goto(page.url)
        expect(native_page.locator("#army-total")).to_have_text("30")
        expect(native_page.locator("#army-cost")).to_have_text("95,000" if en else "95\u00a0000")
        assert native_page.locator(".origin-funding").count() == 3
        native_page.locator(".expedition-form button").click()
        expect(native_page.locator('input[name="men_c3"]')).to_have_value("10")
        no_overflow(native_page)
        native_page.screenshot(
            path=str(artifacts / f"empty-granaries-{language}.png"), full_page=True
        )
        native.close()
        # Automatic reigns wait through onboarding, then join wall-clock boundaries.
        page.goto(base_url + "/games/new/")
        page.locator("#id_title").fill("Automatic opening")
        page.locator("#id_opponents").select_option("passive")
        page.locator("#id_mode").select_option("scheduled")
        page.locator(".game-setup button").click()
        automatic_url = page.url.split("?")[0]
        assert page.locator("[data-deadline]").count() == 0
        waiting = page.request.get(automatic_url + "state/").json()
        assert waiting["game"]["awaiting_start"] and waiting["game"]["paused"]
        next_box = page.locator("[data-prologue-next]").bounding_box()
        start_box = page.locator('.prologue-leaf form[action$="/start/"] button').bounding_box()
        assert next_box["y"] + next_box["height"] <= start_box["y"]
        expect(page.locator(".calendar-cadence")).to_contain_text(":00, :10")
        page.locator('.prologue-leaf form[action$="/start/"] button').click()
        started = page.request.get(automatic_url + "state/").json()
        assert not started["game"]["awaiting_start"] and not started["game"]["paused"]
        assert started["game"]["deadline"] and started["view"]["open_moon"] == 1
        deadline = datetime.fromisoformat(started["game"]["deadline"])
        assert deadline.minute % 10 == 0 and deadline.second == deadline.microsecond == 0
        expect(page.locator(".moon-banner [data-deadline]")).to_be_visible()
        expect(page.locator('.moon-banner [data-icon="moon"]')).to_be_visible()
        expect(page.locator(".moon-banner time")).to_contain_text("UTC")
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
            page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.screenshot(path=str(artifacts / f"moon-banner-{language}.png"), full_page=True)
        native_clock = browser.new_context(
            storage_state=context.storage_state(),
            java_script_enabled=False,
            viewport={"width": 320, "height": 844},
        )
        native_clock_page = native_clock.new_page()
        native_clock_page.goto(automatic_url)
        expect(native_clock_page.locator(".moon-banner time")).to_contain_text("UTC")
        no_overflow(native_clock_page)
        native_clock.close()
        assert page.locator(".reign-header [data-deadline]").count() == 0
        page.reload()
        assert (
            page.request.get(automatic_url + "state/").json()["game"]["deadline"]
            == started["game"]["deadline"]
        )
        page.locator(".book-footer > form:last-child button").click()
        expect(page.locator("#id_username")).to_be_visible()
        page.locator("#id_username").fill(username)
        page.locator("#id_password").fill(password)
        page.locator(".stack-form button").click()
        assert not errors, errors
        context.close()
    browser.close()
print(
    "Browser smoke passed in French and English: prologue and explicit automatic start, rules reference, city accounts, two-target frontiers, local funding and shortfalls, batch works, no-JavaScript previews, draft/seal/cancel, raid/return, translated letters, privacy, compact mobile header, enlarged text, touch targets, logout/login."
)
