"""Fixed collaborators, never alternative implementations of rules or storage."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FixedRandom:
    raid_percentage: int = 40

    def __call__(self, seed, month, purpose):
        return self

    def shuffle(self, items):
        # The prescribed permutation is the original order.
        return None

    def choice(self, values):
        assert self.raid_percentage in values
        return self.raid_percentage


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def __call__(self):
        return self.instant


@dataclass(frozen=True)
class FailingBoundary:
    message: str

    def __call__(self, *args, **kwargs):
        raise RuntimeError(self.message)
