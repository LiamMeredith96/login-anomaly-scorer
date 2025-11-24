from math import radians, sin, cos, asin, sqrt
import pandas as pd

# Great-circle distance in KM between two lat/lon points.
# Small, dependency-free (good enough for this detection use-case).
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Turns raw sign-ins into signals we can score:
      - distance/speed since the user's previous login
      - browser/devic change flags
      - "rare" ASN for that user
    """
    # Keep events ordered per user so "previous" makes sense
    df = df.sort_values(["user_id", "timestamp"]).copy()

    # Previous-event context for each user
    prev = df.groupby("user_id")[["lat", "lon", "timestamp", "user_agent", "device_id"]].shift(1)
    df["prev_lat"] = prev["lat"]
    df["prev_lon"] = prev["lon"]
    df["prev_ts"]  = prev["timestamp"]
    df["prev_ua"]  = prev["user_agent"]
    df["prev_dev"] = prev["device_id"]

    # Distance (km) between current and previous location
    # If no previous (first event), sets to 0
    df["km"] = df.apply(
        lambda r: haversine(r.prev_lat, r.prev_lon, r.lat, r.lon) if pd.notnull(r.prev_lat) else 0,
        axis=1
    )

    # Minutes since previous login (parses to datetime to be safe)
    # Fills first event with 1 minute to avoid divide-by-zero
    df["mins"] = (
        pd.to_datetime(df["timestamp"]) - pd.to_datetime(df["prev_ts"])
    ).dt.total_seconds().div(60).fillna(1)

    # Speed (km/h) – core signal for "impossible travel"
    df["kmph"] = (df["km"] / df["mins"]) * 60

    # Did the UA (browser/OS) or device change since last login?
    # Converts to 0/1 ints for easy scoring later.
    df["ua_changed"]  = (df["user_agent"] != df["prev_ua"]).fillna(False).astype(int)
    df["dev_changed"] = (df["device_id"]  != df["prev_dev"]).fillna(False).astype(int)

    # ASN rarity: first time we've seen this network (ASN) for this user?
    counts = df.groupby(["user_id", "asn"]).size().rename("cnt")
    df = df.join(counts, on=["user_id", "asn"])
    df["asn_rare"] = (df["cnt"] == 1).astype(int)

    return df
