"""
Local MLflow Experiment Dashboard Viewer (Zero-Dependency Fallback)
==================================================================
Runs a local, privacy-safe web dashboard on http://127.0.0.1:5000
using only Python's standard library (no pip dependencies required).

Reads local MLflow runs from ./mlruns and displays:
- Experiment metadata and run history
- Logged parameters (threshold, method, datasets)
- Logged metrics (KS statistics, p-values, drift flags)
- Logged artifacts (drift_summary.csv, drift_summary.json, plots)
"""

import os
import sys
import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MLRUNS_DIR = PROJECT_ROOT / "mlruns"


def load_runs():
    """Parse local runs from mlruns directory."""
    runs = []
    exp_dir = MLRUNS_DIR / "0"
    if not exp_dir.exists():
        return runs

    for item in exp_dir.iterdir():
        if item.is_dir() and item.name != "artifacts" and not item.name.startswith("."):
            run_id = item.name
            meta_file = item / "meta.yaml"
            run_data = {
                "run_id": run_id,
                "start_time": "N/A",
                "status": "COMPLETED",
                "params": {},
                "metrics": {},
                "artifacts": []
            }

            # Parse meta.yaml
            if meta_file.exists():
                for line in meta_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("start_time:"):
                        try:
                            ts = int(line.split(":")[1].strip()) / 1000
                            run_data["start_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                        except Exception:
                            pass
                    elif line.startswith("status:"):
                        status_code = line.split(":")[1].strip()
                        run_data["status"] = "FINISHED" if status_code == "3" else status_code

            # Parse params
            params_dir = item / "params"
            if params_dir.exists():
                for p_file in params_dir.iterdir():
                    if p_file.is_file():
                        run_data["params"][p_file.name] = p_file.read_text(encoding="utf-8").strip()

            # Parse metrics
            metrics_dir = item / "metrics"
            if metrics_dir.exists():
                for m_file in metrics_dir.iterdir():
                    if m_file.is_file():
                        content = m_file.read_text(encoding="utf-8").strip()
                        # MLflow metric format: "<timestamp> <value> <step>"
                        parts = content.splitlines()[-1].split() if content else []
                        if len(parts) >= 2:
                            run_data["metrics"][m_file.name] = parts[1]

            # Parse artifacts
            artifacts_dir = item / "artifacts"
            if artifacts_dir.exists():
                for root, _, files in os.walk(artifacts_dir):
                    for file in files:
                        rel = os.path.relpath(os.path.join(root, file), artifacts_dir)
                        run_data["artifacts"].append(rel.replace("\\", "/"))

            runs.append(run_data)

    # Sort newest first
    runs.reverse()
    return runs


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local MLflow Experiment Tracker - Inventory Stock Drift</title>
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --primary: #38bdf8;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --badge-green: #10b981;
            --badge-red: #ef4444;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }
        .title {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-offline {
            background: rgba(16, 185, 129, 0.15);
            color: var(--badge-green);
            border: 1px solid var(--badge-green);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .run-id {
            font-family: monospace;
            color: var(--primary);
            font-size: 16px;
            font-weight: 600;
        }
        .meta-text {
            color: var(--text-muted);
            font-size: 13px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 14px;
        }
        th, td {
            text-align: left;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
        }
        th {
            background: rgba(0, 0, 0, 0.2);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
        }
        .tag-drift {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        }
        .tag-stable {
            background: rgba(16, 185, 129, 0.2);
            color: #86efac;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 16px;
        }
        .param-list {
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 13px;
        }
        .param-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px dashed var(--border);
        }
        .artifact-chip {
            display: inline-block;
            background: rgba(56, 189, 248, 0.1);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            margin: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div class="title">
                    <span>📊 Inventory Stock Drift Analysis</span>
                    <span class="badge-offline">LOCAL OFFLINE TRACKER</span>
                </div>
                <div class="meta-text" style="margin-top: 6px;">
                    Experiment: <code>Inventory_Stock_Drift_Analysis</code> (Store: <code>./mlruns</code>)
                </div>
            </div>
            <div>
                <button onclick="window.location.reload()" style="background: var(--surface); color: var(--text); border: 1px solid var(--border); padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                    🔄 Refresh
                </button>
            </div>
        </div>

        __RUNS_CONTENT__

    </div>
</body>
</html>
"""


class LocalDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            runs = load_runs()
            if not runs:
                content = """
                <div class="card" style="text-align: center; padding: 40px;">
                    <h3>No MLflow Runs Found in <code>./mlruns</code></h3>
                    <p class="meta-text">Run <code>python src/detect_drift.py</code> to log your first experiment.</p>
                </div>
                """
            else:
                cards = []
                for r in runs:
                    params_html = "".join(
                        f"<li class='param-item'><span class='meta-text'>{k}</span><span><b>{v}</b></span></li>"
                        for k, v in r["params"].items()
                    )
                    artifacts_html = "".join(
                        f"<span class='artifact-chip'>📄 {a}</span>"
                        for a in r["artifacts"]
                    )

                    # Extract metrics grouped by feature
                    features = set()
                    for m in r["metrics"]:
                        if "_" in m:
                            feat = m.rsplit("_", 1)[0]
                            features.add(feat)

                    metrics_rows = []
                    for f in sorted(features):
                        ks = r["metrics"].get(f"{f}_ks_statistic", "N/A")
                        pv = r["metrics"].get(f"{f}_p_value", "N/A")
                        drift_val = r["metrics"].get(f"{f}_drift", "0")
                        is_drift = drift_val == "1"
                        badge = "<span class='tag-drift'>DRIFT</span>" if is_drift else "<span class='tag-stable'>STABLE</span>"
                        metrics_rows.append(
                            f"<tr><td><b>{f}</b></td><td>{ks}</td><td>{pv}</td><td>{badge}</td></tr>"
                        )

                    metrics_table = f"""
                    <table>
                        <thead>
                            <tr><th>Feature</th><th>KS Statistic</th><th>P-Value</th><th>Result</th></tr>
                        </thead>
                        <tbody>
                            {''.join(metrics_rows) if metrics_rows else '<tr><td colspan="4">No feature metrics</td></tr>'}
                        </tbody>
                    </table>
                    """

                    card = f"""
                    <div class="card">
                        <div class="card-header">
                            <div>
                                <span class="meta-text">Run ID:</span> <span class="run-id">{r['run_id']}</span>
                            </div>
                            <div class="meta-text">
                                Started: <b>{r['start_time']}</b> | Status: <b style="color: var(--badge-green)">{r['status']}</b>
                            </div>
                        </div>

                        <div class="grid-2">
                            <div>
                                <h4 style="margin: 0 0 10px 0;">Parameters</h4>
                                <ul class="param-list">{params_html if params_html else '<span class="meta-text">None</span>'}</ul>
                                <h4 style="margin: 16px 0 10px 0;">Logged Artifacts</h4>
                                <div>{artifacts_html if artifacts_html else '<span class="meta-text">None</span>'}</div>
                            </div>
                            <div>
                                <h4 style="margin: 0 0 10px 0;">Statistical Test Metrics</h4>
                                {metrics_table}
                            </div>
                        </div>
                    </div>
                    """
                    cards.append(card)
                content = "".join(cards)

            html = HTML_TEMPLATE.replace("__RUNS_CONTENT__", content)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence default access log to keep terminal clean
        return


def start_server(host="127.0.0.1", port=5000):
    server = HTTPServer((host, port), LocalDashboardHandler)
    print("=" * 70)
    print(" LOCAL EXPERIMENT TRACKER DASHBOARD (OFFLINE)")
    print("=" * 70)
    print(f"[*] Serving MLflow tracking store at: http://{host}:{port}")
    print(f"[*] Bound strictly to loopback: {host} (No external access)")
    print("[*] Press Ctrl+C in this terminal to stop the server.")
    print("=" * 70)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Dashboard server stopped.")
        server.server_close()


if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port=port)
