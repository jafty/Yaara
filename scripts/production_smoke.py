"""Production WSGI-stack smoke, including HTTPS/CSRF and a complete capture.

Run against a disposable database with DEBUG=0 and a configured SECRET_KEY:
    python scripts/production_smoke.py
It creates a uniquely named test account and game without exposing credentials.
"""

import html
import os
import re
import secrets
import sys
from pathlib import Path

import django
from django.conf import settings
from django.test import Client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yaara.settings")

django.setup()

assert not settings.DEBUG, "This smoke must exercise production settings"
client = Client(
    enforce_csrf_checks=True,
    HTTP_HOST="localhost",
    HTTP_X_FORWARDED_PROTO="https",
    HTTP_ORIGIN="https://localhost",
)


def post(path, data):
    return client.post(
        path, {**data, "csrfmiddlewaretoken": client.cookies["csrftoken"].value}, secure=True
    )


signup = client.get("/accounts/signup/", secure=True)
assert signup.status_code == 200
assert client.cookies["csrftoken"]["secure"]
password = secrets.token_urlsafe(30)
response = post(
    "/accounts/signup/",
    {
        "username": "production_" + secrets.token_hex(5),
        "password1": password,
        "password2": password,
    },
)
assert response.status_code == 302
assert client.cookies["sessionid"]["secure"]
response = post(
    "/games/new/",
    {
        "title": "Production capture smoke",
        "player_name": "La maison d’Ambre",
        "version": "V1",
        "opponents": "passive",
        "reign_months": 120,
        "mode": "manual",
        "interval_minutes": 10,
    },
)
assert response.status_code == 302
game_path = response["Location"]
page = client.get(game_path, secure=True)
assert page.status_code == 200
static_path = html.unescape(re.search(r'href="([^"]+\.css)"', page.content.decode())[1])
assert client.get(static_path, secure=True).status_code == 200
for month in range(1, 13):
    assert post(game_path + "advance/", {"month": month}).status_code == 302
state = client.get(game_path + "state/", secure=True).json()
assert state["view"]["available_stock"] == 5_400_000
quote = post(
    game_path + "orders/preview/",
    {"kind": "capture", "target": "c4", "men_c1": 50, "men_c2": 50, "men_c3": 50},
)
assert quote.status_code == 200
payload = html.unescape(re.search(r'name="payload" value="([^"]+)"', quote.content.decode())[1])
assert post(game_path + "orders/confirm/", {"payload": payload}).status_code == 302
for month in range(13, 16):
    assert post(game_path + "advance/", {"month": month}).status_code == 302
state = client.get(game_path + "state/", secure=True).json()
assert state["view"]["month"] == 16
assert len(state["view"]["owned_cities"]) == 4
assert state["view"]["orders"][0]["status"] == "completed"
assert post(game_path + "advance/", {"month": 15}).status_code == 302
assert client.get(game_path + "state/", secure=True).json()["view"]["month"] == 16
letters = client.get(game_path + "?tab=letters", secure=True)
assert "Assaut victorieux" in letters.content.decode()
print(
    "Production smoke passed: secure cookies, CSRF, static assets, signup, annual harvest, capture, returns, persistence and duplicate-tick handling."
)
