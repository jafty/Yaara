from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant one existing registered user the official multiplayer operator permission."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        from simulation.guest_services import is_guest

        user = get_user_model().objects.filter(username=options["username"]).first()
        if user is None or is_guest(user) or hasattr(user, "shared_identity"):
            raise CommandError("Choose an existing registered account.")
        permission = Permission.objects.get(
            content_type__app_label="simulation", codename="manage_multiplayer_games"
        )
        user.user_permissions.add(permission)
        self.stdout.write("Multiplayer operator permission granted.")
