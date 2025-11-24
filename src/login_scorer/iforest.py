import pandas as pd
from sklearn.ensemble import IsolationForest

def add_iforest_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a lightweight anomaly score using Isolation Forest.
    - Unsupervised: no labels needed; it learns what's normal from the generated data.
    - Rules are primary; this is a second ranking signal.
    """
    # Features the model will look at.
    # fillna(0) so the model never sees NaNs.
    feats = df[["km", "kmph", "ua_changed", "dev_changed", "asn_rare"]].fillna(0)

    out = df.copy()

    # IsolationForest basics:
    # - n_estimators: number of random trees (100 is fine for this size)
    # - contamination: rough fraction of anomalies expected (2% here for demo)
    # - random_state: fixed seed so runs are reproducible
    clf = IsolationForest(n_estimators=100, contamination=0.02, random_state=42)

    # decision_function: higher = more normal.
    # We invert it so higher = more anomalous.
    out["iforest_score"] = -clf.fit(feats).decision_function(feats)

    return out
