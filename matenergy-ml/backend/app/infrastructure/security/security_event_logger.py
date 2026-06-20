"""
SecurityEventLogger for MatEnergy-ML.

Named-method wrapper around AuditLogger.log_security_event() that makes
security logging calls explicit, readable, and grep-friendly throughout
the codebase.

Each method maps one security scenario to a structured SecurityEvent row
with the appropriate severity level and event_type string.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.security.audit_logger import AuditLogger
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SecurityEventLogger:
    """
    Dedicated security event logger with named methods per scenario.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self._audit = AuditLogger(db)

    # ------------------------------------------------------------------
    # Authentication events
    # ------------------------------------------------------------------

    def log_failed_login(
        self,
        email: str,
        ip_address: Optional[str] = None,
        attempt_count: int = 1,
    ) -> None:
        self._audit.log_security_event(
            event_type="login_failure",
            severity="medium" if attempt_count < 3 else "high",
            description=f"Failed login attempt for '{email}' (attempt #{attempt_count})",
            ip_address=ip_address,
            metadata={"email_hint": email[:3] + "***", "attempt_count": attempt_count},
        )

    def log_account_locked(
        self,
        user_id: uuid.UUID,
        locked_until_iso: str,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="account_locked",
            severity="high",
            description="Account locked after repeated failed login attempts",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"locked_until": locked_until_iso},
        )

    def log_token_reuse(
        self,
        jti: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="token_reuse",
            severity="critical",
            description="Attempt to reuse a revoked or already-rotated refresh token",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"jti_hint": jti[:8] + "***"},
        )

    def log_invalid_token(
        self,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="invalid_token",
            severity="medium",
            description=f"Invalid JWT token presented: {reason}",
            ip_address=ip_address,
            metadata={"reason": reason},
        )

    # ------------------------------------------------------------------
    # File upload events
    # ------------------------------------------------------------------

    def log_suspicious_upload(
        self,
        filename: str,
        reason: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="suspicious_upload",
            severity="high",
            description=f"Suspicious file upload blocked: {reason}",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"filename_hint": filename[:20], "reason": reason},
        )

    def log_oversized_upload(
        self,
        size_mb: float,
        limit_mb: int,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="oversized_upload",
            severity="medium",
            description=f"File upload rejected: {size_mb:.1f}MB exceeds {limit_mb}MB limit",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"size_mb": size_mb, "limit_mb": limit_mb},
        )

    # ------------------------------------------------------------------
    # Authorization events
    # ------------------------------------------------------------------

    def log_unauthorized_access(
        self,
        endpoint: str,
        user_id: Optional[uuid.UUID] = None,
        required_role: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="unauthorized_access",
            severity="medium",
            description=f"Access denied to {endpoint}",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"endpoint": endpoint, "required_role": required_role},
        )

    def log_privilege_escalation_attempt(
        self,
        user_id: uuid.UUID,
        attempted_action: str,
        ip_address: Optional[str] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="privilege_escalation_attempt",
            severity="critical",
            description=f"Privilege escalation attempt: {attempted_action}",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"attempted_action": attempted_action},
        )

    # ------------------------------------------------------------------
    # ML / artifact events
    # ------------------------------------------------------------------

    def log_artifact_tamper_attempt(
        self,
        model_version_id: str,
        expected_hash_hint: str,
        found_hash_hint: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="artifact_integrity_failure",
            severity="critical",
            description=(
                f"Model artifact hash mismatch for version {model_version_id[:8]}. "
                "Possible tampering detected."
            ),
            user_id=user_id,
            metadata={
                "model_version_id": model_version_id,
                "expected_hash_hint": expected_hash_hint,
                "found_hash_hint": found_hash_hint,
            },
        )

    def log_untrusted_model_load_blocked(
        self,
        file_path: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> None:
        self._audit.log_security_event(
            event_type="untrusted_model_load_blocked",
            severity="high",
            description="Attempt to load a model artifact not registered in the registry",
            user_id=user_id,
            metadata={"file_path_hint": file_path[:30]},
        )
