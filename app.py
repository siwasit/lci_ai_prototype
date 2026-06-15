"""
app.py — Flask web UI for the LCI-AI Prototype
────────────────────────────────────────────────
Run:  python app.py
Then: http://localhost:5000

Expert workflow:
  /          → configure process + upload PDFs
  /run       → run extraction pipeline (POST)
  /review    → review flagged flows, correct or remove
  /approve   → apply corrections + export (POST)
  /results   → download JSON / CSV / ILCD XML
  /download/<f> → serve export file
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import uuid, json
from flask import (
    Flask, render_template, request,
    session, redirect, url_for, send_from_directory, flash,
)

import config
from main import run_pipeline_api
from pipeline.models import LCIDataset
from pipeline.validation import validate_dataset
from pipeline.lcia import calculate_gwp100
from export.to_json import export_json
from export.to_csv  import export_csv
from export.to_ilcd import export_ilcd

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── In-memory session store (fine for single-user demo) ──────────────
_store: dict[str, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────

def _get_store() -> dict | None:
    sid = session.get("sid")
    return _store.get(sid) if sid else None


def _set_store(data: dict) -> str:
    sid = str(uuid.uuid4())
    session["sid"] = sid
    _store[sid] = data
    return sid


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
        default_process=config.DEFAULT_PROCESS_NAME,
        default_fu=config.DEFAULT_FU,
    )


@app.route("/run", methods=["POST"])
def run():
    process_name    = request.form.get("process_name", config.DEFAULT_PROCESS_NAME).strip()
    functional_unit = request.form.get("functional_unit", config.DEFAULT_FU).strip()
    system_boundary = request.form.get("system_boundary", "Cradle to farm gate").strip()
    provider        = request.form.get("provider", "demo")

    # Handle optional PDF upload
    pdf_path = None
    f = request.files.get("pdf_file")
    if f and f.filename:
        os.makedirs(config.DATA_INPUT, exist_ok=True)
        save_path = os.path.join(config.DATA_INPUT, f.filename)
        f.save(save_path)
        pdf_path = save_path

    try:
        result = run_pipeline_api(
            mode="demo" if provider == "demo" else "extract",
            pdf_path=pdf_path,
            provider=provider,
            process_name=process_name,
            functional_unit=functional_unit,
        )
    except Exception as e:
        flash(f"Pipeline error: {e}", "error")
        return redirect(url_for("index"))

    lci: LCIDataset = result["lci"]
    lci.system_boundary = system_boundary  # apply expert's system boundary

    _set_store({
        "lci":        lci.to_dict(),
        "validation": result["validation"],
        "gwp":        result["gwp"],
    })
    return redirect(url_for("review"))


@app.route("/review")
def review():
    data = _get_store()
    if not data:
        return redirect(url_for("index"))

    lci        = LCIDataset.from_dict(data["lci"])
    validation = data["validation"]
    gwp        = data["gwp"]

    # Build per-flow review list (with index and direction for form submission)
    flows_with_meta = []
    val_map = {r["flow"]: r for r in validation}

    for idx, flow in enumerate(lci.inputs):
        v = val_map.get(flow.name, {"status": "NO_RANGE"})
        flows_with_meta.append({
            "direction": "input", "idx": idx,
            "flow": flow, "validation": v,
        })
    for idx, flow in enumerate(lci.outputs):
        v = val_map.get(flow.name, {"status": "NO_RANGE"})
        flows_with_meta.append({
            "direction": "output", "idx": idx,
            "flow": flow, "validation": v,
        })

    flagged = [f for f in flows_with_meta if f["validation"]["status"] == "FLAG"]

    return render_template("review.html",
        lci=lci,
        flows=flows_with_meta,
        flagged=flagged,
        gwp=gwp,
        validation=validation,
    )


@app.route("/approve", methods=["POST"])
def approve():
    data = _get_store()
    if not data:
        return redirect(url_for("index"))

    lci = LCIDataset.from_dict(data["lci"])

    # Collect all form keys: flow_{direction}_{idx}_action / _amount
    corrections = {}
    for key, val in request.form.items():
        if key.startswith("flow_") and key.endswith("_action"):
            parts     = key.split("_")   # ["flow","input","0","action"]
            direction = parts[1]
            idx       = int(parts[2])
            action    = val
            amount_key = f"flow_{direction}_{idx}_amount"
            new_amount = request.form.get(amount_key)
            corrections[(direction, idx)] = (action, new_amount)

    # Apply corrections in reverse-index order (so removals don't shift indices)
    to_remove = sorted(
        [(d, i) for (d, i), (a, _) in corrections.items() if a == "remove"],
        key=lambda x: x[1], reverse=True
    )
    for direction, idx in to_remove:
        lci.remove_flow(direction, idx)

    for (direction, idx), (action, new_amount) in corrections.items():
        if action == "correct" and new_amount:
            try:
                # Re-index after removals: find flow by original position
                # (removals already done above, so only correct surviving flows)
                removed_before = sum(
                    1 for (d, i) in to_remove
                    if d == direction and i < idx
                )
                new_idx = idx - removed_before
                lci.correct_flow_amount(direction, new_idx, float(new_amount))
            except (ValueError, IndexError):
                pass

    # Re-run validation + GWP on corrected dataset
    validation = validate_dataset(lci)
    gwp        = calculate_gwp100(lci)

    # Export
    os.makedirs(config.DATA_OUTPUT, exist_ok=True)
    json_path  = export_json(lci)
    csv_path   = export_csv(lci)
    ilcd_path  = export_ilcd(lci)

    # Update store with corrected data
    sid = session.get("sid")
    if sid and sid in _store:
        _store[sid].update({
            "lci":        lci.to_dict(),
            "validation": validation,
            "gwp":        gwp,
            "exports": {
                "json":  os.path.basename(json_path),
                "csv":   os.path.basename(csv_path),
                "ilcd":  os.path.basename(ilcd_path),
            },
        })

    return redirect(url_for("results"))


@app.route("/results")
def results():
    data = _get_store()
    if not data:
        return redirect(url_for("index"))

    lci     = LCIDataset.from_dict(data["lci"])
    gwp     = data["gwp"]
    exports = data.get("exports", {})
    return render_template("results.html", lci=lci, gwp=gwp, exports=exports)


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(config.DATA_OUTPUT, filename, as_attachment=True)


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(config.DATA_INPUT,  exist_ok=True)
    os.makedirs(config.DATA_OUTPUT, exist_ok=True)
    print("\n  LCI-AI Web UI  →  http://localhost:5000\n")
    app.run(debug=True, port=5000)
