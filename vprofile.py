"""Volume-profile calculations (pure functions, no Streamlit)."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Valid Yahoo period -> interval choices (1h only within Yahoo's 730-day intraday limit,
# and the interval must be shorter than the period).
VALID_INTERVALS = {
    "1d":  ["1h"],
    "5d":  ["1h", "1d"],
    "1mo": ["1h", "1d", "5d", "1wk"],
    "3mo": ["1h", "1d", "5d", "1wk", "1mo"],
    "6mo": ["1h", "1d", "5d", "1wk", "1mo"],
    "1y":  ["1d", "1h", "5d", "1wk", "1mo", "3mo"],
    "2y":  ["1d", "5d", "1wk", "1mo", "3mo"],
    "5y":  ["1d", "5d", "1wk", "1mo", "3mo"],
    "10y": ["1d", "5d", "1wk", "1mo", "3mo"],
}
PERIODS = ["1y", "1d", "5d", "1mo", "3mo", "6mo", "2y", "5y", "10y"]   # first = default


def volume_profile(data: pd.DataFrame, n_bins: int = 99, volume: pd.Series | None = None):
    """Volume per price bin, spreading each bar's volume uniformly over its Low..High range.

    Returns (edges, centers, profile). A bar with High == Low puts all its volume in the
    bin of its close. The price range spans min(Low)..max(High) so every traded price is covered.
    """
    low = data["Low"].to_numpy(float)
    high = data["High"].to_numpy(float)
    close = data["Close"].to_numpy(float)
    vol = (data["Volume"] if volume is None else volume).to_numpy(float)
    ok = ~(np.isnan(low) | np.isnan(high) | np.isnan(vol))
    low, high, close, vol = low[ok], high[ok], close[ok], vol[ok]
    lo, hi = float(np.nanmin(low)), float(np.nanmax(high))
    edges = np.linspace(lo, hi, n_bins + 1)
    rng = high - low
    flat = rng <= 0
    # fraction of each bar's [low, high] range lying below each edge -> per-bin share
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.clip((edges[None, :] - low[:, None]) / rng[:, None], 0.0, 1.0)
    share = np.diff(frac, axis=1)
    if flat.any():
        idx = np.clip(np.searchsorted(edges, close[flat], side="right") - 1, 0, n_bins - 1)
        share[flat] = 0.0
        share[np.where(flat)[0], idx] = 1.0
    profile = (share * vol[:, None]).sum(axis=0)
    centers = (edges[:-1] + edges[1:]) / 2
    return edges, centers, profile


def high_volume_levels(centers, profile, pct: float):
    """Bin centres whose volume exceeds the ``pct`` percentile of bin volumes."""
    cutoff = float(np.percentile(profile, pct))
    return cutoff, [float(c) for c, v in zip(centers, profile) if v > cutoff]


def ordinal(n: int) -> str:
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
