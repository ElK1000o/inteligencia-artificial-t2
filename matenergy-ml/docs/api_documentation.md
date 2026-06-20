# MatEnergy-ML API Documentation

**Base URL**: `http://localhost:8000/api/v1`  
**API Version**: v1  
**Authentication**: Bearer JWT (PyJWT, HS256)  
**Interactive docs**: `http://localhost:8000/docs` (development only)

---

## Authentication

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "researcher@institution.edu",
  "password": "YourPassword123!"
}
```

Response:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 900
}
```

Include the access token in all subsequent requests:
```http
Authorization: Bearer <access_token>
```

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "<refresh_jwt>" }
```

Refresh tokens rotate on each use — store the new token returned.

### Logout

```http
POST /auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{ "refresh_token": "<refresh_jwt>" }
```

### Get Current User

```http
GET /auth/me
Authorization: Bearer <access_token>
```

---

## Error Format

All errors return:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "recommended_action": "What to do next"
}
```

Common status codes:
- `401` — Invalid/expired token
- `403` — Insufficient permissions
- `404` — Resource not found
- `409` — Conflict (duplicate)
- `413` — File too large
- `422` — Validation error
- `500` — Internal error (no details leaked)

---

## Datasets

### Upload Dataset

```http
POST /datasets/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<csv_file>
name=My Dataset
description=Optional description
allow_partial_import=false
```

- CSV must be UTF-8, have a `formula` column, be ≤ 50 MB
- Duplicate datasets (same SHA-256) are rejected with `409`
- Files stored with UUID-based names (never original filename)

### List Datasets

```http
GET /datasets?skip=0&limit=50
Authorization: Bearer <token>
```

### Get Dataset

```http
GET /datasets/{dataset_id}
```

### Validation Report

```http
GET /datasets/{dataset_id}/validation-report
```

### Rejected Rows

```http
GET /datasets/{dataset_id}/rejected-rows?skip=0&limit=100
```

---

## Materials

### List Materials

```http
GET /materials?dataset_id=<uuid>&skip=0&limit=50
GET /materials?formula=LiFePO4&skip=0&limit=50
GET /materials?chemsys=Fe-Li-O&skip=0&limit=50
```

### Get Material Detail

```http
GET /materials/{material_id}
```

Returns formula, elements, composition fractions, and all DFT properties.

### Dataset Stats

```http
GET /materials/dataset/{dataset_id}/stats
```

Returns element distribution and per-property statistics (mean, min, max, std).

---

## Descriptors

### Generate Descriptors

```http
POST /descriptors/generate
Authorization: Bearer <token>  # requires researcher or admin role
Content-Type: application/json

{
  "dataset_id": "<uuid>",
  "include_structural": false,
  "name": "default"
}
```

### List Descriptor Sets

```http
GET /descriptors/sets
```

---

## Models

### Train Model

```http
POST /models/train
Authorization: Bearer <token>  # requires researcher or admin role
Content-Type: application/json

{
  "model_type": "random_forest_regressor",
  "task_type": "regression",
  "target_property": "energy_above_hull",
  "dataset_id": "<uuid>",
  "descriptor_set_id": "<uuid>",
  "name": "RF energy_above_hull v1",
  "test_size": 0.2,
  "hyperparameters": {}
}
```

Available `model_type` values: `ridge_regression`, `random_forest_regressor`, `random_forest_classifier`, `gradient_boosting_regressor`, `gradient_boosting_classifier`, `mlp_regressor`, `mlp_classifier`, `logistic_regression`

### List Models

```http
GET /models
```

### Model Metrics

```http
GET /models/{model_id}/metrics
```

### Activate Model

```http
POST /models/{model_id}/activate
Authorization: Bearer <token>
```

---

## Rankings

### Create Ranking

```http
POST /rankings
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Li-ion Cathode Screening",
  "application_target": "li_ion_batteries",
  "dataset_id": "<uuid>",
  "weights": {
    "stability_weight": 0.30,
    "target_property_weight": 0.25,
    "energy_relevance_weight": 0.20,
    "abundance_weight": 0.10,
    "toxicity_penalty_weight": 0.05,
    "uncertainty_penalty_weight": 0.05,
    "out_of_domain_penalty_weight": 0.05
  }
}
```

### Get Ranking with Items

```http
GET /rankings/{ranking_id}
```

### Export Ranking as CSV

```http
GET /rankings/{ranking_id}/export
```

---

## Dashboard

```http
GET /dashboard/stats
Authorization: Bearer <token>
```

Returns 10 aggregated statistics including total materials, active models, stable candidates, and security event count.

---

## Pagination

All list endpoints use `skip` and `limit` parameters:
- Default limit: 50
- Maximum limit: 200 (higher values rejected with 422)
- Use `skip` for offset-based pagination

---

## DFT Jobs

The DFT job queue allows submitting local or HPC-bound atomistic simulations and tracking their status asynchronously. Jobs run in background daemon threads (local adapter) or produce ready-to-submit HPC scripts (SLURM adapter).

### Submit DFT Job

```http
POST /dft-jobs
Authorization: Bearer <token>  # requires researcher or admin role
Content-Type: application/json

{
  "formula": "LiFePO4",
  "structure_json": null,
  "calculation_type": "RELAX",
  "functional": "PBE",
  "encut": 520,
  "kpoints_density": 64,
  "hubbard_u": {},
  "adapter": "local",
  "job_name": "LiFePO4 relaxation"
}
```

Returns `202 Accepted`:
```json
{
  "job_id": "<uuid>",
  "status": "pending",
  "message": "Job submitted"
}
```

- `adapter`: `"local"` (ASE/EMT: real calculation for {Al,Cu,Ag,Au,Ni,Pd,Pt,Zn,Cd,Hg}; deterministic hash-seeded approximation for all other formulas) or `"slurm"` (generates VASP POSCAR/INCAR/KPOINTS + SLURM script; does not actually submit to HPC)
- `calculation_type`: `"ENERGY"` (single-point) or `"RELAX"` (geometry optimisation via BFGS)
- `structure_json`: optional pymatgen-compatible dict; if null, fetched from Materials Project by formula, or a fallback cubic structure is used
- `functional`, `encut`, `kpoints_density`, `hubbard_u`: VASP/SLURM parameters embedded in the SLURM adapter script; ignored by the local ASE adapter

### List DFT Jobs

```http
GET /dft-jobs?skip=0&limit=50
Authorization: Bearer <token>
```

Returns all jobs submitted by the authenticated user, newest first.

### Get DFT Job Status

```http
GET /dft-jobs/{job_id}
Authorization: Bearer <token>
```

Response:
```json
{
  "job_id": "<uuid>",
  "job_name": "LiFePO4 relaxation",
  "formula": "LiFePO4",
  "calculation_type": "RELAX",
  "adapter": "local",
  "status": "completed",
  "progress_pct": 100,
  "created_at": "2026-06-09T10:00:00Z",
  "started_at": "2026-06-09T10:00:05Z",
  "completed_at": "2026-06-09T10:00:12Z",
  "result": {
    "formation_energy_eV_per_atom": -2.83,
    "total_energy_eV": -45.32,
    "n_atoms": 28,
    "n_steps": 12,
    "converged": true,
    "method": "ASE-EMT",
    "note": "EMT calculator — metallic system"
  },
  "error_message": null
}
```

Job status lifecycle: `pending` → `running` → `completed` | `failed` | `cancelled`

### Cancel DFT Job

```http
DELETE /dft-jobs/{job_id}
Authorization: Bearer <token>
```

Returns `204 No Content`. Sets a `threading.Event` cancel flag; the background thread exits within 0.5 s.

### Ingest DFT Results into Material Properties

```http
POST /dft-jobs/{job_id}/ingest
Authorization: Bearer <token>
Content-Type: application/json

{ "material_id": "<uuid>" }
```

Persists the completed job's DFT results as `MaterialProperty` rows for the target material:
- `formation_energy` (eV/atom)
- `energy_above_hull` (eV/atom)
- `band_gap` (eV)
- `total_energy` (eV)

All rows are tagged with `data_source = "dft_local"` or `"dft_slurm"`. Duplicate property rows (same material + same property_name + same data_source) are skipped. Returns `400` if the job is not yet completed or the material_id is invalid.

### Get Generated Inputs (SLURM adapter only)

```http
GET /dft-jobs/{job_id}/inputs
Authorization: Bearer <token>
```

Returns the VASP input files and SLURM script generated for HPC submission:
```json
{
  "poscar": "...",
  "incar": "...",
  "kpoints": "...",
  "slurm_script": "#!/bin/bash\n#SBATCH --job-name=...\n...",
  "note": "SLURM stub — copy files to HPC and run sbatch manually"
}
```

Returns `400` if the job used the local adapter (no HPC inputs generated).

---

## Rate Limiting

API endpoints are protected by `slowapi` rate limiting. Repeated failed login attempts trigger temporary account lockout (default: 5 attempts → 15 minute lockout).
