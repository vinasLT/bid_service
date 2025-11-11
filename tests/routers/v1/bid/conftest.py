import pytest

from tests.routers.v1.bid.stubs import AuthClientStub, override_auth_client


@pytest.fixture(autouse=True)
def auth_client_stub(monkeypatch):
    return override_auth_client(monkeypatch, AuthClientStub())
