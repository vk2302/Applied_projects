# этот файл:
# берет базу данныз SQLite,
# перед каждым тестом создаёт таблицы заново, после теста всё чистит
# подменяет Redis на объект в памяти, создаёт TestClient.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.models.archived_link import ArchivedLink  # noqa: F401
from app.models.link import Link  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.user import User  # noqa: F401


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.deleted_keys = []

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, key):
        self.deleted_keys.append(key)
        self.store.pop(key, None)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    from app.services import cache
    import app.main as main_module

    fake_redis = FakeRedis()
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "wait_for_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "start_scheduler", lambda: None)
    monkeypatch.setattr(main_module, "stop_scheduler", lambda: None)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    main_module.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def registered_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="function")
def auth_headers(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
