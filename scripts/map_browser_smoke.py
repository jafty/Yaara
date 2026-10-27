"""Bilingual map journeys, including native forms and narrow/large-text layouts."""

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def run_map_journeys():
    base = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"), args=["--no-sandbox"]
        )
        for language in ("fr", "en"):
            for javascript in (True, False):
                context = browser.new_context(
                    locale=language,
                    java_script_enabled=javascript,
                    viewport={"width": 1440, "height": 1000},
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base)
                page.locator('form[action="/play/"] button').click()
                page.wait_for_url("**/games/**")
                url = page.url.split("?")[0]
                expect(page.locator(".map-city")).to_have_count(9)
                expect(page.locator(".map-connection")).to_have_count(12)
                for road in page.locator(".map-connection").all():
                    expect(road).to_have_css("opacity", "0")
                expect(page.locator(".map-marker, .map-inner")).to_have_count(0)
                canvas = page.locator(".map-workspace > .realm-map").bounding_box()
                assert canvas["width"] == 720
                assert abs(canvas["y"] - page.locator(".reign-header").bounding_box()["height"]) < 2
                expect(page.locator(".map-guide-key")).to_be_visible()
                expect(page.locator(".map-reference")).to_have_count(0)
                if javascript:
                    # An already-open tab must reload when the server serves newer assets.
                    page.evaluate("""() => {
                        window.yaaraOldAssets = true;
                        const css = document.querySelector('link[href*="workspace."]');
                        css.href += '?old-release';
                    }""")
                    page.locator('.map-city[href*="city=c1"]').focus()
                    page.keyboard.press("Enter")
                    page.wait_for_url("**city=c1**")
                    expect(page.locator(".city-actions")).to_be_visible()
                    assert page.evaluate("window.yaaraOldAssets === undefined")
                    page.goto(url)

                for width, height in ((1440, 1000), (390, 740), (320, 640)):
                    page.set_viewport_size({"width": width, "height": height})
                    page.evaluate("document.fonts.ready")
                    assert page.locator(".map-frame").evaluate("""frame => {
                        const bounds = frame.getBoundingClientRect();
                        const layer = frame.querySelector('.territory-layer').getBoundingClientRect();
                        return Math.abs(bounds.width / bounds.height - 680 / 500) < .01 &&
                          Math.abs(layer.width - frame.clientWidth) < 1 &&
                          Math.abs(layer.height - frame.clientHeight) < 1 &&
                          [...frame.querySelectorAll('.map-name')].every(el => {
                            const box = el.getBoundingClientRect();
                            return box.left >= bounds.left && box.right <= bounds.right &&
                              box.top >= bounds.top && box.bottom <= bounds.bottom;
                          });
                    }""")
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.evaluate(
                    "window.originalMap = document.querySelector('.map-workspace > .realm-map')"
                )
                if javascript:
                    # A pause/closure can remove a calendar between context requests.
                    page.evaluate("""() => {
                        const stale = document.createElement('aside');
                        stale.className = 'moon-banner';
                        document.querySelector('.reign-header').after(stale);
                    }""")
                page.locator('.map-city[href*="city=c1"]').focus()
                page.keyboard.press("Enter")
                expect(page.locator("#context-title")).to_have_text("Qasr")
                for width in (1440, 390, 320):
                    page.set_viewport_size(
                        {"width": width, "height": 1000 if width == 1440 else 844}
                    )
                    board = page.locator(".map-workspace > .realm-map").bounding_box()
                    sheet = page.locator(".city-sheet").bounding_box()
                    if width == 1440:
                        assert board["x"] + board["width"] <= sheet["x"] + 1
                    else:
                        assert board["y"] + board["height"] <= sheet["y"] + 1
                        assert sheet["height"] > board["height"]
                    assert board["width"] > 0 and board["height"] > 0
                    expect(page.locator("[data-sheet-expand]")).to_be_hidden()
                    expect(page.locator(".city-actions")).to_be_visible()
                    for scale in ("100%", "200%"):
                        page.evaluate("s => document.documentElement.style.fontSize = s", scale)
                        page.locator("#city-granary strong").evaluate(
                            "el => el.textContent = '9 999 999 999 999'"
                        )
                        assert page.locator(".city-resources").evaluate("""el =>
                            el.scrollWidth <= el.clientWidth &&
                            [...el.querySelectorAll('dd')].every(item => item.scrollWidth <= item.clientWidth)
                        """)
                    page.evaluate("document.documentElement.style.fontSize = '100%'")
                page.set_viewport_size({"width": 1440, "height": 1000})
                expect(page.locator(".map-connection.selected-road")).to_have_count(3)
                expect(page.locator("#city-granary")).to_be_visible()
                expect(page.locator(".city-resources meter, .city-capabilities")).to_have_count(0)
                expect(page.locator(".city-actions")).to_be_visible()
                expect(page.locator('[data-local-work="c1"]')).to_have_count(0)
                if javascript:
                    assert page.evaluate(
                        "window.originalMap === document.querySelector('.map-workspace > .realm-map')"
                    )
                    expect(page.locator(".moon-banner")).to_have_count(0)
                    page.keyboard.press("Escape")
                    expect(page.locator(".realm-sheet")).to_be_visible()
                    page.go_back()
                    expect(page.locator("#context-title")).to_have_text("Qasr")
                if javascript:
                    page.evaluate("""() => {
                        window.originalSheet = document.querySelector('.city-sheet');
                        window.originalArt = document.querySelector('.city-art');
                        document.querySelector('.sheet-body').scrollTop = 200;
                    }""")
                page.locator('.city-actions a[href*="action=works"]').click()
                page.wait_for_url("**action=works")
                expect(page.locator(".realm-map")).to_be_hidden()
                expect(page.locator(".city-resources")).to_be_visible()
                assert page.locator('[data-local-work="c1"]').count() > 1
                expect(page.locator("#city-works")).to_be_in_viewport()
                if javascript:
                    assert page.evaluate("""() =>
                        originalSheet === document.querySelector('.city-sheet') &&
                        originalArt === document.querySelector('.city-art') &&
                        document.querySelector('.sheet-body').scrollTop === 0 &&
                        getComputedStyle(originalSheet).animationName === 'none'
                    """)
                    expect(page.locator(".sheet-body")).to_have_css("opacity", "1")
                    page.emulate_media(reduced_motion="reduce")
                    page.locator(".panel-close").click()
                    expect(page.locator(".city-actions")).to_be_visible()
                    page.locator('.city-actions a[href*="action=works"]').click()
                    page.wait_for_url("**action=works")
                    assert page.locator(".city-sheet").evaluate(
                        "el => el.getAnimations().length === 0"
                    )
                    page.emulate_media(reduced_motion="no-preference")
                page.locator('.local-work-choice a[href*="action=irrigation"]').click()
                page.wait_for_url("**action=irrigation**")
                expect(page.locator('[data-local-work="c1"]')).to_be_visible()
                expect(page.locator('input[type="checkbox"]')).to_have_count(0)
                page.locator(".panel-close").click()
                page.wait_for_url("**action=works")
                expect(page.locator("#city-works")).to_be_visible()
                page.locator('.local-work-choice a[href*="action=irrigation"]').click()
                page.wait_for_url("**action=irrigation**")
                for width in (1440, 390, 320):
                    page.set_viewport_size(
                        {"width": width, "height": 1000 if width == 1440 else 844}
                    )
                    for scale in ("100%", "200%"):
                        page.evaluate(
                            "scale => document.documentElement.style.fontSize = scale", scale
                        )
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        assert page.locator(".sheet-body").evaluate(
                            "el => el.scrollWidth <= el.clientWidth"
                        )
                        expect(page.locator(".sheet-heading .panel-close")).to_be_in_viewport()
                        if width < 900:
                            expect(page.locator(".reign-header")).to_be_hidden()
                        expect(page.locator(".panel-close")).to_be_in_viewport()
                        assert page.locator(".city-resources").evaluate(
                            "el => el.scrollWidth <= el.clientWidth && [...el.querySelectorAll('dd')].every(item => item.scrollWidth <= item.clientWidth)"
                        )
                        assert page.locator(".sheet-body").evaluate("el => el.clientHeight > 80")
                        expect(
                            page.locator('[data-local-work] button[type="submit"]')
                        ).to_be_enabled()
                    page.evaluate("document.documentElement.style.fontSize = '100%'")
                page.locator('[data-local-work] button[type="submit"]').click()
                expect(page.locator(".map-workspace")).to_be_visible()
                expect(page.locator(".unsealed-leaf")).to_be_visible()
                page.locator(".decree-reading > form button").click()
                expect(page.locator(".orders-register")).to_contain_text("300")
                page.evaluate("document.documentElement.style.fontSize = '200%'")
                for _ in range(50):
                    panel = page.locator(".mail-panel").bounding_box()
                    bounded = (
                        panel["y"] >= 0
                        and panel["y"] + panel["height"] <= page.viewport_size["height"] + 0.5
                    )
                    if bounded:
                        break
                    page.wait_for_timeout(50)
                assert bounded, panel
                assert page.locator(".sheet-body").evaluate("el => el.clientHeight > 80")
                page.evaluate("document.documentElement.style.fontSize = '100%'")
                page.locator(".orders-register button").click()
                page.goto(url + "?tab=map&city=c1&action=convoy&origin=c1")
                for width in (390, 320):
                    page.set_viewport_size({"width": width, "height": 740})
                    fields = page.locator(".convoy-fields :is(input, select)")
                    boxes = [field.bounding_box() for field in fields.all()]
                    assert (
                        max(box["width"] for box in boxes) - min(box["width"] for box in boxes) < 1
                    )
                    assert all(box["height"] >= 44 for box in boxes)
                    for field in ("origin", "target", "cargo"):
                        label = page.locator(f'label[for="convoy-{field}"]').bounding_box()
                        control = page.locator(f"#convoy-{field}").bounding_box()
                        assert label["y"] + label["height"] <= control["y"]
                page.set_viewport_size({"width": 390, "height": 740})
                page.goto(url + "?tab=map&city=c4#map-context")
                expect(page.locator(".expedition-form")).to_be_visible()
                expect(page.locator('.alerts-trigger [data-icon="envelope"]')).to_have_count(1)
                assert page.locator("[data-army-summary]").evaluate(
                    "el => !el.closest('.sheet-body')"
                )
                for width, height in ((1440, 1000), (390, 740), (320, 640)):
                    page.set_viewport_size({"width": width, "height": height})
                    for scale in ("100%", "200%"):
                        page.evaluate("s => document.documentElement.style.fontSize = s", scale)
                        expect(
                            page.locator(".primary-action[form='expedition-form']")
                        ).to_be_in_viewport()
                        expect(page.locator(".panel-close")).to_be_in_viewport()
                        geometry = page.locator(".sheet-body").evaluate("""el => ({
                            height: el.clientHeight, width: el.clientWidth,
                            scrollWidth: el.scrollWidth,
                            position: getComputedStyle(el.parentElement).position
                        })""")
                        assert (
                            geometry["height"] > 80 and geometry["scrollWidth"] <= geometry["width"]
                        ), (language, javascript, width, height, scale, geometry)
                        if javascript and geometry["position"] == "absolute":
                            expect(page.locator(".realm-map")).to_have_attribute(
                                "aria-hidden", "true"
                            )
                            assert page.locator(".reign-header").evaluate("el => el.inert")
                        assert page.locator(".sheet-body").evaluate("""el =>
                            el.getBoundingClientRect().bottom <=
                            document.querySelector('[data-army-summary]').getBoundingClientRect().top + 1
                        """)
                    page.evaluate("document.documentElement.style.fontSize = '100%'")
                page.set_viewport_size({"width": 390, "height": 740})
                controls = page.locator('[data-origin="c1"] [data-contingent-controls]')
                if javascript:
                    controls.locator('[data-adjust="1"]').click()
                    expect(page.locator("#men-c1")).to_have_value("1")
                    page.locator("#men-c1").fill("5")
                    expect(page.locator("#army-total")).to_have_text("5")
                    controls.locator("[data-maximum]").click()
                    expect(page.locator("#men-c1")).to_have_value("100")
                    controls.locator('[data-adjust="-1"]').click()
                    expect(page.locator("#men-c1")).to_have_value("99")
                else:
                    expect(controls.locator('[data-adjust="1"]')).to_be_hidden()
                    expect(controls.locator('input[type="range"]')).to_have_count(0)
                    expect(page.locator("#men-c1")).to_be_visible()
                page.locator("#men-c1").fill("10")
                page.locator("#men-c3").fill("20")
                if javascript:
                    expect(page.locator("#army-total")).to_have_text("30")
                    page.locator('input[name="kind"][value="capture"]').check()
                    expect(page.locator("[data-loot-preview]")).to_be_hidden()
                    expect(page.locator("#mission-help")).to_contain_text("80")
                    page.locator('input[name="kind"][value="raid"]').check()
                    expect(page.locator("[data-loot-preview]")).to_be_visible()
                    expect(page.locator("#draft-route path")).to_have_count(1)
                    assert page.locator("#draft-route path").get_attribute("d").startswith("M ")
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    expect(page.locator(".city-sheet[data-focus-action]")).to_be_visible()
                    expect(page.locator("#men-c1")).to_have_value("10")
                    expect(page.locator("#men-c3")).to_have_value("20")
                    page.set_viewport_size({"width": 390, "height": 740})
                page.screenshot(
                    path=str(artifacts / f"army-{language}-{javascript}.png"), full_page=True
                )
                page.locator('.primary-action[form="expedition-form"]').click()
                page.locator(".decree-reading > form button").click()
                expect(page.locator('[data-march-state="sealed"]')).to_have_count(1)
                page.goto(url + "?tab=domain#turn-page")
                page.locator('#turn-page form[action$="/advance/"] button').click()
                page.goto(url + "?tab=mail&mail=schedule")
                expect(page.locator('[data-march-state="outbound"]')).to_have_count(1)
                page.locator('.milestones a[href^="#mission-"]').first.click()
                expect(page.locator('.mail-panel p[id^="mission-"]')).to_be_in_viewport()
                expect(page.locator(".expedition-form")).to_have_count(0)
                page.goto(url + "?tab=mail&mail=chronicle")
                if javascript:
                    button = page.locator("[data-read-report]").first
                    article_id = button.get_attribute("data-read-report")
                    button.click()
                    page.reload()
                    expect(page.locator("#" + article_id)).not_to_have_class("unread-report")
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(url)
                page.screenshot(
                    path=str(artifacts / f"map-{language}-{javascript}.png"), full_page=True
                )
                assert not errors, errors
                context.close()
        browser.close()
    print("Map journeys passed in French and English, with and without JavaScript.")


if __name__ == "__main__":
    run_map_journeys()
