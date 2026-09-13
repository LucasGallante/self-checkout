import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app

# Dedicated Postgres test DB. The concurrency tests need real row locking
# (SELECT ... FOR UPDATE) which SQLite's StaticPool can't exercise, so we run
# everything against Postgres.
TEST_DATABASE_URL = (
    "postgresql+psycopg2://selfcheckout:selfcheckout@localhost:5432/selfcheckout_test"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _reset_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
