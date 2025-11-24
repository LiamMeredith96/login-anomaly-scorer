import argparse
import os
import pandas as pd

# Relative imports inside the package
from .data_gen import generate_synthetic
from .features import add_features
from .rules import score_rules, precision_at_k
from .iforest import add_iforest_score


def main():
    # CLI: booleans + simple flags/paths so anypne can run this quickly.
    p = argparse.ArgumentParser(description="Login Anomaly Scorer")
    p.add_argument("--in_csv",  default="data/sample_logins.csv", help="Input CSV of sign-ins")
    p.add_argument("--out_csv", default="data/alerts.csv",       help="Output CSV of alerts")
    p.add_argument("--gen",     action="store_true",             help="Generate synthetic input at data/sample_logins.csv")
    p.add_argument("--iforest", action="store_true",             help="Add IsolationForest anomaly score")

    # Small flags for demos
    p.add_argument("--max_speed", type=float, default=900.0, help="Impossible-travel threshold in km/h")
    p.add_argument("--sortby", choices=["score", "iforest_score"], default="score",
                   help="Column to sort preview/CSV by")
    p.add_argument("--top", type=int, default=10, help="How many rows to preview in the terminal")
    args = p.parse_args()

    # Makes sure output folder exists
    os.makedirs("data", exist_ok=True)

    # Generates a reproducible synthetic dataset so this runs end-to-end
    if args.gen:
        df_gen = generate_synthetic()
        df_gen.to_csv("data/sample_logins.csv", index=False)
        print("Wrote data/sample_logins.csv")

    # Loads input parse timestamp so time deltas work
    try:
        df = pd.read_csv(args.in_csv, parse_dates=["timestamp"])
    except FileNotFoundError:
        raise SystemExit(f"Input not found: {args.in_csv}. Run with --gen or point --in_csv to a CSV.")

    # Feature engineering and rule scoring
    feats = add_features(df)
    scored = score_rules(feats, max_speed_kmph=args.max_speed)

    # Optional: add Isolation Forest as a secondary ranking signal (rules stay primary)
    if args.iforest:
        scored = add_iforest_score(scored)
        if "iforest_score" not in scored.columns:
            print("Note: --iforest was requested, but no ML score column was produced.")

    # Quick terminal preview
    if args.sortby == "score":
        preview_cols = ["score", "kmph", "ua_changed", "dev_changed", "asn_rare"]
        asc = False
    else:
        # iforest sort needs the column, but if missing, fall back
        if "iforest_score" not in scored.columns:
            print("Note: --sortby iforest_score requested but no ML score present. Falling back to score.")
            args.sortby = "score"
            preview_cols = ["score", "kmph", "ua_changed", "dev_changed", "asn_rare"]
            asc = False
        else:
            preview_cols = ["iforest_score", "score", "kmph", "ua_changed", "dev_changed", "asn_rare"]
            asc = False  # higher = more anomalous

    print("\nTop rows (preview):")
    try:
        print(scored[preview_cols].sort_values(args.sortby, ascending=asc).head(args.top))
    except KeyError:
        # If user asks for a column that isn't there, falls back to rule score
        print(scored[["score", "kmph", "ua_changed", "dev_changed", "asn_rare"]]
              .sort_values("score", ascending=False).head(args.top))

    # Persist results using the chosen sort key
    scored.sort_values(args.sortby, ascending=asc).to_csv(args.out_csv, index=False)
    print(f"\nWrote {args.out_csv}")

    # If synthetic labels exist, prints a tiny metric
    if "label" in scored.columns:
        p10_rules = precision_at_k(scored, k=10, by="score")
        print(f"precision@10 (rule): {p10_rules:.2f}")
        if args.iforest and "iforest_score" in scored.columns:
            p10_ml = precision_at_k(scored, k=10, by="iforest_score")
            print(f"precision@10 (iforest): {p10_ml:.2f}")


if __name__ == "__main__":
    # Standard Python entrypoint. Keeps the module importable and the CLI runnable.
    main()
