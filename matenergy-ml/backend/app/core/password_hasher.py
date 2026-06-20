"""
Password hashing and verification using Argon2id via argon2-cffi.

Parameters chosen to meet OWASP Argon2id recommendations for interactive login
while remaining practical on typical CI/CD hardware:
  - time_cost=2      (2 iterations)
  - memory_cost=65536 (64 MiB)
  - parallelism=2    (2 threads)

The module exposes three functions:
  hash_password   — produce a new Argon2id hash
  verify_password — constant-time comparison; returns bool (never raises)
  needs_rehash    — returns True when the stored hash uses outdated parameters
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Module-level singleton; constructed once at import time.
# All three argon2-cffi parameters are set explicitly so changes to the
# argon2 library's own defaults do not silently alter security properties.
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65_536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password with Argon2id.

    Args:
        password: The user-supplied plain-text password.

    Returns:
        An Argon2id PHC-format hash string (includes algorithm, parameters, salt,
        and hash — everything needed for future verification).

    Raises:
        ValueError: If *password* is empty.
    """
    if not password:
        raise ValueError("Password must not be empty")
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored Argon2id hash.

    The verification is always constant-time from the caller's perspective;
    failures are caught and normalised to ``False`` instead of raising.

    Args:
        plain:   The plain-text password to check.
        hashed:  The stored Argon2id PHC hash string.

    Returns:
        True if the password matches, False otherwise.
    """
    if not plain or not hashed:
        return False
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """
    Check whether a stored hash should be upgraded.

    Returns True when the hash was produced with different (usually older /
    weaker) Argon2 parameters than the current ``_ph`` configuration.  Call
    this after a successful ``verify_password`` and, if True, rehash and
    persist the new hash.

    Args:
        hashed: The stored Argon2id PHC hash string.

    Returns:
        True if the hash parameters differ from the current configuration.
    """
    return _ph.check_needs_rehash(hashed)
