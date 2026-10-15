import pytest
from django.contrib.auth import get_user_model


@pytest.fixture(autouse=True)
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

    return create_game(user, "Le règne des tests", opponents="passive")
