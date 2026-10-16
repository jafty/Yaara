"""Exercise the shipped template and script with a controlled polling response."""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from django.template.loader import render_to_string
from playwright.sync_api import sync_playwright

from tests.cases import case


@case("polling-rendered-revision", "PR #1: compare the first poll with the rendered revision")
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize(
    "rendered,current,expected",
    [(0, 1, 1), (7, 8, 1), (0, 0, 0)],
    ids=["initial-change", "later-change", "unchanged"],
)
def test_polling_uses_rendered_revision(rendered, current, expected):
    html = render_to_string(
        "simulation/manuscript.html",
        {
            "game": {
                "id": UUID(int=1),
                "title": "Test",
                "mode": "scheduled",
                "deadline": datetime(2030, 1, 1, tzinfo=timezone.utc),
                "revision": rendered,
            },
            "view": {"finished": False},
        },
    )
    script = Path("simulation/static/simulation/app.js").read_text()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=shutil.which("chromium"))
        page = browser.new_page()
        page.clock.install()

        def respond(route):
            if route.request.url.endswith("state/"):
                route.fulfill(json={"game": {"revision": current}})
            elif route.request.url.endswith("app.js"):
                route.fulfill(body=script, content_type="text/javascript")
            elif route.request.resource_type == "document":
                route.fulfill(body=html, content_type="text/html")
            else:
                route.fulfill(body="")

        page.route("**/*", respond)
        page.goto("http://localhost/games/1/")
        page.locator("#main").evaluate(
            "element => element.innerHTML += '<input id=unsent value=draft>'"
        )
        with page.expect_response("**/state/"):
            page.clock.fast_forward(15000)
        page.evaluate("async () => { await new Promise(r => setTimeout(r, 0)); }")
        assert page.locator("#refresh-notice").count() == expected
        with page.expect_response("**/state/"):
            page.clock.fast_forward(15000)
        page.evaluate("async () => { await new Promise(r => setTimeout(r, 0)); }")
        assert page.locator("#refresh-notice").count() == expected
        assert page.locator("#unsent").input_value() == "draft"
        browser.close()
