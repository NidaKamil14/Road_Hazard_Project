import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pwdlib import PasswordHash

import os
os.environ["SESSION_SECRET_KEY"] = "test-secret-key-for-pytest-only-must-be-32-chars-long"
os.environ["SESSION_COOKIE_SECURE"] = "false"

# Override the database for testing
from backend.database import Base, get_db
from backend.main import app
from backend.models.admin import Admin

# Use an in-memory SQLite database for tests to isolate from development DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Admin.__table__.create(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

password_hash = PasswordHash.recommended()

@pytest.fixture(autouse=True)
def setup_db():
    # Setup: Create tables
    Admin.__table__.create(bind=engine, checkfirst=True)
    db = TestingSessionLocal()

    # Add active admin
    active_admin = Admin(
        username="testadmin",
        password_hash=password_hash.hash("secure123"),
        is_active=True
    )
    # Add disabled admin
    disabled_admin = Admin(
        username="disabledadmin",
        password_hash=password_hash.hash("secure123"),
        is_active=False
    )

    db.add(active_admin)
    db.add(disabled_admin)
    db.commit()
    db.close()

    yield

    # Teardown: Drop tables
    Admin.__table__.drop(bind=engine, checkfirst=True)

def test_password_hashing():
    phash = PasswordHash.recommended()
    hash_str = phash.hash("my_password")
    assert phash.verify("my_password", hash_str)
    assert not phash.verify("wrong_password", hash_str)

def test_valid_login(client):
    response = client.post("/api/auth/login", json={"username": "testadmin", "password": "secure123"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user"]["username"] == "testadmin"
    assert "road_hazard_admin_session" in response.cookies

def test_invalid_username(client):
    response = client.post("/api/auth/login", json={"username": "wronguser", "password": "secure123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"
    assert "road_hazard_admin_session" not in response.cookies

def test_invalid_password(client):
    response = client.post("/api/auth/login", json={"username": "testadmin", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"
    assert "road_hazard_admin_session" not in response.cookies

def test_disabled_administrator(client):
    response = client.post("/api/auth/login", json={"username": "disabledadmin", "password": "secure123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"
    assert "road_hazard_admin_session" not in response.cookies

def test_session_lifecycle(client):
    # Check session before login
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False

    # Login
    response = client.post("/api/auth/login", json={"username": "testadmin", "password": "secure123"})
    assert response.status_code == 200
    assert "road_hazard_admin_session" in response.cookies

    # Check session after login
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["username"] == "testadmin"

    # Logout
    response = client.post("/api/auth/logout")
    assert response.status_code == 200

    # Check session after logout
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False

def test_protected_access_without_session(client):
    # If the user has an endpoint that depends on the session, it should fail
    # Since we only have /session that checks it directly and returns {authenticated: False}
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False

def test_disabled_admin_during_session(client):
    # a. logs in successfully
    response = client.post("/api/auth/login", json={"username": "testadmin", "password": "secure123"})
    assert response.status_code == 200
    assert "road_hazard_admin_session" in response.cookies

    # b. disables that administrator in the test database
    db = TestingSessionLocal()
    admin = db.query(Admin).filter(Admin.username == "testadmin").first()
    admin.is_active = False
    db.commit()
    db.close()

    # c. calls GET /api/auth/session
    response = client.get("/api/auth/session")

    # d. verifies the session is rejected and cleared
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"

def test_username_stripping(client):
    response = client.post("/api/auth/login", json={"username": "  testadmin  ", "password": "secure123"})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "testadmin"

def test_password_whitespace_not_stripped():
    from backend.schemas.auth import LoginRequest
    req = LoginRequest(username="testadmin", password=" secure123 ")
    assert req.password == " secure123 "
