from pytest_cqase import qase


@qase.id(1)
def test_one():
    assert 1 == 1


@qase.id(2)
def test_two():
    assert 1 == 2
