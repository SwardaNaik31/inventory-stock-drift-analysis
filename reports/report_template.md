# Inventory Stock Drift Analysis — Methodology & Report Template

> **Privacy Notice**: This template defines the evaluation methodology, statistical criteria, and report schema. Actual inventory drift outputs (containing private business metrics, item counts, prices, and distributions) are generated locally into `reports/drift_summary.csv`, `reports/drift_summary.json`, and `reports/plots/`, which are strictly excluded from version control via `.gitignore`.

---

## 1. Objective & Scope

The purpose of this pipeline is to detect statistical drift in inventory and stock metrics between a baseline historical reference period and a current operational period. Detecting stock drift helps supply chain managers identify:
- Sudden surges or drops in stock availability (out-of-stock risk or excess inventory).
- Changes in restock frequencies, lead times, or inventory valuations.
- Shifts in product demand velocity before stockouts impact sales.

---

## 2. Statistical Methodology

### Kolmogorov-Smirnov (KS) Two-Sample Test
For each numeric inventory feature, we apply the two-sample Kolmogorov-Smirnov test (`scipy.stats.ks_2samp`):
- **Null Hypothesis ($H_0$)**: The reference period and current period samples come from identical continuous distributions.
- **Alternative Hypothesis ($H_1$)**: The current distribution has significantly drifted from the reference distribution.
- **Decision Rule**:
  $$\text{Drift Detected} = \begin{cases} \text{True} & \text{if } p\text{-value} < \alpha \\ \text{False} & \text{if } p\text{-value} \ge \alpha \end{cases}$$
- **Default Significance Threshold ($\alpha$)**: `0.05`

---

## 3. Evaluated Inventory Metrics

| Feature Category | Example Numeric Columns | Drift Significance |
| :--- | :--- | :--- |
| **Stock Levels** | `closing_stock`, `available_quantity` | Changes in warehouse inventory levels |
| **Reorder Dynamics** | `reorder_point`, `safety_stock_level` | Shifts in restocking triggers |
| **Financial Valuation** | `unit_cost`, `total_inventory_value` | Price fluctuations or supplier cost shifts |
| **Velocity & Turnover** | `units_sold_per_month`, `days_of_supply` | Shifts in consumer demand or sales velocity |

---

## 4. Experiment Tracking Architecture (MLflow Local-Only)

All experiment metadata, parameters, and generated distribution plots are logged using a 100% offline, local MLflow tracking store:

- **Tracking URI**: `file:./mlruns` (relative to project root)
- **Telemetry**: Disabled (`MLFLOW_ENABLE_TELEMETRY=false`)
- **Remote Endpoints**: None (zero cloud exfiltration)
- **Local Dashboard**: Accessible exclusively via loopback `http://127.0.0.1:5000`

---

## 5. Drift Report Schema (Placeholder Template)

*When `src/detect_drift.py` is executed locally, private results are written to `reports/drift_summary.csv` matching this schema:*

| Feature | Reference Count | Current Count | Reference Mean | Current Mean | KS Statistic | P-Value | Drift Detected |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *`<metric_1>`* | *`<int>`* | *`<int>`* | *`<float>`* | *`<float>`* | *`<float>`* | *`<float>`* | `True / False` |
| *`<metric_2>`* | *`<int>`* | *`<int>`* | *`<float>`* | *`<float>`* | *`<float>`* | *`<float>`* | `True / False` |

---

## 6. Local Artifacts Generated

1. `reports/drift_summary.csv`: Tabular drift test results for all numeric columns.
2. `reports/drift_summary.json`: JSON format results for integration with local downstream dashboards.
3. `reports/plots/<feature>_comparison.png`: Side-by-side distribution histogram comparisons.
4. `mlruns/`: Local MLflow runs and artifact storage.

*(All of the above paths are local-only and excluded from Git commits)*
