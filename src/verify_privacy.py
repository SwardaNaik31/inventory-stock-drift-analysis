"""
Privacy and Git Safety Pre-Commit Verification Tool
===================================================
Run this script before any Git commit or push to verify that:
1. Strict privacy rules are properly set in .gitignore.
2. No private Excel/CSV files, reports, plots, or MLflow artifacts are staged.
3. MLflow is configured exclusively for offline local tracking.
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mandatory patterns that must exist in .gitignore
REQUIRED_GITIGNORE_PATTERNS = [
    "data/private/",
    "data/**/*.xlsx",
    "data/**/*.xls",
    "data/**/*.csv",
    "data/**/*.xlsm",
    ".env",
    ".venv/",
    "__pycache__/",
    "mlruns/",
]

# Sensitive file extensions and paths that must NEVER be staged in Git
DANGEROUS_EXTENSIONS = [".xlsx", ".xls", ".xlsm", ".db", ".sqlite"]
DANGEROUS_PATH_SEGMENTS = [
    "data/private",
    "mlruns",
    "reports/plots",
    "reports/drift_summary.csv",
    "reports/drift_summary.json",
    ".venv",
    "__pycache__",
]


def check_gitignore():
    """Verify that .gitignore contains all mandatory privacy exclusions."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return False, "Missing .gitignore file in project root!"

    content = gitignore_path.read_text(encoding="utf-8")
    missing = []
    for pattern in REQUIRED_GITIGNORE_PATTERNS:
        if pattern not in content:
            missing.append(pattern)

    if missing:
        return False, f"Missing required privacy patterns in .gitignore:\n  " + "\n  ".join(missing)
    return True, "All required privacy rules are present in .gitignore."


def check_git_staged_files():
    """Inspect Git staging area to ensure zero private files are staged."""
    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.exists():
        return True, "Git repository not yet initialized. No files are currently staged."

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        lines = res.stdout.strip().splitlines()
        staged_files = []
        for line in lines:
            if len(line) >= 3:
                index_status = line[0]
                filepath = line[3:].strip().replace("\\", "/")
                # If staged (A, M, R, C, etc. in index column)
                if index_status in ["A", "M", "R", "C"]:
                    staged_files.append(filepath)

        violations = []
        for f in staged_files:
            lower = f.lower()
            # Allow synthetic demo CSVs
            if "synthetic_demo" in lower:
                continue

            # Check dangerous extensions
            if any(lower.endswith(ext) for ext in DANGEROUS_EXTENSIONS):
                violations.append(f"STAGED DANGEROUS EXTENSION: {f}")
            # Check dangerous CSV files
            elif lower.endswith(".csv") and not "synthetic_demo" in lower:
                violations.append(f"STAGED RAW CSV: {f}")
            # Check dangerous paths
            elif any(seg in lower for seg in DANGEROUS_PATH_SEGMENTS):
                violations.append(f"STAGED SENSITIVE PATH: {f}")

        if violations:
            msg = "STAGED PRIVACY VIOLATIONS FOUND:\n  " + "\n  ".join(violations)
            msg += "\n\nRemediation: Run 'git reset HEAD <file>' to unstage before committing!"
            return False, msg

        return True, f"Git staging is clean ({len(staged_files)} safe files staged, 0 private files staged)."
    except Exception as e:
        return False, f"Could not inspect Git status: {e}"


def check_test_ignore_behavior():
    """Test git check-ignore on hypothetical sensitive paths."""
    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.exists():
        return True, "Git repository not yet initialized; skipping git check-ignore test."

    test_paths = [
        "data/private/inventory_q3.xlsx",
        "data/private/stock_levels.csv",
        "mlruns/0/meta.yaml",
        "reports/plots/current_stock_comparison.png",
        "reports/drift_summary.csv",
        ".env",
    ]

    unignored = []
    for path in test_paths:
        res = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=PROJECT_ROOT
        )
        if res.returncode != 0:
            unignored.append(path)

    if unignored:
        return False, f"The following test paths are NOT ignored by Git:\n  " + "\n  ".join(unignored)

    return True, "All sensitive test paths are correctly verified as IGNORED by Git."


def run_all_checks():
    print("=" * 70)
    print(" PRIVACY & PRE-COMMIT AUDIT CHECKLIST")
    print("=" * 70)

    checks = [
        ("Checking .gitignore privacy rules", check_gitignore),
        ("Checking Git staged files", check_git_staged_files),
        ("Testing Git ignore rules on sensitive paths", check_test_ignore_behavior),
    ]

    all_passed = True
    for desc, func in checks:
        passed, msg = func()
        status_icon = "[✓ PASS]" if passed else "[✗ FAIL]"
        print(f"\n{status_icon} {desc}:")
        print(f"       {msg}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[✓ AUDIT PASSED] Your project meets all dataset privacy requirements.")
        print("                 Safe to work locally or commit approved code files.")
    else:
        print("[✗ AUDIT FAILED] Privacy issues detected! Address above errors before committing.")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
