"""Tests for Argon2 password hashing."""
import pytest
from app.core.password_hasher import hash_password, verify_password, needs_rehash

class TestPasswordHashing:
    def test_hash_returns_string(self):
        hashed = hash_password("TestPassword123!")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_different_from_plaintext(self):
        pwd = "TestPassword123!"
        assert hash_password(pwd) != pwd

    def test_two_hashes_of_same_password_differ(self):
        pwd = "TestPassword123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2  # Argon2 uses random salt

    def test_verify_correct_password(self):
        pwd = "MySecurePassword2024!"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectPassword!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_string_fails(self):
        hashed = hash_password("SomePassword!")
        assert verify_password("", hashed) is False

    def test_verify_never_raises(self):
        # Should return False, not raise
        assert verify_password("test", "not_a_valid_hash") is False

    def test_needs_rehash_returns_bool(self):
        hashed = hash_password("TestPassword!")
        result = needs_rehash(hashed)
        assert isinstance(result, bool)
