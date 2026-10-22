import logging.config
import runpy
from pathlib import Path

import pytest

from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "render-host-trusted", "Render deployment: generated hostname accepts HTTPS requests and forms"
)
def test_render_hostname_is_allowed_and_trusted(monkeypatch):
    """Given a Render service alongside Railway and a custom domain.
    When deployment settings are loaded.
    Then Render accepts its hostname and HTTPS forms while preserving existing hosts.
    """
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "yaara-backup.onrender.com")
    monkeypatch.setenv("ALLOWED_HOSTS", "game.example.com")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "yaara.up.railway.app")
    settings = runpy.run_path(str(Path(__file__).parents[1] / "yaara/settings.py"))
    assert "yaara-backup.onrender.com" in settings["ALLOWED_HOSTS"]
    assert "https://yaara-backup.onrender.com" in settings["CSRF_TRUSTED_ORIGINS"]
    assert "game.example.com" in settings["ALLOWED_HOSTS"]
    assert "yaara.up.railway.app" in settings["ALLOWED_HOSTS"]


@case("render-host-absent", "Render deployment: local settings never add an empty hostname")
def test_missing_render_hostname_is_ignored(monkeypatch):
    """Given a deployment without a Render hostname.
    When deployment settings are loaded.
    Then no empty hostname or incomplete HTTPS origin is trusted.
    """
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    settings = runpy.run_path(str(Path(__file__).parents[1] / "yaara/settings.py"))
    assert "" not in settings["ALLOWED_HOSTS"]
    assert "https://" not in settings["CSRF_TRUSTED_ORIGINS"]


@case(
    "deployment-errors-console", "Render deployment: rejected hosts are visible with DEBUG disabled"
)
def test_rejected_host_error_reaches_console(monkeypatch, capsys):
    """Given production settings with debugging disabled.
    When Django logs a rejected request hostname.
    Then the error appears in the platform console logs.
    """
    monkeypatch.setenv("DEBUG", "0")
    monkeypatch.setenv("SECRET_KEY", "test-only-settings-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    settings = runpy.run_path(str(Path(__file__).parents[1] / "yaara/settings.py"))
    logger = logging.getLogger("django.security.DisallowedHost")
    parent = logging.getLogger("django")
    previous = parent.handlers[:], parent.level, parent.propagate
    try:
        logging.config.dictConfig(settings["LOGGING"])
        logger.error("Invalid HTTP_HOST header: 'untrusted.example'")
        assert "Invalid HTTP_HOST header" in capsys.readouterr().err
    finally:
        parent.handlers, parent.level, parent.propagate = previous
