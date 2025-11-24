# Login Anomaly Scorer (Impossible-Travel & Device-Mismatch)

Detects unusual sign-in behaviour (e.g., impossible travel, device/UA switches, first-seen networks) and writes a ranked `alerts.csv` for triage. Optional anomaly ranking adds a lightweight ML signal (Isolation Forest).

---

## Project layout (modular `src` style)

repo_root/
- README.md
- requirements.txt
- .gitignore
- data/                 # generated files live here
- src/
  - login_scorer/
    - __init__.py
    - data_gen.py       # synthetic data generator
    - features.py       # feature/signal engineering
    - rules.py          # rule-based scoring + reasons
    - iforest.py        # optional IsolationForest anomaly score
    - cli.py            # CLI entrypoint

---

## Install

**Windows**
1) Create venv: `python -m venv .venv`
2) Activate: `.\.venv\Scripts\Activate.ps1`
3) Upgrade pip: `pip install --upgrade pip`
4) Install deps: `pip install -r requirements.txt`

**macOS / Linux**
1) Create venv: `python -m venv .venv`
2) Activate: `source .venv/bin/activate`
3) Upgrade pip: `pip install --upgrade pip`
4) Install deps: `pip install -r requirements.txt`

---

## How to run

1) Generate synthetic sign-ins: `python -m src.login_scorer.cli --gen` → writes `data/sample_logins.csv`

2) Score with rules (impossible travel, device/UA change, rare ASN): `python -m src.login_scorer.cli` → writes `data/alerts.csv` (adds `score`, `reason`)

3) Optional: add ML anomaly ranking (Isolation Forest): `python -m src.login_scorer.cli --iforest` → rewrites `data/alerts.csv` adding `iforest_score`, prints precision@10 if labels exist

### CLI options
- `--gen` (boolean): create synthetic input at `data/sample_logins.csv`
- `--iforest` (boolean): add Isolation Forest anomaly ranking
- `--in_csv PATH` (string): input CSV path (default `data/sample_logins.csv`)
- `--out_csv PATH` (string): output CSV path (default `data/alerts.csv`)

Examples:
- `python -m src.login_scorer.cli --in_csv data/logins_week1.csv --out_csv data/alerts_week1.csv`
- `python -m src.login_scorer.cli --iforest --out_csv data/alerts_with_ml.csv`

---

## What it computes (features)

- `km` — great-circle distance to the previous login for the same user
- `mins` — minutes since the previous login
- `kmph` — speed (km/h) = `km / mins * 60`
- `ua_changed` — 1 if User-Agent (browser/OS) changed since previous login
- `dev_changed` — 1 if device ID changed
- `asn_rare` — 1 if this ASN (network/ISP) is first-seen for the user

Notes: ASN = Autonomous System Number (network owner of an IP); UA = User-Agent (browser/OS string); lat/lon are synthetic (sampled from a small city list).

---

## Scoring (rules)

- Impossible travel: `kmph > 900` → +2 points (tag `impossible_travel`)
- Device/UA change: either changed → +1 point (tag `device_mismatch`)
- Rare ASN: first-seen for user → +1 point (tag `rare_asn`)
- Sum → `score` (higher = more suspicious)
- `reason` lists the rule tags (e.g., `impossible_travel;device_mismatch`)

---

## Optional anomaly ranking (ML)

Adds `iforest_score` via Isolation Forest (unsupervised outlier detection). Use it as a secondary ranking signal (e.g., sort by `score` then by `iforest_score` to break ties). Rules remain primary for explainability.

---

## Reproducibility

To get the same synthetic data every run, set a fixed seed at the top of `data_gen.py`:
`import random, numpy as np` then `random.seed(42); np.random.seed(42)`.

---

## Outputs

- `data/sample_logins.csv` — synthetic sign-ins (created by `--gen`)
- `data/alerts.csv` — scored results (`score`, `reason`, optional `iforest_score`)

---

## Typical workflow

1) Generate a dataset (`--gen`)
2) Score with rules (and optionally using `--iforest`)
3) Open `data/alerts.csv` and review the top rows by `score` (and `iforest_score`)

---

## Limitations & next steps

- VPNs/shared IPs can create false positives (geo/ASN can be misleading)
- Next: time-of-day per-user baselines, country allow-lists, IP reputation, session binding
- In production, geo/ASN come from real enrichment, not synthetic values

