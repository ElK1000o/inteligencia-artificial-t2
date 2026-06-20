# User Manual — MatEnergy-ML

## 1. Getting Started

### 1.1 Prerequisites
- Docker and Docker Compose installed
- A Materials Project API key (optional, for live data fetching)
- A modern web browser (Chrome 90+, Firefox 88+, Edge 90+)

### 1.2 First Launch

```bash
# 1. Copy environment template
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET_KEY

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Create admin user and roles
docker compose exec backend python scripts/seed_db.py

# 5. Import demo dataset
docker compose exec backend python scripts/import_demo_data.py

# 6. Generate descriptors for demo data
docker compose exec backend python scripts/generate_descriptors.py

# 7. Train baseline models
docker compose exec backend python scripts/train_baseline_models.py

# 8. Open the application
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs (development only)
```

### 1.3 Default Login
```
Email:    admin@matenergy.local
Password: (set during seed_db.py execution)
```

> **WARNING**: Change the admin password immediately after first login.

---

## 2. Workflows

### 2.1 Workflow A: Load and Validate a Dataset

1. Navigate to **Datasets** in the sidebar.
2. Click **Upload Dataset**.
3. Select a CSV file (max 50 MB).
4. Enter a name and optional description.
5. Click **Upload**.
6. Once uploaded, click the **View** button next to the dataset.
7. The Validation Report page shows:
   - Total / valid / rejected row counts
   - Row distribution chart
   - Specific validation errors per row
   - Warnings about data quality

**CSV format requirements**:
```csv
formula,energy_above_hull,formation_energy_per_atom,band_gap,is_stable
LiFePO4,0.000,-3.181,3.71,True
Li2O,0.000,-1.991,4.91,True
```
- `formula` column is required.
- At least one of the target columns is needed for training.
- `is_stable` accepts True/False/1/0.

> **Scientific note**: Ensure your CSV contains DFT-computed values, not experimental values, for consistency with the training data.

---

### 2.2 Workflow B: Generate Descriptors

1. Navigate to **Descriptors** in the sidebar.
2. Select the dataset you uploaded.
3. Choose descriptor type:
   - **Compositional**: Uses chemical formula only (always available).
   - **Compositional + Structural**: Also uses crystal structure data (requires `space_group`, `lattice_a/b/c` columns).
4. Click **Generate Descriptors**.
5. Wait for the job to complete (typically < 30 seconds for 200 materials).
6. The descriptor set will appear with the number of features computed.

> **Limitation**: If a formula cannot be parsed by pymatgen, that material will be skipped and counted in the error report.

---

### 2.3 Workflow C: Train a Model

1. Navigate to **Models** in the sidebar.
2. Click **Train New Model**.
3. Select:
   - **Model Type**: `random_forest_regressor` recommended for first experiments.
   - **Task Type**: `regression` for continuous properties; `classification` for `is_stable`.
   - **Target Property**: e.g., `energy_above_hull`.
   - **Dataset**: The dataset you validated.
   - **Descriptor Set**: The descriptor set you generated.
4. Click **Start Training**.
5. The model status will update to `completed` when done.
6. Click **Metrics** to view training/test MAE, R², and other performance metrics.
7. Click **Activate** to mark the model as the active predictor for its target property.

> **Scientific note**: Random Forest cannot extrapolate beyond the training range. Predictions for materials outside the training chemical space should be treated with caution.

---

### 2.4 Workflow D: Run Predictions

> **Prerequisite**: At least one model must be activated for the target property.

1. Navigate to **Predictions** in the sidebar.
2. Select the active model and target dataset.
3. Click **Run Batch Prediction**.
4. Results will show:
   - Predicted value (regression) or class label (classification)
   - Out-of-domain (OOD) flag — highlighted in red if the material is outside the training domain
   - Confidence score (not calibrated — treat as relative, not absolute probability)

---

### 2.5 Workflow E: Generate Candidate Rankings

1. Navigate to **Ranking** in the sidebar.
2. Click **Create Ranking**.
3. Configure:
   - **Name**: A descriptive label for this ranking run.
   - **Application Target**: e.g., `li_ion_batteries`, `solid_electrolytes`.
   - **Dataset**: Dataset to rank.
4. Click **Generate**.
5. Results show each material with:
   - **Rank position** (1 = best)
   - **Candidate Score** (0–1)
   - **Priority Label**: High / Moderate / Low / Not Recommended / Insufficient Evidence
   - **Reasoning**: Rule-based explanation (never AI-generated)
6. Click **Export CSV** to download the ranking.

> **Scientific note**: The ranking score combines multiple factors. High-priority candidates still require experimental validation. See `docs/limitations.md` for full caveats.

---

### 2.6 Workflow F: Export Reports

1. Navigate to **Reports** in the sidebar.
2. Click **Generate Report** and select report type:
   - **Ranking Report** (CSV): Full candidate table with scores
   - **Model Metrics** (Markdown): Performance table for a model
   - **Dataset Summary** (Markdown): Dataset statistics and validation info
   - **Platform Summary** (Markdown): Aggregate counts
3. Download the generated file.

---

## 3. User Roles

| Role | Permissions |
|---|---|
| `admin` | Full access: manage users, all datasets, all models, admin page |
| `researcher` | Upload datasets, train models, run predictions, generate rankings |
| `viewer` | Read-only access to materials, models, rankings, reports |

---

## 4. Scientific Warnings

The platform displays scientific limitation warnings in three places:

1. **Prediction results**: OOD flag and `is_calibrated=False` indicator.
2. **Ranking reasoning**: Rule-based explanation explicitly states what is NOT validated.
3. **Reports**: Markdown reports include a "Limitations" section.

These warnings are intentional. The platform is a **screening tool**, not a substitute for:
- Experimental synthesis and characterization
- Electrochemical testing
- Finite-temperature DFT or molecular dynamics simulations

---

## 5. Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| Login fails | Wrong password or account locked | Wait 15 min or reset password via admin |
| CSV upload rejected | Wrong extension or file too large | Use `.csv`, max 50 MB |
| Descriptor generation error | Invalid formula in dataset | Check validation report for rejected rows |
| Training fails with "no descriptor vectors" | Descriptors not generated yet | Run Workflow B first |
| Model shows "running" indefinitely | Backend crash | Check `docker compose logs backend` |
| OOD warnings on all predictions | Training set too small | Upload more diverse materials |
