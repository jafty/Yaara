import json
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def test_static_storage(settings):
    # HTTP unit tests do not build deployment assets; the production smoke does.
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("pretender", password="Test-only-password-832!")


@pytest.fixture
def game(user):
    from simulation.services import create_game

    # Existing exact-date cases also protect compatibility with persisted reigns.
    return create_game(user, "Le règne des tests", opponents="passive", calendar_version=1)


def pytest_addoption(parser):
    parser.addoption("--case-report", help="Write the collected variation/result matrix as JSON")
    parser.addoption(
        "--check-case-catalog", action="store_true", help="Require the reviewed case ID set"
    )
    parser.addoption("--require-postgresql", action="store_true", help="Reject SQLite full runs")
    parser.addoption("--fail-on-skip", action="store_true", help="Reject skipped or xfailed cases")


def pytest_sessionstart(session):
    if session.config.getoption("--require-postgresql"):
        from django.db import connection

        if connection.vendor != "postgresql":
            raise pytest.UsageError("The full suite requires a real PostgreSQL DATABASE_URL")
    session.config._yaara_cases = {}


def pytest_collection_modifyitems(config, items):
    identifiers = set()
    for item in items:
        markers = list(item.iter_markers("case"))
        layers = [
            name for name in ("logic", "integration", "journey") if item.get_closest_marker(name)
        ]
        if len(markers) != 1 or len(layers) != 1:
            raise pytest.UsageError(f"{item.nodeid}: require exactly one case and one layer")
        marker = markers[0]
        if (
            len(marker.args) != 2
            or not all(isinstance(arg, str) and arg.strip() for arg in marker.args)
            or not re.fullmatch(r"[a-z][a-z0-9-]*", marker.args[0])
        ):
            raise pytest.UsageError(
                f"{item.nodeid}: require case('stable-id', 'source requirement')"
            )
        identifier, requirement = marker.args
        if hasattr(item, "callspec"):
            # Explicit row IDs identify independently collected variations.
            identifier += "/" + item.callspec.id
        if identifier in identifiers:
            raise pytest.UsageError(f"Duplicate variation ID: {identifier}")
        identifiers.add(identifier)
        config._yaara_cases[item.nodeid] = {
            "id": identifier,
            "requirement": requirement,
            "layer": layers[0],
            "nodeid": item.nodeid,
            "phases": {},
        }
    if config.getoption("--check-case-catalog"):
        catalog = Path(__file__).with_name("case_ids.txt")
        expected = set(catalog.read_text().splitlines())
        if identifiers != expected:
            raise pytest.UsageError(
                f"Case catalog differs: missing={sorted(expected - identifiers)}, "
                f"uncatalogued={sorted(identifiers - expected)}. Review the variation list."
            )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    item.config._yaara_cases[item.nodeid]["phases"][report.when] = report.outcome
    if hasattr(report, "wasxfail"):
        item.config._yaara_cases[item.nodeid]["xfail"] = report.wasxfail


def pytest_sessionfinish(session, exitstatus):
    cases = list(session.config._yaara_cases.values())
    for row in cases:
        phases = row["phases"].values()
        row["outcome"] = (
            "failed"
            if "failed" in phases
            else "skipped"
            if "skipped" in phases
            else "passed"
            if len(row["phases"]) == 3
            else "not-run"
        )
    if session.config.getoption("--fail-on-skip") and any(
        "skipped" in row["phases"].values() or "xfail" in row for row in cases
    ):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    path = session.config.getoption("--case-report")
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(cases, indent=2) + "\n")
