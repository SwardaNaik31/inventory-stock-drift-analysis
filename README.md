# Local Inventory Stock Drift Analysis with MLflow

> **CRITICAL PRIVACY DIRECTIVE**: 
> All inventory datasets, business metrics, and experiment artifacts in this repository **must remain strictly local**. No confidential data is ever uploaded to GitHub, cloud storage, external APIs, or remote MLflow servers.

---

## 1. Project Architecture & Privacy Guarantee

This project monitors and detects statistical distribution drift in warehouse inventory stock levels between a historical reference baseline and current operational data using the Kolmogorov-Smirnov (KS) two-sample test.

```
                    +------------------------------------------+
                    |           LOCAL WORKSTATION              |
                    |                                          |
                    |  +--------------------+                  |
                    |  |  data/private/     | (Never tracked)  |
                    |  |  *.xlsx, *.csv     |                  |
                    |  +---------+----------+                  |
                    |            |                             |
                    |            v                             |
                    |  +--------------------+                  |
                    |  | src/detect_drift.py|                  |
                    |  +---------+----------+                  |
                    |            |                             |
                    |    +-------+--------+                    |
                    |    |                |                    |
                    |    v                v                    |
                    | +----------+  +------------+             |
                    | | reports/ |  |  mlruns/   |             |
                    | |  plots/  |  |  (Local)   |             |
                    | +----------+  +-----+------+             |
                    |                     |                    |
                    |                     v                    |
                    |            +-----------------+           |
                    |            | Local MLflow UI |           |
                    |            | 127.0.0.1:5000  |           |
                    |            +-----------------+           |
                    +------------------------------------------+
```

### Privacy Guarantees:
1. **Zero Cloud Exfiltration**: All data loading, cleaning, KS-testing, plot rendering, and artifact storage happen strictly on your local machine.
2. **Offline MLflow Tracking**: MLflow is configured with local file-based tracking (`file:./mlruns`). Network telemetry is permanently disabled (`MLFLOW_ENABLE_TELEMETRY=false`).
3. **Loopback UI Binding**: The MLflow tracking dashboard is bound strictly to `127.0.0.1:5000` (loopback only), never exposed to external networks.
4. **Git Isolation**: Confidential directories (`data/private/`, `mlruns/`, `reports/plots/`, raw CSVs/Excels) are excluded by `.gitignore`.

---

## 2. Directory Layout

```
inventory-stock-drift-analysis/
├── .gitignore                      # Strict Git exclusion rules
├── README.md                       # Repository guide & privacy protocols
├── requirements.txt                # Local dependencies (mlflow, scipy, etc.)
│
├── data/
│   ├── private/                    # [LOCAL-ONLY] Store confidential Excel/CSV files here
│   │   └── README_LOCAL_ONLY.txt
│   ├── synthetic_demo_reference.csv# [PUBLIC SAFE] Synthetic demo baseline
│   └── synthetic_demo_current.csv  # [PUBLIC SAFE] Synthetic demo current stock
│
├── notebooks/
│   └── drift_analysis_template.ipynb # Clean notebook template (ZERO output cells)
│
├── reports/
│   ├── report_template.md          # Public-safe methodology & schema template
│   ├── README.md                   # Privacy instructions for generated outputs
│   ├── drift_summary.csv           # [LOCAL-ONLY] Generated drift metrics
│   ├── drift_summary.json          # [LOCAL-ONLY] Generated drift metrics in JSON
│   └── plots/                      # [LOCAL-ONLY] Feature comparison histograms
│       └── *.png
│
├── screenshots/
│   └── README.md                   # Guidance (never commit screenshots with private data)
│
└── src/
    ├── detect_drift.py             # Main drift detection & local MLflow logging
    ├── generate_synthetic_data.py  # Generates realistic synthetic demo data
    └── verify_privacy.py           # Pre-commit privacy audit verification tool
```

---

## 3. Quickstart & Installation

### Step 1: Environment Setup
Using PowerShell on Windows:
```powershell
# Create virtual environment if not already present
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install required dependencies
python -m pip install -r requirements.txt
```

---

## 4. How to Run Drift Analysis

### Option A: Using Your Private Inventory Excel Files (Recommended)
1. Place your private inventory Excel workbooks into `data/private/`:
   - `data/private/reference.xlsx` (Baseline historical inventory)
   - `data/private/current.xlsx` (Current operational inventory)
2. Run the detection script:
```powershell
python src/detect_drift.py --reference data/private/reference.xlsx --current data/private/current.xlsx
```
*Note: The script also accepts `.xls`, `.xlsm`, and `.csv` files. You can specify Excel sheets using `--ref-sheet` and `--cur-sheet`.*

### Option B: Using Synthetic Demonstration Data
If you wish to test or demonstrate the pipeline without touching real data:
```powershell
# 1. Generate synthetic demonstration datasets
python src/generate_synthetic_data.py

# 2. Run drift detection against synthetic datasets
python src/detect_drift.py --reference data/synthetic_demo_reference.csv --current data/synthetic_demo_current.csv
```

---

## 5. Viewing Experiment Tracking in Local MLflow

All runs, parameters, metrics (KS statistics, p-values), and distribution comparison artifacts are logged into the local `./mlruns` directory in standard MLflow format.

### Option 1: Standalone Local Viewer (No external packages needed)
Run the built-in offline viewer using Python's standard library:
```powershell
python src/view_mlflow_local.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Option 2: Official MLflow UI (Requires `pip install mlflow`)
If you have the `mlflow` package installed:
```powershell
mlflow ui --host 127.0.0.1 --port 5000
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
- Bound strictly to `127.0.0.1` (localhost loopback only).
- Zero communication with any remote MLflow tracking server.
- All artifact downloads and metric comparisons remain on disk.

---

## 6. Pre-Commit Privacy Verification

Before executing any Git operations, run the automated privacy audit tool:
```powershell
python src/verify_privacy.py
```
This tool performs 3 automated checks:
1. **Rule Validation**: Ensures all mandatory exclusion patterns exist in `.gitignore`.
2. **Staging Inspection**: Checks `git status --porcelain` to verify that no `.xlsx`, `.xls`, `.xlsm`, private `.csv`, `.env`, or `mlruns` files are staged.
3. **Ignore Simulation**: Tests `git check-ignore` against sensitive test paths.

---

## 7. What is Safe vs Forbidden for GitHub

| Category | Allowed for Git Commit | Strictly Forbidden from Git Commit |
| :--- | :--- | :--- |
| **Source Code** | `src/*.py`, `requirements.txt` | Any hardcoded confidential constants/paths |
| **Datasets** | `data/synthetic_demo_*.csv` | `data/private/*`, `*.xlsx`, `*.xls`, real CSVs |
| **Reports** | `reports/report_template.md`, `README.md` | `reports/drift_summary.csv`, `reports/plots/*.png` |
| **Notebooks** | `notebooks/drift_analysis_template.ipynb` (clean outputs) | Notebooks with cached execution cells containing real data |
| **Experiments**| None | `mlruns/`, `mlartifacts/`, `*.db`, SQLite files |
| **Screenshots**| Generic demo screenshots (synthetic data only) | Any screenshots showing actual company stock/SKUs |

---

## 8. Remediation: Removing Committed Files from Git History

> [!WARNING]
> Simply deleting a private file in a new commit (`git rm file.xlsx && git commit`) does **not** remove it from Git history. Previous copies remain accessible in past commit snapshots.

If a sensitive file was previously committed, completely purge it from git history using one of the following methods:

### Method 1: Using `git-filter-repo` (Recommended)
```powershell
pip install git-filter-repo
git filter-repo --path "data/private/" --invert-paths
```

### Method 2: Using BFG Repo-Cleaner
```powershell
# Delete all files larger than 1MB or matching private file patterns
java -jar bfg.jar --delete-files "*.xlsx" my-repo.git
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

### Method 3: If Only Staged (Not Yet Committed)
```powershell
# Unstage private files immediately
git restore --staged <path_to_file>
```
