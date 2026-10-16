"""One stable identifier and one source requirement per collected variation."""

import pytest


def case(identifier, requirement):
    return pytest.mark.case(identifier, requirement)
