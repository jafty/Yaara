from django.core.management.base import BaseCommand

from simulation.notifications import process_due


class Command(BaseCommand):
    help = "Send due confirmed recipient notifications through Django's mail backend."

    def handle(self, *args, **options):
        self.stdout.write(f"Sent {process_due()} notification batches.")
