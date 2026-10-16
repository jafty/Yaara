import signal
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections


class Command(BaseCommand):
    help = "Run the shared calendar worker; use one separate Railway service."

    def handle(self, *args, **options):
        stopped = False

        def stop(*_):
            nonlocal stopped
            stopped = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not stopped:
            close_old_connections()
            call_command("tick_due", stdout=self.stdout, stderr=self.stderr)
            for _ in range(10):
                if stopped:
                    break
                time.sleep(1)
