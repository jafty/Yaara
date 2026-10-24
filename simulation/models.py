import uuid

from django.conf import settings
from django.db import models


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=80)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    state = models.JSONField()
    seed = models.CharField(max_length=64)
    revision = models.PositiveIntegerField(default=0)
    mode = models.CharField(max_length=10, default="manual")
    interval_minutes = models.PositiveSmallIntegerField(default=10)
    deadline = models.DateTimeField(null=True, blank=True)
    paused = models.BooleanField(default=False)
    remaining_seconds = models.PositiveIntegerField(default=600)
    ranked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=16, default="solo")
    lobby_status = models.CharField(max_length=16, blank=True, default="")
    play_window = models.CharField(max_length=240, blank=True, default="")
    auto_start = models.BooleanField(default=False)
    recruitment_version = models.PositiveIntegerField(default=1)

    class Meta:
        permissions = [("manage_multiplayer_games", "Manage official multiplayer reigns")]


class Participant(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    actor = models.CharField(max_length=10)
    view_revision = models.PositiveIntegerField(default=0)
    claim_key = models.UUIDField(null=True, blank=True, unique=True)
    claim_version = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "user"], name="one_user_per_game"),
            models.UniqueConstraint(fields=["game", "actor"], name="one_user_per_actor"),
        ]


class SeatIdentity(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shared_identity"
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_shared_seats",
    )


class SharedInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="invitations")
    actor = models.CharField(max_length=10)
    version = models.PositiveIntegerField(default=1)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "actor"], name="one_shared_invite_per_seat")
        ]


class CommandReceipt(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    actor = models.CharField(max_length=10)
    request_id = models.UUIDField()
    order_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "actor", "request_id"], name="unique_command_delivery"
            )
        ]


class TargetEngagement(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    city_id = models.CharField(max_length=10)
    order_id = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "city_id"], name="one_active_attack_per_city")
        ]


class TickExecution(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="ticks")
    month = models.PositiveIntegerField()
    rules = models.CharField(max_length=8)
    engine_version = models.CharField(max_length=20, default="0.1.0")
    trace = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "month"], name="one_execution_per_month")
        ]


class Report(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="reports")
    recipient = models.CharField(max_length=10)
    month = models.PositiveIntegerField()
    kind = models.CharField(max_length=20)
    title = models.CharField(max_length=180)
    body = models.TextField()
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-month", "-id"]
        indexes = [models.Index(fields=["game", "recipient", "-month"])]


class EmailSubscription(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="email_subscription"
    )
    email = models.EmailField(blank=True)
    language = models.CharField(max_length=2, default="fr")
    token = models.UUIDField(default=uuid.uuid4)
    requested_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    start = models.BooleanField(default=True)
    capture = models.BooleanField(default=True)
    yearly = models.BooleanField(default=True)
    raid = models.BooleanField(default=False)
    last_raid_sent_at = models.DateTimeField(null=True, blank=True)


class NotificationDelivery(models.Model):
    subscription = models.ForeignKey(
        EmailSubscription, on_delete=models.CASCADE, related_name="deliveries"
    )
    report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True)
    event_key = models.CharField(max_length=80)
    kind = models.CharField(max_length=10)
    status = models.CharField(max_length=12, default="pending")
    available_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "event_key"], name="one_email_per_recipient_event"
            )
        ]


from .guest_models import GuestCreationBucket, GuestIdentity  # noqa: E402,F401
