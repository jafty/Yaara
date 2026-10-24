"""Explicit temporary identities, separate from passwordless shared-game seats."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class GuestIdentity(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guest_identity"
    )
    game = models.OneToOneField(
        "simulation.Game", on_delete=models.CASCADE, related_name="guest_identity"
    )
    start_key = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)


class GuestCreationBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField(default=0)
