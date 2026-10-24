from django.core.management.base import BaseCommand

from simulation.guest_services import cleanup_expired_guests


class Command(BaseCommand):
    help = "Remove only expired, unclaimed, private guest solos and old creation counters."

    def handle(self, *args, **options):
        result = cleanup_expired_guests()
        self.stdout.write(
            f"Removed {result['removed']} expired guests; skipped {result['skipped']}."
        )
