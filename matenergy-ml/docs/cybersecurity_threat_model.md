# Cybersecurity Threat Model — MatEnergy-ML

## Overview

This document enumerates security threats specific to the MatEnergy-ML platform,
following a structured vulnerability / scenario / impact / likelihood / mitigation
format. The platform handles scientific data, ML models, and user credentials —
each of which presents distinct attack surfaces.

---

## 1. Authentication Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| A1 | Weak password hashing | Attacker obtains DB dump; bcrypt-weak hashes cracked offline | Account takeover | Medium | Argon2id with m=65536, t=3, p=4 | `core/password_hasher.py` | `test_password_hasher.py` |
| A2 | Brute force login | Automated credential stuffing against /auth/login | Account takeover | High | MAX_LOGIN_ATTEMPTS=5, lockout 15 min | `api/v1/auth_routes.py` | `test_security.py::brute_force` |
| A3 | Long-lived JWT | Stolen access token used indefinitely | Unauthorized API access | Medium | ACCESS_TOKEN_EXPIRE_MINUTES=15 | `core/jwt_provider.py` | `test_jwt_provider.py::test_expiry` |
| A4 | Refresh token reuse | Attacker reuses revoked refresh token | Session hijack | High | Rotative refresh + jti revocation table | `api/v1/auth_routes.py` | `test_jwt_provider.py::test_revocation` |
| A5 | Account enumeration | Distinguish "wrong password" vs "user not found" | Targeted attacks | Medium | Generic "Invalid credentials" response | `api/v1/auth_routes.py` | `test_auth_flow.py::test_generic_error` |
| A6 | Token type confusion | Use refresh token where access token expected | Privilege escalation | Low | `token_type` claim validated in `decode_token()` | `core/jwt_provider.py` | `test_jwt_provider.py::test_wrong_type` |
| A7 | Missing nbf/iss/aud | Token accepted outside intended scope | Cross-service replay | Low | All standard claims enforced | `core/jwt_provider.py` | `test_jwt_provider.py::test_claims` |

---

## 2. Authorization Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| B1 | Broken object-level auth (IDOR) | User accesses dataset belonging to another user | Data leak | Medium | Ownership check in dataset routes | `api/v1/dataset_routes.py` | `test_rbac_endpoints.py` |
| B2 | Horizontal privilege escalation | Researcher calls admin-only endpoint | Unauthorized admin action | Medium | `require_roles()` dependency | `core/security.py` | `test_rbac_endpoints.py::test_viewer_cannot_train` |
| B3 | Vertical privilege escalation | Viewer modifies is_active on their own account | Unauthorized re-activation | Low | Only admins can change is_active | `api/v1/user_routes.py` | `test_rbac_endpoints.py` |
| B4 | Missing auth on endpoints | Unauthenticated access to material data | Data leak | High | `get_current_user_payload` on all routes | All route files | `test_rbac_endpoints.py::test_unauthenticated` |

---

## 3. File Upload Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| C1 | Path traversal via filename | Upload `../../etc/passwd` as filename | Arbitrary file overwrite | High | UUID-based stored paths; original name never used as path | `api/v1/dataset_routes.py` | `test_security.py::test_path_traversal` |
| C2 | CSV formula injection | `=CMD('...')` in formula cell triggers Excel macro | Client-side execution | Medium | All CSV exports use `csv.QUOTE_ALL` + prefix injection characters | `use_cases/export_dataset_use_case.py` | `test_security.py::test_csv_injection` |
| C3 | MIME spoofing | Rename `shell.php` to `data.csv` | Server-side execution | High | Extension allowlist + MIME check + no execution of uploads | `api/v1/dataset_routes.py` | `test_dataset_upload.py::test_wrong_extension` |
| C4 | Oversized upload | 500 MB CSV causes OOM or disk exhaustion | DoS | Medium | MAX_UPLOAD_SIZE_MB=50 enforced before reading body | `api/v1/dataset_routes.py` | `test_dataset_upload.py::test_oversized` |
| C5 | Stored XSS via filename | Filename reflected in UI without escaping | XSS attack | Medium | Filename sanitized server-side; stored name is UUID | `api/v1/dataset_routes.py` | `test_security.py::test_xss_filename` |
| C6 | Invalid UTF-8 encoding | Non-UTF-8 content causes parser crash | DoS | Low | `errors="replace"` in CSV decode | `infrastructure/materials/csv_loader.py` | `test_csv_loader.py` |
| C7 | Empty file upload | Zero-byte file accepted, causes null-pointer errors | Crash | Low | Empty file check before processing | `api/v1/dataset_routes.py` | `test_dataset_upload.py::test_empty` |

---

## 4. API Security Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| D1 | SQL injection | Inject SQL via formula parameter in search | Data exfiltration / corruption | Medium | SQLAlchemy ORM with parameterized queries only | All repositories | `test_security.py::test_sql_injection` |
| D2 | Mass assignment | POST body with extra fields bypasses validation | Unauthorized data change | Medium | Pydantic schemas with strict field definitions | All `schemas/` files | - |
| D3 | Verbose error leakage | Stack traces returned to client reveal internals | Recon | Medium | Global exception handler returns generic 500 | `core/error_handlers.py` | - |
| D4 | Unbounded query | `?limit=1000000` causes DB overload | DoS | Low | `limit` capped at max 500 in all paginated endpoints | All list routes | - |
| D5 | Insecure CORS | Any origin allowed, enabling CSRF | CSRF on authenticated endpoints | Medium | `BACKEND_CORS_ORIGINS` restricted to known frontends | `main.py` | - |
| D6 | Excessive data exposure | List endpoint returns full user objects with hashes | Credential leak | Low | `UserProfileResponse` excludes `hashed_password` | `api/v1/user_routes.py` | - |

---

## 5. ML Security Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| E1 | Data poisoning | Attacker uploads CSV with crafted outliers to skew model | Biased predictions | Medium | Validation ranges; outlier detection; hash tracking | `csv_loader.py`, `use_cases/validate_materials_use_case.py` | `test_ml_pipeline.py` |
| E2 | Target leakage | energy_above_hull used as feature for itself | Artificially perfect metrics | Medium | `check_for_leakage()` before training | `infrastructure/ml/preprocessing.py` | `test_model_training.py::test_leakage` |
| E3 | Artifact tampering | Joblib file replaced on disk with malicious model | Arbitrary code execution on load | Critical | SHA-256 verification before load; load only from registry | `use_cases/verify_model_artifact_use_case.py` | `test_model_evaluation.py::test_hash_mismatch` |
| E4 | Unsafe deserialization | Load untrusted pickle/joblib from external source | RCE | Critical | Only load artifacts from internal registry with verified hash | `predictor.py`, `evaluate_model_use_case.py` | `test_model_evaluation.py` |
| E5 | Uncalibrated confidence | Confidence=0.99 reported without calibration | False certainty in decisions | Medium | `is_calibrated=False` flag on all predictions | `prediction_models.py` | `test_ml_pipeline.py::test_calibration` |
| E6 | Out-of-domain silent failure | Prediction for exotic compound shown without warning | Misleading screening result | Medium | OOD detection via range-check; `is_out_of_domain` flag | `infrastructure/ml/predictor.py` | `test_prediction_endpoint.py::test_ood` |
| E7 | Train/test contamination | Duplicate materials in train and test sets | Overfitted metric reporting | Medium | Duplicate check before split | `infrastructure/ml/preprocessing.py` | `test_model_training.py` |

---

## 6. Infrastructure Threats

| # | Vulnerability | Attack Scenario | Impact | Likelihood | Mitigation | Code Location | Test |
|---|---|---|---|---|---|---|---|
| F1 | Secrets in repository | API keys committed to git | Credential exposure | High | `.env.example` with placeholders; real `.env` in `.gitignore` | `.env.example`, `.gitignore` | - |
| F2 | Debug mode in production | `/docs` exposed; stack traces visible | Recon / info leak | Medium | `docs_url=None` in production; `ENVIRONMENT=production` check | `main.py` | - |
| F3 | Container running as root | Compromised container has full host access | Container escape | Medium | `user: "1001:1001"` in docker-compose; non-root Dockerfile | `Dockerfile`, `docker-compose.yml` | - |
| F4 | No resource limits | Runaway ML training exhausts CPU/RAM | DoS | Medium | `deploy.resources.limits` in docker-compose | `docker-compose.yml` | - |
| F5 | Insecure backup | DB backup readable by all users | Data leak | Low | Document: backup files should use 600 permissions and encryption | `docs/deployment_guide.md` | - |
| F6 | Missing log rotation | Logs grow unbounded, fill disk | DoS | Low | structlog to stdout; container log rotation via Docker daemon | `core/logging_config.py` | - |

---

## Security Contact

For vulnerabilities in this academic platform, contact the thesis author.
This is a research system — do not deploy in production without a full security audit.
