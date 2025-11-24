import random
from datetime import datetime, timedelta
from typing import List, Tuple
import numpy as np
import pandas as pd

# Fixed seeds so the synthetic dataset is reproducible every run
random.seed(42); np.random.seed(42)

# Small pool of cities we "teleport" between (demo-friendly lat/lon)
CITIES: List[Tuple[str, float, float]] = [
    ("London", 51.5074, -0.1278),
    ("Manchester", 53.4808, -2.2426),
    ("Paris", 48.8566, 2.3522),
    ("New York", 40.7128, -74.0060),
    ("Sydney", -33.8688, 151.2093),
]

# Basic network owners (ASNs) and user-agents to simulate variety
ASNS = ["AS15169", "AS3356", "AS174", "AS5607"]
UAS  = ["Win/Chrome", "Win/Edge", "Mac/Safari", "Linux/Firefox", "Android/Chrome"]


def generate_synthetic(n_users: int = 20, days: int = 7, rows: int = 1500) -> pd.DataFrame:
    """
    Create a synthetic sign-in table with a mix of 'benign' and injected 'attack' rows.
    - Benign: random user logs in from a city at some time within the window.
    - Attacks: (1) impossible travel hop in ~30 mins, (2) device/UA switch + rare ASN.
    """
    # Start of the time window we sample from
    start = datetime(2025, 10, 1)

    # User pool
    users = [f"user{i}@example.com" for i in range(n_users)]

    data = []
    for _ in range(rows):
        # Random timestamp within the time window
        ts = start + timedelta(minutes=random.randint(0, 60 * 24 * days))
        # Picks a user and a city (with lat/lon), UA, device, and ASN
        u = random.choice(users)
        city, lat, lon = random.choice(CITIES)
        ua = random.choice(UAS)
        dev = f"dev-{random.randint(1, 30)}"
        asn = random.choice(ASNS)
        # Label is benign by default
        data.append([ts, u, city, lat, lon, ua, dev, asn, "benign"])

    # Pack into a DataFrame and keep events in time order
    df = pd.DataFrame(
        data,
        columns=[
            "timestamp", "user_id", "city", "lat", "lon",
            "user_agent", "device_id", "asn", "label"
        ],
    )
    df.sort_values("timestamp", inplace=True)

    # Choose some rows to mutate into attacks
    attack_idx = np.random.choice(df.index, size=min(20, len(df)), replace=False)
    half = len(attack_idx) // 2

    # Attack type 1: impossible travel
    # Duplicates a chosen event for the same user ~30 mins later but far away (NY/Sydney)
    for idx in attack_idx[:half]:
        row = df.loc[idx].copy()
        row["timestamp"] = df.at[idx, "timestamp"] + timedelta(minutes=30)
        city, lat, lon = random.choice([CITIES[3], CITIES[4]])  # big jump: New York or Sydney
        row["city"], row["lat"], row["lon"], row["label"] = city, lat, lon, "attack"
        # Append the injected attack row
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    # Attack type 2: device/UA switch + rare ASN
    # Flips UA/device and assign an ASN we never use elsewhere to make it "rare"
    for idx in attack_idx[half:]:
        # Forces a change in UA (pick any different UA)
        df.at[idx, "user_agent"] = random.choice([x for x in UAS if x != df.at[idx, "user_agent"]])
        # New device range to make the change obvious
        df.at[idx, "device_id"] = f"dev-{100 + random.randint(1, 30)}"
        # ASN that won't appear in the benign pool
        df.at[idx, "asn"] = "AS9999"
        # Mark as attack
        df.at[idx, "label"] = "attack"

    # Time-sort and reset the integer index
    return df.sort_values("timestamp").reset_index(drop=True)
