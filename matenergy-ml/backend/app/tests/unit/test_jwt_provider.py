"""Tests for JWT token creation and validation."""
import time
import uuid
import pytest
from unittest.mock import patch
from app.core.jwt_provider import (
    create_access_token, create_refresh_token, decode_token, validate_token_claims
)
from app.core.constants import TokenType
from app.core.exceptions import TokenExpiredError, TokenInvalidError, TokenTypeMismatchError

class TestJWTCreation:
    def test_create_access_token_returns_string(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_has_correct_type(self):
        token = create_access_token("user-123")
        payload = decode_token(token, TokenType.ACCESS)
        assert payload["type"] == TokenType.ACCESS.value

    def test_access_token_has_required_claims(self):
        token = create_access_token("user-123")
        payload = decode_token(token, TokenType.ACCESS)
        for claim in ["sub", "jti", "type", "iss", "aud", "exp", "iat"]:
            assert claim in payload

    def test_access_token_subject_matches(self):
        token = create_access_token("user-456")
        payload = decode_token(token, TokenType.ACCESS)
        assert payload["sub"] == "user-456"

    def test_access_token_additional_claims(self):
        token = create_access_token("user-789", additional_claims={"role": "admin"})
        payload = decode_token(token, TokenType.ACCESS)
        assert payload["role"] == "admin"

    def test_create_refresh_token_returns_tuple(self):
        token, jti = create_refresh_token("user-123")
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) == 36  # UUID

    def test_refresh_token_has_correct_type(self):
        token, _ = create_refresh_token("user-123")
        payload = decode_token(token, TokenType.REFRESH)
        assert payload["type"] == TokenType.REFRESH.value

    def test_jti_is_unique_per_token(self):
        _, jti1 = create_refresh_token("user-123")
        _, jti2 = create_refresh_token("user-123")
        assert jti1 != jti2

class TestJWTValidation:
    def test_wrong_token_type_raises(self):
        access_token = create_access_token("user-123")
        with pytest.raises(TokenTypeMismatchError) as exc:
            decode_token(access_token, TokenType.REFRESH)
        assert exc.value.code == "TOKEN_TYPE_MISMATCH"

    def test_invalid_token_raises(self):
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.token", TokenType.ACCESS)

    def test_tampered_token_raises(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "AAAAA"
        with pytest.raises(TokenInvalidError):
            decode_token(tampered, TokenType.ACCESS)

    def test_expired_token_raises(self):
        import jwt
        from datetime import timedelta
        from app.core.config import settings
        import time

        payload = {
            "sub": "user-123",
            "jti": str(uuid.uuid4()),
            "type": TokenType.ACCESS.value,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(time.time()) - 1000,
            "nbf": int(time.time()) - 1000,
            "exp": int(time.time()) - 1,  # already expired
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        with pytest.raises(TokenExpiredError):
            decode_token(expired_token, TokenType.ACCESS)
