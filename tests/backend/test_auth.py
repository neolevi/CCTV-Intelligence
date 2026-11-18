"""Tests for User Authentication, Argon2 Security, and Database Session Logic."""
import pytest
from fastapi import HTTPException
from backend.database import SessionLocal
from backend import models, schemas
from backend.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.auth.routes import register, login, get_me


def test_password_hashing():
    pw = "SuperSecure987!"
    hashed = get_password_hash(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    token = create_access_token(subject=42, extra_claims={"role": "operator"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "operator"


def test_login_default_admin():
    with SessionLocal() as db:
        creds = schemas.UserLogin(email="admin@cctv.local", password="AdminPass123!")
        token_data = login(creds, db)
        assert token_data["access_token"] is not None
        assert token_data["user"].email == "admin@cctv.local"
        assert token_data["user"].role == "admin"


def test_login_invalid_credentials():
    with SessionLocal() as db:
        creds = schemas.UserLogin(email="admin@cctv.local", password="WrongPassword123!")
        with pytest.raises(HTTPException) as exc_info:
            login(creds, db)
        assert exc_info.value.status_code == 401


def test_user_registration_and_duplicate_prevention():
    with SessionLocal() as db:
        test_email = f"officer_test_{id(db)}@cctv.local"
        user_in = schemas.UserCreate(
            email=test_email,
            password="SecurePassword123!",
            full_name="Test Officer",
        )
        res = register(user_in, db)
        assert res["access_token"] is not None
        assert res["user"].email == test_email
        assert res["user"].role == "operator"

        # Duplicate attempt raises HTTPException 400
        with pytest.raises(HTTPException) as exc_info:
            register(user_in, db)
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()


def test_registration_privilege_escalation_prevented():
    """Verify that public registration does not allow self-promotion to admin."""
    with SessionLocal() as db:
        test_email = f"hacker_attempt_{id(db)}@cctv.local"
        # UserCreate schema has no role field; even if submitted, role must remain operator
        user_in = schemas.UserCreate(
            email=test_email,
            password="HackerPassword123!",
            full_name="Privilege Escalation Tester",
        )
        res = register(user_in, db)
        assert res["user"].role == "operator"
        assert res["user"].role != "admin"


def test_get_me():
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        assert admin is not None
        user_out = get_me(current_user=admin)
        assert user_out.email == "admin@cctv.local"
