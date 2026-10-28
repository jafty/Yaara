"""Real bilingual browser journeys against a disposable local server/database."""

import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from map_browser_smoke import run_map_journeys
from playwright.sync_api import expect, sync_playwright

base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
artifacts = Path("artifacts")
artifacts.mkdir(exist_ok=True)


def no_overflow(page):
    page.evaluate("document.fonts.ready")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "The page overflows horizontally"
    )
    readable_hierarchy(page)
    for scene in page.locator(".illustration").all():
        box = scene.bounding_box()
        framed = scene.evaluate("el => getComputedStyle(el, '::before').content !== 'none'")
        source = scene.evaluate("el => getComputedStyle(el, '::before').backgroundImage")
        # Standalone originals keep their complete composition; atlas excerpts are wider.
        catalogue = scene.evaluate("el => Boolean(el.closest('.work-card'))")
        building = scene.evaluate("el => el.classList.contains('illustration-building')")
        building_detail = scene.evaluate(
            "el => el.classList.contains('illustration-building-detail')"
        )
        if building:
            ratio = 1
        elif building_detail or not framed or (".jpg" in source and not catalogue):
            ratio = 1.5
        else:
            ratio = 2
        assert abs(box["width"] / box["height"] - ratio) < 0.02
        if framed:
            # Never stretch a scene or expose adjacent atlas cells.
            geometry = scene.evaluate("""el => {
              const art = getComputedStyle(el, '::before');
              return {width: parseFloat(art.width), height: parseFloat(art.height),
                      overflow: getComputedStyle(el).overflow};
            }""")
            assert abs(geometry["width"] / geometry["height"] - 1.5) < 0.02
            assert geometry["overflow"] == "hidden"
    if page.locator(".house-identity").count() and not page.locator(".workspace-page").count():
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
    """A city jump opens beside the desktop map or beneath it on mobile."""
    heading = page.locator("#context-title")
    expect(heading).to_be_in_viewport()
    # Browser-side timers do not run in the JavaScript-disabled journey.
    for _ in range(100):
        aligned = page.evaluate("""() => {
      const header = document.querySelector('.reign-header').getBoundingClientRect();
      const heading = document.querySelector('#context-title').getBoundingClientRect();
      const map = document.querySelector('.realm-map').getBoundingClientRect();
      const gap = heading.top - header.bottom;
      const panel = document.querySelector('#map-context').getBoundingClientRect();
      const desktop = matchMedia('(min-width: 1100px) and (min-height: 600px)').matches;
      if (getComputedStyle(document.querySelector('#map-context')).position === 'absolute')
        return panel.top >= 0 && panel.bottom <= innerHeight + 1;
      return desktop
        ? gap >= 0 && panel.left >= map.right && map.top >= header.bottom
        : gap >= 0 && heading.bottom <= innerHeight
          && map.bottom <= heading.top;
    }""")
        if aligned:
            return
        page.wait_for_timeout(100)
    raise AssertionError("The city heading must be the first content below the header")


def section_jump_lands(page, selector):
    """Native alert destinations clear the sticky header and skip preceding content."""
    expect(page.locator(selector)).to_be_in_viewport()
    for _ in range(100):
        if page.locator(selector).evaluate("""el => {
          const top = el.getBoundingClientRect().top;
          const header = document.querySelector('.reign-header').getBoundingClientRect();
          const bottom = innerHeight;
          const line = parseFloat(getComputedStyle(el).lineHeight);
          // Native navigation may keep an already visible target in place.
          return location.hash === '#' + el.id
            && top >= header.bottom && top + line <= bottom;
        }"""):
            return
        page.wait_for_timeout(100)
    geometry = page.evaluate(
        """selector => ({
      width: innerWidth,
      targetId: selector,
      hash: location.hash,
      font: getComputedStyle(document.documentElement).fontSize,
      padding: getComputedStyle(document.documentElement).scrollPaddingTop,
      target: document.querySelector(selector).getBoundingClientRect().top,
      header: document.querySelector('.reign-header').getBoundingClientRect().bottom
    })""",
        selector,
    )
    page.screenshot(path=str(artifacts / "fragment-failure.png"))
    raise AssertionError(f"The alert destination must appear below the header: {geometry}")


def scannable_layout(page):
    """The title remains readable and secondary actions stay below the folio."""
    title = page.locator(".house-identity")
    assert title.evaluate("el => el.scrollWidth <= el.clientWidth")
    assert title.evaluate("el => getComputedStyle(el).whiteSpace") == "normal"
    expect(page.locator('.resource-ribbon [data-icon="moon"]')).to_have_count(1)
    expect(page.locator(".resource-ribbon .resource-value")).to_have_count(3)
    expect(page.locator('.reign-header a[href$="?tab=mail"]')).to_have_count(1)
    expected = page.evaluate("""() => {
      const tab = new URL(location.href).searchParams.get('tab') || 'map';
      if (document.querySelector('.decree-reading')) return 'map';
      if (location.pathname.endsWith('/archive/')) return 'domain';
      if (tab === 'mail' || tab === 'letters') return 'mail';
      return tab === 'map' ? 'map' : 'domain';
    }""")
    active = page.locator('.reign-header a[data-section][aria-current="page"]')
    expect(active).to_have_count(1)
    expect(active).to_have_attribute("data-section", expected)
    for selector in (
        ".notice",
        ".marginal-note",
    ):
        for element in page.locator(selector).all():
            assert element.evaluate("el => parseFloat(getComputedStyle(el).borderLeftWidth)") == 0
    expect(
        page.locator(".chapter-heading .illustration, .map-heading .illustration")
    ).to_have_count(0)
    for scene in page.locator(".letter-entry > .illustration").all():
        assert scene.evaluate("""el => Math.abs(el.getBoundingClientRect().width
          - el.parentElement.getBoundingClientRect().width) < 2""")
    for selector in (".guide-index a",):
        # Measure adjacent links together: a native smooth jump can move the page
        # between separate browser calls, especially without JavaScript enabled.
        links = page.locator(selector).evaluate_all(
            "elements => elements.map(el => el.getBoundingClientRect().toJSON())"
        )
        for first, second in zip(links, links[1:]):
            assert abs(first["x"] - second["x"]) < 1
            assert second["y"] >= first["y"] + first["height"]
    for note in page.locator(".notice, .marginal-note").all():
        contrast = note.evaluate("""el => {
          const style = getComputedStyle(el);
          function luminance(colour) {
            const channels = colour.match(/[\\d.]+/g).slice(0, 3).map(Number).map(value => {
              const channel = value / 255;
              return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
            });
            return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
          }
          const text = luminance(style.color), surface = luminance(style.backgroundColor);
          return (Math.max(text, surface) + .05) / (Math.min(text, surface) + .05);
        }""")
        assert contrast >= 4.5, contrast


def redesign_reflow(page):
    """The reading and decision layouts remain usable with enlarged text."""
    viewport = page.viewport_size
    for width in (320, 390, 1440):
        page.set_viewport_size({"width": width, "height": 844})
        for scale in ("100%", "125%", "200%"):
            page.evaluate("scale => document.documentElement.style.fontSize = scale", scale)
            no_overflow(page)
            if (
                width == 390
                and scale == "100%"
                and page.evaluate("new URL(location.href).searchParams.get('tab') || 'domain'")
                == "domain"
                and page.locator('.alerts-trigger[data-alert-count="0"]').count()
                and page.locator(".letter-entry").count()
            ):
                page.locator(".letter-entry h3").first.scroll_into_view_if_needed()
                # The permanent decision pane scrolls independently of the map.
                heading = page.locator(".letter-entry h3").first.bounding_box()
                assert heading["y"] + heading["height"] <= page.viewport_size["height"]
            # Covered navigation is inert; otherwise labels appear on keyboard focus.
            if page.locator(".reign-header").evaluate("el => el.inert"):
                expect(page.locator(".context-sheet")).to_have_css("position", "absolute")
            else:
                for resource in page.locator(".resource-value").all():
                    resource.focus()
                    expect(resource.locator(".resource-caption")).to_have_css("clip-path", "none")
                page.locator(".book-world").focus()
    page.evaluate("document.documentElement.style.removeProperty('font-size')")
    page.set_viewport_size(viewport)


def illustration_asset(scene, filename):
    """Check the actual displayed local asset, including successful image decoding."""
    assert scene.evaluate(
        r"""async (el, filename) => {
          const art = getComputedStyle(el, '::before');
          const background = art.content !== 'none' ? art.backgroundImage : getComputedStyle(el).backgroundImage;
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
        page.goto(game_url + "?tab=domain")
        expect(page.get_by_role("heading", name="Reign" if en else "Règne")).to_be_visible()
        expect(page.locator("#turn-page")).to_be_visible()
        redesign_reflow(page)
        expect(page.locator(".alerts-trigger")).to_have_attribute("data-alert-count", "0")
        assert page.locator("#city-ledgers").count() == 0
        links = page.locator(".council-links a").all()
        for first, second in zip(links, links[1:]):
            a, b = first.bounding_box(), second.bounding_box()
            assert b["x"] >= a["x"] + a["width"] + 10 or b["y"] >= a["y"] + a["height"]
        assert page.locator(".house-accounts").count() == 0
        assert page.locator(".reign-header a[data-section]").count() == 3
        news = page.locator(".reign-header .alerts-trigger")
        expect(news).to_have_css("border-top-width", "0px")
        expect(news.locator("strong")).to_have_css("border-top-width", "0px")
        expect(news.locator(".visually-hidden")).to_contain_text("News" if en else "Nouvelles")
        expect(news.locator(".visually-hidden")).to_contain_text("Alerts" if en else "Alertes")
        # City actions open a full sheet and retain local resources at every size.
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            for action in ("works", "convoy"):
                page.goto(game_url + "?tab=map&city=c1")
                expect(page.locator(".city-actions")).to_be_visible()
                expect(page.locator('.city-actions a[href*="action=accounts"]')).to_have_count(0)
                expect(page.locator(".map-neighbors, .city-activities")).to_have_count(0)
                expect(page.locator("#city-works")).to_have_count(0)
                assert page.locator(".city-action").first.evaluate(
                    "el => getComputedStyle(el).display === 'flex' && el.getBoundingClientRect().height >= 44"
                )
                first, second = [
                    action.bounding_box() for action in page.locator(".city-action").all()
                ]
                assert (
                    abs(first["x"] - second["x"]) < 1
                    and second["y"] >= first["y"] + first["height"]
                )
                assert page.locator(".city-action small").count() == 2
                assert page.locator(".city-resources").evaluate(
                    "el => getComputedStyle(el).whiteSpace === 'nowrap' && el.getBoundingClientRect().width <= innerWidth"
                )
                page.locator(f'.city-actions a[href*="action={action}"]').click()
                expect(page.locator(".city-sheet[data-focus-action]")).to_be_visible()
                expect(page.locator(".city-resources")).to_be_visible()
                expect(page.locator(".reign-header")).to_be_hidden()
                expect(page.locator(".city-activities")).to_have_count(0)
                expect(page.locator(".sheet-body")).to_have_css("opacity", "1")
                no_overflow(page)
                page.locator(".panel-close").click()
                expect(page.locator(".city-actions")).to_be_visible()
                expect(page.locator(".reign-header")).to_be_visible()
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.goto(game_url + "?tab=constructions")
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
        expect(page.locator(".work-card > .illustration")).to_have_count(
            page.locator(".work-card").count()
        )
        redesign_reflow(page)
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
        redesign_reflow(page)
        page.locator("[data-works-return]").focus()
        page.keyboard.press("Enter")
        expect(page.locator(".work-choices")).to_be_visible()
        readable_hierarchy(page)
        page.evaluate("document.documentElement.style.fontSize = '125%'")
        readable_hierarchy(page)
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.screenshot(path=str(artifacts / f"works-named-{language}.png"), full_page=True)
        page.goto(game_url + "?tab=domain")
        expect(page.locator(".chapter-heading .illustration")).to_have_count(0)
        assert page.locator("body").evaluate("el => getComputedStyle(el).backgroundImage") == "none"
        assert (
            page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor")
            == "rgb(253, 252, 249)"
        )
        assert (
            page.locator(".first-decisions").evaluate("el => getComputedStyle(el).backgroundImage")
            == "none"
        )
        assert page.evaluate("document.fonts.check('16px Alegreya')")
        assert page.locator("#city-ledgers").count() == 0
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        assert page.locator(".sidebar, .stats-strip, img, table").count() == 0
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            for anchor in ("city-defenses", "city-stocks"):
                page.goto(game_url + "?tab=city&city=c3#" + anchor)
                section_jump_lands(page, "#" + anchor)
                page.evaluate("document.documentElement.style.fontSize = '125%'")
                page.locator("#" + anchor).evaluate("el => el.scrollIntoView()")
                section_jump_lands(page, "#" + anchor)
                no_overflow(page)
                page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.goto(game_url + "?tab=domain")
        assert page.locator(".city-entry details").count() == 0
        expect(page.locator("body")).to_have_css("background-color", "rgb(253, 252, 249)")
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
            cityscapes.add(
                scene.evaluate("el => getComputedStyle(el, '::before').backgroundPosition")
            )
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
        page.goto(game_url + "?tab=constructions")
        # Local forges keep the same atomic multi-city draft/seal/cancel workflow.
        page.goto(game_url + "?tab=constructions&action=forge")
        forge = page.locator("#work-forge")
        forge.locator('input[value="c1"]').check()
        forge.locator('input[value="c2"]').check()
        expect(forge.locator("[data-work-cost]")).to_have_text("300,000" if en else "300\u202f000")
        forge.locator('button[type="submit"]').click()
        expect(page.locator(".decree-reading")).to_contain_text(
            "Small arsenal equipment" if en else "Équipement du petit arsenal"
        )
        expect(
            page.locator('.reign-header a[data-section][aria-current="page"]')
        ).to_have_attribute("data-section", "map")
        page.locator(".decree-reading > form button[type=submit]").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "2,400,000" if en else "2\u00a0400\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "2,700,000" if en else "2\u00a0700\u00a0000"
        )
        page.goto(game_url + "?tab=constructions&action=irrigation")
        canals = page.locator("#work-irrigation")
        canals.locator('input[value="c1"]').check()
        expect(canals.locator("[data-budget-note]")).to_have_text(
            "After reservation: 2,400,000 Measures available."
            if en
            else "Après réservation : 2\u202f400\u202f000 Mesures libres."
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
        expect(page.locator("#context-title")).to_have_text(
            "Review your order" if en else "Vérifier votre ordre"
        )
        # The panel language action reopens the same signed, read-only draft.
        for selected_language in ("fr" if en else "en", language):
            page.locator(".review-language summary").click()
            page.locator("#language").select_option(selected_language)
            page.locator(".language-switch button").click()
            expect(page.locator("#context-title")).to_have_text(
                "Review your order" if selected_language == "en" else "Vérifier votre ordre"
            )
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "2,700,000" if en else "2\u00a0700\u00a0000"
        )
        page.screenshot(
            path=str(artifacts / f"decree-letter-desktop-{language}.png"), full_page=True
        )
        page.locator(".decree-reading > form button[type=submit]").click()
        expect(page.locator(".orders-register")).to_contain_text("Confirmed" if en else "Confirmé")
        expect(page.locator(".resource-ribbon")).to_contain_text(
            "2,300,000" if en else "2\u00a0300\u00a0000"
        )
        page.locator(".orders-register button").click()
        expect(page.locator(".orders-register")).to_have_count(0)
        page.goto(game_url + "?tab=wars")
        assert page.locator(".map-city").count() == 9
        illustration_asset(page.locator(".map-frame"), "map/parchment.webp")
        assert page.locator(".map-territory").count() == 9
        assert page.locator('[data-map-state="owned"]').count() == 3
        assert page.locator('[data-map-state="reachable"]').count() == 2
        assert page.locator('[data-map-state="unreachable"]').count() == 4
        expect(page.locator('.map-city[href*="city=c6"]')).to_have_attribute(
            "aria-label", re.compile("Out of reach" if en else "Hors de portée")
        )
        assert page.locator(".map-road").count() == 0
        expect(page.locator(".illustration")).to_have_count(0)
        page.goto(game_url + "?tab=map")
        expect(page.locator(".map-guide-key")).to_be_visible()
        expect(page.locator(".map-reference")).to_have_count(0)
        page.goto(game_url + "?tab=wars")
        page.locator('.map-city[href*="city=c4"]').focus()
        page.keyboard.press("Enter")
        assert page.locator("[data-local-accounts]").count() == 0
        expect(page.locator("#map-context")).to_contain_text("Sefra")
        city_heading_starts_panel(page)
        expect(page.locator("#map-context .illustration")).to_have_count(0)
        page.screenshot(path=str(artifacts / f"map-context-desktop-{language}.png"), full_page=True)
        page.locator('input[name="kind"][value="capture"]').check()
        expect(page.locator('input[name="kind"][value="capture"]')).to_be_checked()
        expect(page.locator("#map-context .illustration")).to_have_count(0)
        expect(page.locator("#map-context .illustration")).to_have_count(0)
        redesign_reflow(page)
        page.goto(page.url)
        city_heading_starts_panel(page)
        atlas = page.locator(".realm-map").bounding_box()
        panel = page.locator("#map-context").bounding_box()
        assert panel["x"] >= atlas["x"] + atlas["width"]
        assert atlas["y"] >= page.locator(".reign-header").bounding_box()["height"]
        expect(page.locator(".origin-details[open]")).to_have_count(0)
        origin_note = page.locator(".origin-details").first
        origin_note.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(origin_note.locator("[data-origin-means]")).to_be_visible()
        page.keyboard.press("Enter")
        expect(origin_note).not_to_have_attribute("open", "")
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
            for item in page.locator(".map-legend li").all():
                assert item.evaluate("el => getComputedStyle(el).fontStyle") == "normal"
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
            page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        expect(page.locator("#mission-target")).to_have_value("c4")
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("20")
        page.locator('.primary-action[form="expedition-form"]').click()
        expect(page.locator('input[name="kind"][value="capture"]')).to_be_checked()
        expect(page.locator("#mission-target")).to_have_value("c4")
        expect(page.locator('input[name="men_c1"]')).to_have_value("20")
        assert "tab=map" in page.url and "action=expedition" in page.url
        page.locator(".expedition-notes > summary").focus()
        page.keyboard.press("Enter")
        help_note = page.locator(".ledger-help").first
        help_note.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(help_note).to_have_attribute("open", "")
        page.keyboard.press("Enter")
        expect(help_note).not_to_have_attribute("open", "")
        page.locator('input[name="kind"][value="raid"]').check()
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("10")
        expect(page.locator("#army-cost")).to_have_text("35,000" if en else "35\u202f000")
        for origin, amount in (
            ("c1", "11,667" if en else "11\u202f667"),
            ("c2", "11,667" if en else "11\u202f667"),
            ("c3", "11,666" if en else "11\u202f666"),
        ):
            expect(page.locator(f'[data-origin="{origin}"] .origin-funding')).to_contain_text(
                amount
            )
        expect(page.locator("[data-carry-limit]")).to_have_text("150,000" if en else "150\u202f000")
        expect(page.locator("[data-loot-preview]")).to_be_visible()
        page.locator('input[name="kind"][value="capture"]').check()
        expect(page.locator("[data-loot-preview]")).to_be_hidden()
        page.locator('input[name="kind"][value="raid"]').check()
        page.locator('input[name="men_c1"]').fill("0")
        page.locator('input[name="men_c2"]').fill("0")
        page.locator('input[name="men_c3"]').fill("60")
        expect(page.locator("#army-cost")).to_contain_text("65,000" if en else "65\u202f000")
        page.locator('.primary-action[form="expedition-form"]').click()
        expect(
            page.get_by_role("heading", name="The people committed" if en else "Les hommes engagés")
        ).to_be_visible()
        page.locator(".decree-reading > form button[type=submit]").click()
        assert page.locator('[data-map-state="engaged"]').count() == 0
        page.screenshot(path=str(artifacts / f"decrees-desktop-{language}.png"), full_page=True)
        for moon in range(1, 4):
            if not page.locator(".reign-header").is_visible():
                page.locator(".panel-close").click()
            page.locator('.reign-header a[data-section="domain"]').click()
            page.locator("#turn-page button.primary-action").click()
            page.goto(page.url.split("?")[0] + "?tab=domain")
            expect(page.locator(".resource-ribbon")).to_contain_text(str(moon + 1))
            if moon == 1:
                page.goto(game_url + "?tab=mail")
                illustration_asset(
                    page.locator(".illustration-start-army"),
                    "action-starts.png",
                )
        page.goto(game_url + "?tab=wars")
        expect(
            page.get_by_role("heading", name="Expeditions" if en else "Expéditions", exact=True)
        ).to_be_visible()
        page.locator('.reign-header a[data-section="domain"]').click()
        page.goto(game_url + "?tab=letters")
        assert (
            page.locator('.letter-entry a[href="?tab=map"]').count()
            == page.locator(".letter-entry").count()
        )
        for title in (
            ("Return of the contingent from Namar", "Successful foray at Sefra")
            if en
            else ("Retour du contingent de Namar", "Pillage réussi à Sefra")
        ):
            expect(
                page.locator(".correspondence").get_by_role("heading", name=title)
            ).to_be_visible()
        expect(page.locator(".correspondence")).to_contain_text(
            "Paid cost of this foray: 65,000 Measures"
            if en
            else "Coût payé pour ce pillage : 65\u202f000 Mesures"
        )
        expect(page.locator(".correspondence")).to_contain_text(
            "Namar: 65,000 Measures paid" if en else "Namar : 65\u202f000 Mesures payées"
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
        expect(page.locator(".letter-entry .illustration-small")).to_have_count(0)
        redesign_reflow(page)
        illustration_asset(page.locator(".illustration-start-army"), "action-starts.png")
        for letter in page.locator(".letter-entry").all():
            expect(letter.locator(":scope > .illustration")).to_have_count(1)
            image_width = letter.locator(":scope > .illustration").bounding_box()["width"]
            assert abs(image_width - letter.bounding_box()["width"]) < 2
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
        page.screenshot(
            path=str(artifacts / f"letters-full-images-mobile-{language}.png"), full_page=True
        )
        page.evaluate("document.documentElement.style.removeProperty('font-size')")
        page.set_viewport_size({"width": 1440, "height": 1100})
        # HTTP cases cover action selection; review and decode each beginning scene.
        for family in (
            "army",
            "storage",
            "forge",
            "walls",
            "irrigation",
            "watch",
            "shelter",
            "transport",
            "siege",
        ):
            scene_name = f"start-{family}"
            page.locator("main").evaluate(
                """(root, scene) => {
                  const el = document.createElement('div');
                  el.id = 'action-artwork-check';
                  el.className = 'illustration illustration-' + scene;
                  el.setAttribute('aria-hidden', 'true');
                  root.append(el);
                }""",
                scene_name,
            )
            scene = page.locator("#action-artwork-check")
            illustration_asset(scene, "action-starts.png")
            scene.screenshot(path=str(artifacts / f"{scene_name}-{language}.png"))
            scene.evaluate("el => el.remove()")
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
                        scene.evaluate("el => getComputedStyle(el, '::before').backgroundSize")
                        == "100% 100%"
                    )
                    box = scene.bounding_box()
                    assert abs(box["width"] / box["height"] - 1.5) < 0.02
                    scene.evaluate("el => el.remove()")
        page.screenshot(path=str(artifacts / f"letters-desktop-{language}.png"), full_page=True)
        # Switching the same persisted letters translates their bodies too.
        page.locator("#language").select_option("fr" if en else "en")
        page.locator(".language-switch button").click()
        expect(page.locator(".correspondence")).to_contain_text(
            "Butin conservé" if en else "Spoils retained"
        )
        page.locator("#language").select_option(language)
        page.locator(".language-switch button").click()
        page.goto(game_url + "?tab=domain")
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
        page.locator(".decree-reading > form button[type=submit]").click()
        for _ in range(5):
            if not page.locator(".reign-header").is_visible():
                page.locator(".panel-close").click()
            page.locator('.reign-header a[data-section="domain"]').click()
            page.locator("#turn-page button.primary-action").click()
            page.goto(page.url.split("?")[0] + "?tab=domain")
        page.goto(game_url + "?tab=letters")
        completion = page.locator(".letter-entry").filter(
            has=page.get_by_role(
                "heading", name="Works completed in Qasr" if en else "Travaux achevés à Qasr"
            )
        )
        illustration_asset(completion.locator(".illustration"), "granary.jpg")
        page.goto(game_url + "?tab=constructions")
        page.goto(game_url + "?tab=constructions&action=forge")
        forge = page.locator("#work-forge")
        forge.locator('input[value="c2"]').check()
        forge.locator('button[type="submit"]').click()
        page.locator(".decree-reading > form button[type=submit]").click()
        page.goto(game_url + "?tab=map&city=c2&action=accounts")
        commitment = page.locator('[data-local-accounts] [data-crew-phase="reserved"]')
        expect(commitment).to_contain_text("Small arsenal" if en else "Petit arsenal")
        expect(commitment).to_contain_text("Expected finish: Moon" if en else "Fin prévue : lune")
        page.goto(game_url + "?tab=city&city=c2")
        expect(page.locator('[data-local-accounts] [data-crew-phase="reserved"]')).to_contain_text(
            "Small arsenal" if en else "Petit arsenal"
        )
        page.goto(game_url + "?tab=constructions&action=storage")
        storage = page.locator("#work-storage")
        expect(storage.locator('input[value="c2"]')).to_be_disabled()
        expect(storage.locator('input[value="c1"]')).to_be_enabled()
        expect(storage.locator('[data-team-state="occupied"]')).to_have_text(
            "Crew occupied" if en else "Équipe occupée"
        )
        expect(storage.locator('[data-team-state="available"]')).to_have_count(2)
        expect(storage.locator('[data-crew-phase="reserved"]')).to_contain_text(
            "Small arsenal" if en else "Petit arsenal"
        )
        expect(storage.locator(".work-transition").first).to_have_text(
            "Additional granaries to Silo complex"
            if en
            else "Greniers supplémentaires à Ensemble de silos"
        )
        expect(storage.locator(".work-benefit").first).to_contain_text(
            "3,600,000 to 5,400,000" if en else "3\u202f600\u202f000 à 5\u202f400\u202f000"
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
                header = page.locator(".reign-header").bounding_box()
                assert header["height"] < 130, {
                    "width": width,
                    "url": page.url,
                    "header": header,
                    "text": page.locator(".reign-header").inner_text(),
                }
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
                for link in page.locator(".reign-header a[data-section]").all():
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
        plain_page.goto(game_url + "?tab=map&city=c1")
        expect(plain_page.locator(".city-actions")).to_be_visible()
        plain_page.locator('.city-actions a[href*="action=works"]').click()
        expect(plain_page.locator(".city-sheet[data-focus-action]")).to_be_visible()
        expect(plain_page.locator(".city-resources")).to_be_visible()
        plain_page.locator(".panel-close").click()
        expect(plain_page.locator(".city-actions")).to_be_visible()
        plain_page.goto(game_url + "?tab=help")
        plain_page.locator("#realm-alerts > summary").focus()
        plain_page.keyboard.press("Enter")
        expect(plain_page.locator("#realm-alerts")).to_have_attribute("open", "")
        no_overflow(plain_page)
        plain_page.locator("#realm-alerts > summary").click()
        expect(plain_page.locator("#victory")).to_be_visible()
        no_overflow(plain_page)
        plain_page.locator("[data-prologue-replay]").click()
        plain_page.locator("[data-prologue-next]").click()
        expect(plain_page.locator("[data-prologue-page]")).to_have_attribute(
            "data-prologue-page", "2"
        )
        plain_page.locator("[data-prologue-previous]").click()
        plain_page.locator("[data-prologue-skip]").click()
        expect(plain_page.locator(".map-guide-key")).to_be_visible()
        plain_page.goto(game_url + "?tab=domain")
        plain_page.goto(game_url + "?tab=map&city=c2&action=accounts")
        expect(plain_page.locator('[data-team-state="occupied"]').first).to_be_visible()
        expect(plain_page.locator('[data-crew-phase="reserved"]').first).to_contain_text(
            "Small arsenal" if en else "Petit arsenal"
        )
        plain_page.goto(game_url + "?tab=city&city=c1")
        expect(plain_page.locator("[data-local-accounts]")).to_be_visible()
        expect(plain_page.locator(".illustration-city-c1")).to_be_visible()
        illustration_asset(plain_page.locator(".illustration-city-c1"), "cityscapes.png")
        redesign_reflow(plain_page)
        no_overflow(plain_page)
        for anchor in ("city-defenses", "city-stocks"):
            plain_page.goto(game_url + "?tab=city&city=c1#" + anchor)
            section_jump_lands(plain_page, "#" + anchor)
        plain_page.goto(game_url + "?tab=wars&action=convoy")
        convoy_help = plain_page.locator("#convoy-order .ledger-help")
        convoy_help.locator("summary").focus()
        plain_page.keyboard.press("Enter")
        expect(convoy_help).to_have_attribute("open", "")
        no_overflow(plain_page)
        plain_page.locator("#convoy-origin").select_option("c1")
        plain_page.locator("#convoy-target").select_option("c3")
        plain_page.locator("#convoy-cargo").fill("500000")
        plain_page.locator("#convoy-order button").click()
        expect(plain_page.locator(".decree-reading")).to_contain_text(
            "50,000 Measures in fees" if en else "50\u00a0000 Mesures de frais"
        )
        expect(plain_page.locator(".reserve-warning")).to_contain_text(
            "350,000" if en else "350\u00a0000"
        )
        no_overflow(plain_page)
        plain_page.screenshot(path=str(artifacts / f"convoy-native-{language}.png"), full_page=True)
        plain_page.locator(".decree-reading > form button[type=submit]").click()
        expect(
            plain_page.locator(".order-entry").filter(
                has_text="Send resources" if en else "Acheminer des ressources"
            )
        ).to_be_visible()
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
        expect(plain_page.locator(".review-panel")).to_be_visible()
        plain_page.goto(game_url + "?tab=wars")
        plain_page.locator('.map-city[href*="city=c4"] .city-marker').click()
        expect(plain_page.locator("#map-context")).to_contain_text("Sefra")
        city_heading_starts_panel(plain_page)
        expect(plain_page.locator("#map-context .illustration")).to_have_count(0)
        note = plain_page.locator(".origin-details").first
        note.locator("summary").focus()
        plain_page.keyboard.press("Enter")
        expect(note.locator("[data-origin-means]")).to_be_visible()
        no_overflow(plain_page)
        plain_page.keyboard.press("Enter")
        plain_page.screenshot(
            path=str(artifacts / f"map-context-mobile-{language}.png"), full_page=True
        )
        plain_page.locator('input[name="kind"][value="raid"]').check()
        expect(plain_page.locator("#mission-target")).to_have_value("c4")
        expect(plain_page.locator('input[name="kind"][value="raid"]')).to_be_checked()
        plain_page.goto(game_url + "?tab=wars")
        plain_page.locator(".order-entry").filter(
            has_text="Send resources" if en else "Acheminer des ressources"
        ).get_by_role("button").click()
        expect(
            plain_page.locator(".order-entry").filter(
                has_text="Send resources" if en else "Acheminer des ressources"
            )
        ).to_have_count(0)
        plain.close()
        # Spend exactly 900k per city on two arsenals and irrigation before harvest.
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
            page.locator(".decree-reading > form button[type=submit]").click()
            for _ in range(4 if tier == 0 else 6):
                page.goto(empty_url + "?tab=domain")
                page.locator("#turn-page button.primary-action").click()
            page.goto(page.url.split("?")[0] + "?tab=domain")
        page.goto(empty_url + "?tab=constructions&action=irrigation")
        irrigation = page.locator("#work-irrigation")
        irrigation.locator("[data-select-cities]").click()
        irrigation.locator('button[type="submit"]').click()
        page.locator(".decree-reading > form button[type=submit]").click()
        page.goto(empty_url + "?tab=domain")
        page.locator("#turn-page button.primary-action").click()
        page.goto(empty_url + "?tab=wars&action=expedition&city=c4")
        for origin in ("c1", "c2", "c3"):
            page.locator(f'input[name="men_{origin}"]').fill("10")
        expect(page.locator("#army-cost")).to_have_text("35,000" if en else "35\u202f000")
        expect(page.locator("[data-expedition-budget]")).to_contain_text(
            "35,000" if en else "35\u202f000"
        )
        page.locator('.primary-action[form="expedition-form"]').click()
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
        expect(native_page.locator("#army-cost")).to_have_text("35,000" if en else "35\u00a0000")
        assert native_page.locator(".origin-funding").count() == 3
        native_page.locator('.primary-action[form="expedition-form"]').click()
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
        clock_label = "Paris time" if en else "heure de Paris"
        expect(page.locator(".moon-banner time")).to_contain_text(clock_label)
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
            for scale in ("125%", "200%"):
                page.evaluate("value => document.documentElement.style.fontSize = value", scale)
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
        expect(native_clock_page.locator(".moon-banner time")).to_contain_text(clock_label)
        no_overflow(native_clock_page)
        native_clock.close()
        assert page.locator(".reign-header [data-deadline]").count() == 0
        page.reload()
        assert (
            page.request.get(automatic_url + "state/").json()["game"]["deadline"]
            == started["game"]["deadline"]
        )
        # A completed reign opens a native literary archive and scoped analysis download.
        page.goto(base_url + "/games/new/")
        page.locator("#id_title").fill("Archive journey")
        page.locator("#id_opponents").select_option("passive")
        page.locator("#id_reign_months").select_option("24")
        page.locator(".game-setup button").click()
        archive_game_url = page.url.split("?")[0]
        page.goto(archive_game_url + "?tab=domain")
        for _ in range(24):
            page.locator("#turn-page button.primary-action").click()
            page.goto(page.url.split("?")[0] + "?tab=domain")
        page.locator('.epilogue a[href$="/archive/"]').click()
        expect(page.locator("h1")).to_have_text(
            "The book of the reign" if en else "Le livre du règne"
        )
        page.locator('a[href="?scope=all"]').click()
        assert page.locator(".letter-entry").count() >= 3
        page.locator("[data-archive-exports] summary").click()
        with page.expect_download() as download_info:
            page.locator('a[href="?scope=all&format=json"]').click()
        assert download_info.value.suggested_filename.endswith("-all.json")
        archive = page.request.get(archive_game_url + "archive/?scope=all&format=json").json()
        with page.expect_download() as compact_download:
            page.locator('a[href="?scope=all&format=compact"]').click()
        assert compact_download.value.suggested_filename.endswith("-all-compact.json")
        compact = page.request.get(archive_game_url + "archive/?scope=all&format=compact").json()
        assert compact["reports"] == archive["reports"]
        assert len(compact["economy"]["rows"]) == 72
        assert len(archive["accounts"]) == 24
        assert archive["coverage"]["missing_account_moons"] == []
        assert set(archive["final_accounts"]) == {"p1", "p2", "p3"}
        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 844})
            no_overflow(page)
            page.evaluate("document.documentElement.style.fontSize = '125%'")
            no_overflow(page)
            page.evaluate("document.documentElement.style.removeProperty('font-size')")
        native_archive = browser.new_context(
            storage_state=context.storage_state(),
            java_script_enabled=False,
            viewport={"width": 320, "height": 844},
        )
        native_archive_page = native_archive.new_page()
        native_archive_page.goto(archive_game_url + "archive/")
        native_archive_page.locator('a[href="?scope=all"]').click()
        native_archive_page.locator("#archive-accounts details summary").first.click()
        expect(native_archive_page.locator("#archive-accounts details").first).to_have_attribute(
            "open", ""
        )
        no_overflow(native_archive_page)
        native_archive.close()
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

# The map journey supplements the retained realm/batch/report compatibility journey.

run_map_journeys()
