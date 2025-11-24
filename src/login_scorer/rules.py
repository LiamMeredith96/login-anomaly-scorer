import pandas as pd

def score_rules(
    df: pd.DataFrame,
    max_speed_kmph: float = 900.0,      # threshold for "impossible travel"
    device_mismatch_trigger: int = 1,   # how many change flags (UA/device) to trigger
    rare_asn_bonus: int = 1,            # points to add if ASN is first-seen for the user
) -> pd.DataFrame:
    """
    Simple, explainable scoring:
      - +2 if speed > max_speed_kmph  (impossible travel)
      - +1 if UA or device changed    (device mismatch)
      - +1 if ASN is first-seen       (rare ASN)
    Also builds a reason string so you know exactly why a row was flagged.
    """
    out = df.copy()

    # Base points for impossible travel
    s_imposs = (out["kmph"] > max_speed_kmph).astype(int) * 2

    # +1 if either UA or device changed since last login (>= trigger)
    s_dev = ((out["ua_changed"] + out["dev_changed"]) >= device_mismatch_trigger).astype(int)

    # +1 if first time we've seen this ASN for that user (cheap risk signal)
    s_asn = out["asn_rare"] * rare_asn_bonus

    # Total rule score (higher = more suspicious)
    out["score"] = s_imposs + s_dev + s_asn

    # Human-readable tags so an analyst sees why it scored up
    out["reason"] = [
        ";".join(
            [t for (t, fired) in (
                ("impossible_travel", r.kmph > max_speed_kmph),
                ("device_mismatch", bool(r.ua_changed or r.dev_changed)),
                ("rare_asn",        bool(r.asn_rare)),
            ) if fired]
        )
        for _, r in out.iterrows()
    ]

    return out


def precision_at_k(df: pd.DataFrame, k: int = 20, by: str = "score") -> float:
    topk = df.sort_values(by, ascending=False).head(k)
    # If there’s no data, return 0
    return 0.0 if topk.empty else (topk["label"] == "attack").mean()
