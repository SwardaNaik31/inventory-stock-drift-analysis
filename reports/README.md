# Reports Directory

This directory contains:
- `report_template.md`: Public-safe methodology documentation and schema template.
- Generated reports (`drift_summary.csv`, `drift_summary.json`) and plot images (`reports/plots/*.png`).

### Privacy Rule:
All generated files (`*.csv`, `*.json`, `plots/`) contain actual business metrics from your local inventory datasets and are **strictly excluded from Git tracking** via the root `.gitignore`.

Do not force-add (`git add -f`) any generated report files to version control.
