import pytest

from nexuscore import TestClock
from nexuscore import TraderId


@pytest.fixture
def clock():
    return TestClock()


@pytest.fixture
def trader_id():
    return TraderId("TRADER-001")
