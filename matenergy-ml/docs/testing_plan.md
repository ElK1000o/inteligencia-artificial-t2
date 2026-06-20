# Testing Plan — MatEnergy-ML

## 1. Testing Philosophy

- Tests verify behavior, not implementation.
- Every public use case and API endpoint must have at least one test.
- Security controls must be tested adversarially (not just happy path).
- ML tests verify scientific correctness: reproducibility, metric formulas, OOD detection.
- Tests run without external network access; all DB tests use SQLite in-memory.

---

## 2. Test Architecture

```
backend/app/tests/
├── conftest.py              — shared fixtures (SQLite engine, sample data)
├── unit/                    — pure domain / service tests (no I/O)
├── integration/             — cross-layer tests (use cases, routes)
├── security/                — adversarial / boundary tests
└── ml/                      — ML pipeline and evaluation tests
```

---

## 3. Unit Tests (20 cases)

| # | File | What it tests | Acceptance Criterion |
|---|---|---|---|
| U01 | `test_formula_parsing.py` | Valid/invalid chemical formula parsing | All valid formulas accepted; `=CMD()`, empty, lowercase rejected |
| U02 | `test_formula_parsing.py` | Property range validation | Values outside physical bounds raise `InvalidTargetValueError` |
| U03 | `test_stability_service.py` | Stability classification thresholds | 0.00 → stable; 0.08 → unstable; 0.04 → borderline |
| U04 | `test_jwt_provider.py` | JWT creation and decode | Token decodes correctly with expected claims |
| U05 | `test_jwt_provider.py` | JWT expiration | Expired token raises `TokenExpiredError` |
| U06 | `test_jwt_provider.py` | JWT wrong type | Access token used as refresh token → error |
| U07 | `test_jwt_provider.py` | JWT revocation | Revoked jti is rejected |
| U08 | `test_password_hasher.py` | Argon2 hash + verify | `verify_password(hash, plaintext)` returns True |
| U09 | `test_password_hasher.py` | Wrong password rejected | `verify_password(hash, wrong)` returns False |
| U10 | `test_rbac.py` | RBAC role checks | Viewer cannot call researcher-only functions |
| U11 | `test_file_upload_validator.py` | Extension allowlist | `.exe`, `.py`, `.php` rejected; `.csv` accepted |
| U12 | `test_file_upload_validator.py` | Path traversal in filename | `../etc/passwd` sanitized |
| U13 | `test_csv_loader.py` | Valid CSV parsing | 5-row CSV fully loaded |
| U14 | `test_csv_loader.py` | Formula injection detected | `=CMD()` cells rejected as invalid formula |
| U15 | `test_ml_preprocessing.py` | Constant feature removal | Zero-variance column removed |
| U16 | `test_ml_preprocessing.py` | Train/test split size | 80/20 split produces correct sample counts |
| U17 | `test_candidate_scoring.py` | Score formula | LiFePO4 scores higher than toxic material under same conditions |
| U18 | `test_candidate_scoring.py` | OOD penalty | OOD flag reduces score |
| U19 | `test_artifact_integrity.py` | SHA-256 computation | Known bytes produce expected hash |
| U20 | `test_descriptors.py` | Compositional descriptors | LiFePO4 produces `frac_Li > 0` and `n_elements = 4` |

**Tool**: pytest  
**DB**: None (pure Python)  
**Run**: `pytest backend/app/tests/unit/`

---

## 4. Integration Tests (12 cases)

| # | File | What it tests | Acceptance Criterion |
|---|---|---|---|
| I01 | `test_auth_flow.py` | Login with wrong credentials | Returns 401 with generic message |
| I02 | `test_auth_flow.py` | Protected endpoint without token | Returns 401 |
| I03 | `test_auth_flow.py` | Expired JWT token | Returns 401 |
| I04 | `test_dataset_upload.py` | CSV with wrong extension | Upload rejected |
| I05 | `test_dataset_upload.py` | Path traversal filename | Upload rejected |
| I06 | `test_material_import.py` | Valid CSV loaded | 5 rows successfully parsed |
| I07 | `test_descriptor_generation.py` | Compositional descriptors for LiFePO4 | Dict with `frac_Li > 0` |
| I08 | `test_model_training.py` | Ridge + RF train and evaluate | MAE < 1.0; R² > -inf |
| I09 | `test_model_training.py` | Training reproducibility | Two runs produce identical predictions |
| I10 | `test_model_evaluation.py` | Hash mismatch → ArtifactIntegrityError | Exception raised with MISMATCH code |
| I11 | `test_report_export.py` | Ranking CSV contains all items | Formula names present in CSV |
| I12 | `test_db_repositories.py` | User CRUD in SQLite | Create, read, update round-trip |
| I13 | `test_ranking_endpoint.py` | Candidate scoring | LiFePO4 scores ≥ 0.5 for Li-ion batteries |
| I14 | `test_prediction_endpoint.py` | OOD detection | Extreme outlier flagged as OOD |
| I15 | `test_rbac_endpoints.py` | Viewer cannot train model | Returns 403 |
| I16 | `test_dashboard_endpoint.py` | Health endpoint accessible | Returns 200 without auth |

**Tool**: pytest + FastAPI TestClient  
**DB**: SQLite in-memory (via conftest.py)  
**Run**: `pytest backend/app/tests/integration/`

---

## 5. Security Tests (18 cases)

| # | File | What it tests | Acceptance Criterion |
|---|---|---|---|
| S01 | `test_security.py` | Path traversal in filename | `../etc/passwd` → no `..` in sanitized result |
| S02 | `test_security.py` | SQL injection attempt | Repository uses ORM; no raw string concatenation |
| S03 | `test_security.py` | CSV formula injection | `=CMD()` cells rejected as invalid formula |
| S04 | `test_security.py` | Ranking weights validation | Weights outside [0,1] raise validation error |
| S05 | `test_rbac_endpoints.py` | Unauthenticated access | All data endpoints return 401 |
| S06 | `test_rbac_endpoints.py` | Wrong auth scheme | `Basic` header returns 401 |
| S07 | `test_rbac_endpoints.py` | Viewer cannot train | Returns 403 |
| S08 | `test_rbac_endpoints.py` | Researcher cannot list users | Returns 403 |
| S09 | `test_auth_flow.py` | Invalid JWT signature | Returns 401 |
| S10 | `test_auth_flow.py` | Expired JWT | Returns 401 |
| S11 | `test_auth_flow.py` | Generic login error message | Error does not mention email or password |
| S12 | `test_dataset_upload.py` | Oversized file rejected | 60 MB file blocked |
| S13 | `test_dataset_upload.py` | Wrong MIME type | Non-CSV MIME rejected |
| S14 | `test_model_evaluation.py` | Missing file → integrity error | ArtifactIntegrityError raised |
| S15 | `test_model_evaluation.py` | Hash mismatch → integrity error | ArtifactIntegrityError raised |
| S16 | `test_security.py` | Excessive pagination blocked | limit > 500 capped or rejected |
| S17 | `test_auth_flow.py` | Empty bearer token | Returns 401 |
| S18 | `test_rbac_endpoints.py` | Admin can access admin endpoints | Returns 200 |

**Tool**: pytest  
**Run**: `pytest backend/app/tests/security/`

---

## 6. ML Tests (8 cases)

| # | File | What it tests | Acceptance Criterion |
|---|---|---|---|
| M01 | `test_ml_pipeline.py` | Reproducibility with seed=42 | Two Ridge models produce identical predictions |
| M02 | `test_ml_preprocessing.py` | Constant feature detection | Zero-variance column removed from X |
| M03 | `test_material_import.py` | Missing target → row rejected | Rows with null target not included in valid_rows |
| M04 | `test_model_training.py` | Insufficient dataset | < 20 samples → InsufficientDataError (or equivalent) |
| M05 | `test_prediction_endpoint.py` | OOD prediction warning | Values 100× outside training range flagged |
| M06 | `test_model_training.py` | Regression metrics correct | MAE ≥ 0; R² ≤ 1 |
| M07 | `test_model_training.py` | Classification metrics correct | Accuracy in [0, 1]; F1 in [0, 1] |
| M08 | `test_model_training.py` | Leakage detection | Target column as feature raises TargetLeakageError |

**Tool**: pytest + scikit-learn  
**Run**: `pytest backend/app/tests/ml/`

---

## 7. Running the Full Suite

```bash
# From the backend directory, with dependencies installed:
pip install pytest pytest-asyncio httpx[test]

# All tests:
pytest backend/app/tests/ -v

# With coverage:
pytest backend/app/tests/ --cov=app --cov-report=term-missing

# Only security tests:
pytest backend/app/tests/security/ -v
```

---

## 8. CI Recommendations

- Run unit + security tests on every pull request.
- Run full integration tests before merging to main.
- Pin all test dependencies in `requirements.txt`.
- Store coverage reports as CI artifacts.
- Fail CI if any test in `tests/security/` fails.
