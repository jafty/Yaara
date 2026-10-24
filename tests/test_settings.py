import logging.config
import os
import runpy
import subprocess
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
    previous = {
        name: (configured.handlers[:], configured.level, configured.propagate)
        for name in settings["LOGGING"]["loggers"]
        for configured in [logging.getLogger(name)]
    }
    try:
        logging.config.dictConfig(settings["LOGGING"])
        logger.error("Invalid HTTP_HOST header: 'untrusted.example'")
        assert "Invalid HTTP_HOST header" in capsys.readouterr().err
    finally:
        for name, state in previous.items():
            configured = logging.getLogger(name)
            configured.handlers, configured.level, configured.propagate = state


@case("render-startup-migrations", "Render deployment: migrations must succeed before HTTP startup")
@pytest.mark.parametrize("migration_status", [0, 1], ids=["success", "failure"])
def test_render_startup_migration_boundary(tmp_path, migration_status):
    """Given a Render startup with migration exit status {migration_status}.
    When the dedicated startup script runs.
    Then Gunicorn starts only after successful migrations.
    """
    events = tmp_path / "events"
    python = tmp_path / "python"
    python.write_text(
        f'#!/bin/sh\nprintf "migrate %s\\n" "$*" >> "$STARTUP_EVENTS"\nexit {migration_status}\n',
        newline="\n",
    )
    gunicorn = tmp_path / "gunicorn"
    gunicorn.write_text('#!/bin/sh\nprintf "serve\\n" >> "$STARTUP_EVENTS"\n', newline="\n")
    python.chmod(0o755)
    gunicorn.chmod(0o755)
    result = subprocess.run(
        ["sh", "scripts/start-render.sh"],
        cwd=Path(__file__).parents[1],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "STARTUP_EVENTS": events.as_posix(),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == migration_status
    assert events.read_text().splitlines() == ["migrate manage.py migrate --noinput"] + (
        ["serve"] if migration_status == 0 else []
    )


@case("deployment-access-log-private", "Shared invitations: HTTP access logs omit bearer URLs")
def test_access_log_omits_private_request_fields(tmp_path):
    """Given a request carrying a private invitation in its path and referrer.
    When the deployment access log format renders the request.
    Then method status and timing remain available without request URLs or secrets.
    """
    arguments = tmp_path / "arguments"
    gunicorn = tmp_path / "gunicorn"
    gunicorn.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$STARTUP_ARGUMENTS"\n')
    gunicorn.chmod(0o755)
    subprocess.run(
        ["sh", "scripts/start.sh"],
        cwd=Path(__file__).parents[1],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "STARTUP_ARGUMENTS": arguments.as_posix(),
        },
        check=True,
    )
    supplied = arguments.read_text().splitlines()
    access_format = supplied[supplied.index("--access-logformat") + 1]
    rendered = access_format % {
        "t": "[24/Oct/2026:12:00:00 +0000]",
        "m": "GET",
        "s": "403",
        "D": "1250",
        "B": "42",
        "r": "GET /join/private-seat-secret/?credential=private-query HTTP/1.1",
        "U": "/join/private-seat-secret/",
        "q": "credential=private-query",
        "f": "https://example.test/join/private-referrer/",
    }
    assert "GET" in rendered and "403" in rendered and "1250" in rendered
    assert "private-" not in rendered and "/join/" not in rendered


@case(
    "deployment-request-log-private",
    "Shared invitations: request and error logs redact seat tokens",
)
@pytest.mark.parametrize(
    "logger_name",
    ["django.request", "django.security.csrf", "django.server", "gunicorn.error"],
    ids=["request", "csrf", "development-server", "worker-error"],
)
def test_request_logs_redact_private_links(logger_name, capsys):
    """Given a request error containing an invitation token in arguments and traceback.
    When {logger_name} writes the error through the deployment logging configuration.
    Then useful error diagnostics remain while every private token is redacted.
    """
    settings = runpy.run_path(str(Path(__file__).parents[1] / "yaara/settings.py"))
    names = set(settings["LOGGING"]["loggers"]) | {logger_name}
    previous = {
        name: (logger.handlers[:], logger.level, logger.propagate)
        for name in names
        for logger in [logging.getLogger(name)]
    }
    try:
        logging.config.dictConfig(settings["LOGGING"])
        logger = logging.getLogger(logger_name)
        try:
            raise ValueError("Rejected private route /join/traceback-seat-secret/")
        except ValueError:
            logger.error("Forbidden: %s", "/join/request-seat-secret/", exc_info=True)
        output = capsys.readouterr().err
        assert "Forbidden" in output and "ValueError" in output
        assert "request-seat-secret" not in output
        assert "traceback-seat-secret" not in output
        assert "/join/[redacted]/" in output
    finally:
        for name, state in previous.items():
            logger = logging.getLogger(name)
            logger.handlers, logger.level, logger.propagate = state
