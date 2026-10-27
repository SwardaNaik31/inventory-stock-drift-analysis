"""
Local-Only Inventory Stock Drift Detection Pipeline
===================================================
CRITICAL PRIVACY GUARANTEE:
- All data loading, statistical testing, plotting, and experiment tracking
  run 100% locally on your computer.
- MLflow telemetry is disabled.
- Tracking store and artifacts are strictly local ('file:./mlruns').
- Zero data, column names, or metrics are transmitted to any remote API or cloud.
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# Auto-Bootstrap: Bridge to project .venv if invoked with system Python
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_VENV_SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if LOCAL_VENV_SITE.exists() and str(LOCAL_VENV_SITE) not in sys.path:
    sys.path.insert(0, str(LOCAL_VENV_SITE))

import math
import uuid
import time
import argparse
import numpy as np
import pandas as pd

# ==============================================================================
# 1. Enforce Local-Only MLflow Configuration & Telemetry Disablement
# ==============================================================================
os.environ["MLFLOW_ENABLE_TELEMETRY"] = "false"
os.environ["MLFLOW_DISABLE_TELEMETRY"] = "true"
os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "false"

LOCAL_MLFLOW_DIR = PROJECT_ROOT / "mlruns"
LOCAL_TRACKING_URI = LOCAL_MLFLOW_DIR.as_uri()

# Check for MLflow package
MLFLOW_AVAILABLE = False
try:
    import mlflow
    mlflow.set_tracking_uri(LOCAL_TRACKING_URI)
    # Security Guardrail: Verify tracking URI is strictly local
    current_tracking_uri = mlflow.get_tracking_uri()
    if not (current_tracking_uri.startswith("file:") or current_tracking_uri.startswith("sqlite:")):
        raise RuntimeError(
            f"[PRIVACY VIOLATION DETECTED] MLflow tracking URI '{current_tracking_uri}' is not local. "
            "Aborting execution immediately to prevent any cloud exfiltration."
        )
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

# Check for Scipy
SCIPY_AVAILABLE = False
try:
    from scipy.stats import ks_2samp as scipy_ks_2samp
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Check for Matplotlib
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ==============================================================================
# 2. Statistical Testing (Kolmogorov-Smirnov Two-Sample Test)
# ==============================================================================
def ks_two_sample_test(data1, data2):
    """
    Compute two-sample Kolmogorov-Smirnov test.
    Uses scipy.stats.ks_2samp if available, or pure-NumPy asymptotic calculation.
    """
    if SCIPY_AVAILABLE:
        res = scipy_ks_2samp(data1, data2)
        return float(res.statistic), float(res.pvalue)

    # Pure NumPy implementation of KS two-sample statistic and asymptotic p-value
    n1 = len(data1)
    n2 = len(data2)
    s1 = np.sort(data1)
    s2 = np.sort(data2)
    all_data = np.concatenate([s1, s2])
    
    cdf1 = np.searchsorted(s1, all_data, side="right") / n1
    cdf2 = np.searchsorted(s2, all_data, side="right") / n2
    d_stat = float(np.max(np.abs(cdf1 - cdf2)))

    # Asymptotic approximation for p-value using Kolmogorov distribution
    en = np.sqrt(n1 * n2 / (n1 + n2))
    lambda_val = (en + 0.12 + 0.11 / en) * d_stat
    if lambda_val <= 0:
        p_val = 1.0
    else:
        k = np.arange(1, 101)
        terms = 2.0 * ((-1) ** (k - 1)) * np.exp(-2.0 * (k ** 2) * (lambda_val ** 2))
        p_val = float(np.clip(np.sum(terms), 0.0, 1.0))

    return round(d_stat, 6), round(p_val, 6)


# ==============================================================================
# 3. Privacy-Safe Dataset Loading (Supports Excel .xlsx/.xls/.xlsm & CSV)
# ==============================================================================
def load_dataset(file_path: str, sheet_name=0) -> pd.DataFrame:
    """Load dataset locally from Excel or CSV format without external exposure."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset file not found at: {path}\n"
            "Please ensure your private inventory files are placed in 'data/private/' "
            "or generate demo data using 'python src/generate_synthetic_data.py'."
        )

    ext = path.suffix.lower()
    if ext in [".xlsx", ".xls", ".xlsm"]:
        try:
            return pd.read_excel(path, sheet_name=sheet_name)
        except ImportError:
            raise ImportError(
                f"Reading Excel file '{path.name}' requires 'openpyxl'.\n"
                "To resolve: Install openpyxl via 'pip install openpyxl', or export "
                "your private Excel data to a local CSV in 'data/private/'."
            )
    elif ext == ".csv":
        return pd.read_csv(path)
    else:
        raise ValueError(
            f"Unsupported file format '{ext}' for {path.name}. "
            "Supported formats: .xlsx, .xls, .xlsm, .csv"
        )


def find_default_file(candidates):
    """Find the first existing file among a list of candidates."""
    for rel_path in candidates:
        full_path = PROJECT_ROOT / rel_path
        if full_path.exists():
            return rel_path
    return candidates[0]


# ==============================================================================
# 4. Local-Only MLflow & Fallback Store Manager
# ==============================================================================
class LocalRunLogger:
    """Manages MLflow runs if mlflow is installed, or writes standard MLflow file store structure."""

    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.run_id = uuid.uuid4().hex
        self.start_time = int(time.time() * 1000)
        self.run_dir = LOCAL_MLFLOW_DIR / "0" / self.run_id
        self.params = {}
        self.metrics = {}
        self.artifacts = []

    def start(self):
        if MLFLOW_AVAILABLE:
            mlflow.set_experiment(self.experiment_name)
            mlflow.start_run()
        else:
            (self.run_dir / "params").mkdir(parents=True, exist_ok=True)
            (self.run_dir / "metrics").mkdir(parents=True, exist_ok=True)
            (self.run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

    def log_param(self, key: str, val):
        if MLFLOW_AVAILABLE:
            mlflow.log_param(key, val)
        else:
            self.params[key] = val
            (self.run_dir / "params" / key).write_text(str(val), encoding="utf-8")

    def log_metric(self, key: str, val: float):
        if MLFLOW_AVAILABLE:
            mlflow.log_metric(key, val)
        else:
            self.metrics[key] = val
            timestamp = int(time.time() * 1000)
            with open(self.run_dir / "metrics" / key, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} {val} 0\n")

    def log_artifact(self, local_path: str, artifact_path: str = None):
        if MLFLOW_AVAILABLE:
            if artifact_path:
                mlflow.log_artifact(local_path, artifact_path=artifact_path)
            else:
                mlflow.log_artifact(local_path)
        else:
            src = Path(local_path)
            if artifact_path:
                dest_dir = self.run_dir / "artifacts" / artifact_path
            else:
                dest_dir = self.run_dir / "artifacts"
            dest_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(src, dest_dir / src.name)

    def finish(self):
        if MLFLOW_AVAILABLE:
            mlflow.end_run()
        else:
            # Write MLflow compatible meta.yaml
            meta_yaml = (
                f"artifact_uri: {self.run_dir.as_uri()}/artifacts\n"
                f"end_time: {int(time.time() * 1000)}\n"
                f"experiment_id: '0'\n"
                f"lifecycle_stage: active\n"
                f"run_id: {self.run_id}\n"
                f"run_name: inventory_drift_run\n"
                f"run_uuid: {self.run_id}\n"
                f"start_time: {self.start_time}\n"
                f"status: 3\n"
                f"user_id: local_user\n"
            )
            (self.run_dir / "meta.yaml").write_text(meta_yaml, encoding="utf-8")


# ==============================================================================
# 5. Main Drift Detection Pipeline
# ==============================================================================
def run_drift_analysis(
    reference_path: str,
    current_path: str,
    ref_sheet=0,
    cur_sheet=0,
    threshold: float = 0.05,
    experiment_name: str = "Inventory_Stock_Drift_Analysis",
    output_dir: str = "reports"
):
    print("=" * 72)
    print("       INVENTORY STOCK DRIFT ANALYSIS (LOCAL PRIVACY MODE)")
    print("=" * 72)
    print(f"[*] MLflow Tracking Store : {LOCAL_TRACKING_URI}")
    print(f"[*] MLflow Package Status : {'Installed' if MLFLOW_AVAILABLE else 'Local File Store Mode'}")
    print(f"[*] Telemetry Disabled    : YES (Strictly Offline)")
    print(f"[*] Loading Reference     : {reference_path}")
    print(f"[*] Loading Current       : {current_path}")
    print(f"[*] Significance Alpha    : {threshold}")
    print("=" * 72)

    # 1. Load datasets locally
    reference = load_dataset(reference_path, sheet_name=ref_sheet)
    current = load_dataset(current_path, sheet_name=cur_sheet)

    # 2. Identify shared numeric features for statistical testing
    features = [
        col for col in reference.select_dtypes(include="number").columns
        if col in current.columns
        and col in current.select_dtypes(include="number").columns
    ]

    if not features:
        raise ValueError(
            "No matching numeric features found between reference and current datasets.\n"
            f"Reference columns: {list(reference.columns)}\n"
            f"Current columns: {list(current.columns)}"
        )

    # 3. Ensure local output directory exists
    reports_path = PROJECT_ROOT / output_dir
    plots_path = reports_path / "plots"
    plots_path.mkdir(parents=True, exist_ok=True)

    # 4. Initialize Local Experiment Run
    logger = LocalRunLogger(experiment_name=experiment_name)
    logger.start()

    logger.log_param("reference_dataset", Path(reference_path).name)
    logger.log_param("current_dataset", Path(current_path).name)
    logger.log_param("statistical_method", "Kolmogorov-Smirnov two-sample test")
    logger.log_param("p_value_threshold", threshold)
    logger.log_param("numeric_features_tested", len(features))

    results = []

    # 5. Perform local Kolmogorov-Smirnov test per feature
    for feature in features:
        ref = reference[feature].dropna().to_numpy()
        cur = current[feature].dropna().to_numpy()

        if len(ref) < 2 or len(cur) < 2:
            print(f"[!] Skipping {feature}: insufficient valid records (< 2).")
            continue

        statistic, p_value = ks_two_sample_test(ref, cur)
        drift = bool(p_value < threshold)

        results.append({
            "feature": feature,
            "reference_count": int(len(ref)),
            "current_count": int(len(cur)),
            "reference_mean": round(float(np.mean(ref)), 4),
            "current_mean": round(float(np.mean(cur)), 4),
            "ks_statistic": round(float(statistic), 4),
            "p_value": round(float(p_value), 6),
            "drift_detected": drift
        })

        # Log metrics locally
        logger.log_metric(f"{feature}_ks_statistic", float(statistic))
        logger.log_metric(f"{feature}_p_value", float(p_value))
        logger.log_metric(f"{feature}_drift", int(drift))

        # Generate comparison plot locally
        if MATPLOTLIB_AVAILABLE:
            plt.figure(figsize=(8, 4))
            plt.hist(ref, bins=25, alpha=0.6, label="Reference (Baseline)", color="#1f77b4")
            plt.hist(cur, bins=25, alpha=0.6, label="Current (Operational)", color="#ff7f0e")
            plt.title(f"Distribution Comparison: {feature} (Drift: {drift})", fontsize=12)
            plt.xlabel(feature)
            plt.ylabel("Frequency")
            plt.legend()
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            plt.tight_layout()

            plot_file = plots_path / f"{feature}_comparison.png"
            plt.savefig(plot_file, dpi=150)
            plt.close()

            logger.log_artifact(str(plot_file), artifact_path="distribution_plots")
        else:
            # Generate local text distribution summary for plot fallback
            summary_txt = plots_path / f"{feature}_distribution.txt"
            ref_q = np.percentile(ref, [10, 25, 50, 75, 90])
            cur_q = np.percentile(cur, [10, 25, 50, 75, 90])
            txt_content = (
                f"Feature: {feature}\n"
                f"Reference Percentiles [10, 25, 50, 75, 90]: {ref_q}\n"
                f"Current Percentiles   [10, 25, 50, 75, 90]: {cur_q}\n"
                f"KS Statistic: {statistic}, P-Value: {p_value}, Drift: {drift}\n"
            )
            summary_txt.write_text(txt_content, encoding="utf-8")
            logger.log_artifact(str(summary_txt), artifact_path="distribution_plots")

    if not results:
        raise ValueError("No features contained sufficient valid numeric data for testing.")

    # 6. Save tabular summary locally
    report_df = pd.DataFrame(results)
    summary_csv = reports_path / "drift_summary.csv"
    summary_json = reports_path / "drift_summary.json"

    report_df.to_csv(summary_csv, index=False)
    report_df.to_json(summary_json, orient="records", indent=2)

    logger.log_artifact(str(summary_csv))
    logger.log_artifact(str(summary_json))
    logger.finish()

    # Print summary table to console
    print("\n--- DRIFT TEST SUMMARY ---")
    print(report_df.to_string(index=False))
    print("\n" + "=" * 72)
    print(f"[✓] Local drift CSV report saved: {summary_csv}")
    print(f"[✓] Local drift JSON report saved: {summary_json}")
    print(f"[✓] Local plots saved           : {plots_path}")
    print(f"[✓] MLflow local run logged to  : {LOCAL_MLFLOW_DIR}")
    print("=" * 72)
    print("\n[+] To view your local MLflow tracking dashboard, run:")
    print("    mlflow ui --host 127.0.0.1 --port 5000\n")
    print("    Then open http://127.0.0.1:5000 in your browser.")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="Local-Only Inventory Stock Drift Analysis with MLflow Tracking"
    )
    default_ref_candidates = [
        "data/private/reference.xlsx",
        "data/private/reference.csv",
        "data/synthetic_demo_reference.csv",
        "data/reference.csv",
    ]
    default_cur_candidates = [
        "data/private/current.xlsx",
        "data/private/current.csv",
        "data/synthetic_demo_current.csv",
        "data/current.csv",
    ]

    parser.add_argument(
        "--reference",
        default=find_default_file(default_ref_candidates),
        help="Path to baseline reference dataset (.xlsx, .xls, .xlsm, or .csv)"
    )
    parser.add_argument(
        "--current",
        default=find_default_file(default_cur_candidates),
        help="Path to current operational dataset (.xlsx, .xls, .xlsm, or .csv)"
    )
    parser.add_argument(
        "--ref-sheet",
        default=0,
        help="Sheet name or index for reference Excel workbook (default: 0)"
    )
    parser.add_argument(
        "--cur-sheet",
        default=0,
        help="Sheet name or index for current Excel workbook (default: 0)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Significance p-value threshold for KS test (default: 0.05)"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Local directory for generated reports and plots (default: reports)"
    )

    args = parser.parse_args()

    run_drift_analysis(
        reference_path=args.reference,
        current_path=args.current,
        ref_sheet=args.ref_sheet,
        cur_sheet=args.cur_sheet,
        threshold=args.threshold,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
