import logging
import time

import pytest
from pytest_cqase.plugin import qase

logger = logging.getLogger("ncps")


@qase.id(1)
def test_app():
    """
    Steps
    1. One
    2. Two
    """
    time.sleep(4)
    logger.info("Start 1 test")
    logger.info("End 1 test")
    assert 1 == 2


@qase.id(2)
def test_function(record_property):
    """
    Steps
    1. One
    2. Two
    """
    logger.info("Start 2 test")
    logger.info("End 2 test")
    assert 1 == 1


def test_without_function(record_property):
    assert 1 == 1


@qase.id(3, 4)
def test_four():
    assert 1 == 1


@pytest.mark.skip
@qase.id(5)
def test_skip():
    assert 1 == 1


@pytest.mark.xfail
@qase.id(7)
def test_xfailed():
    assert 1 == 2


@pytest.mark.parametrize("a", [1, 2])
@qase.id(8)
def test_param(a):
    assert a == a
