import pytest

from backend.app import app


@pytest.fixture()
def client():
    app.config.update({"TESTING": True})
    with app.test_client() as c:
        yield c
