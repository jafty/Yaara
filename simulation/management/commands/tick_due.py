from django.core.management.base import BaseCommand
from django.utils import timezone

from simulation.calendar import closing_moon
from simulation.models import Game
from simulation.rules import RuleError
from simulation.services import tick


class Command(BaseCommand):
    help = "Resolve due months once; safely pause games after excessive lateness."

    def handle(self, *args, **options):
        games = Game.objects.filter(mode="scheduled", paused=False, deadline__lte=timezone.now())
        for game in games.iterator():
            try:
                _, executed = tick(game.id, closing_moon(game.state))
                self.stdout.write(f"{game.id}: {'resolved' if executed else 'unchanged or paused'}")
            except RuleError as error:
                self.stderr.write(f"{game.id}: {error}")
