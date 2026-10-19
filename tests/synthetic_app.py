# Harness: run main.py with yf.download patched to return synthetic OHLCV (offline).
# VP_SYNTH=empty -> empty frame; VP_SYNTH=alt -> same first 70% of bars, different later bars.
import os, runpy, sys
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fake_download(*a, **k):
    kind = os.environ.get("VP_SYNTH", "base")
    if kind == "empty":
        return pd.DataFrame()
    n = 300
    rng = np.random.default_rng(42)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    if kind == "alt":
        cut = int(n * 0.7)
        close[cut:] = close[cut:] * 3.0          # a completely different "future"
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    return pd.DataFrame({"Open": close, "High": close * 1.02, "Low": close * 0.98, "Close": close,
                         "Volume": rng.uniform(1e6, 2e6, n)}, index=idx)


_real_download = yf.download
yf.download = fake_download
import streamlit as st
st.cache_data.clear()   # the app caches downloads by (symbol, period, interval); each synthetic variant must be fresh
os.chdir(ROOT)
sys.path.insert(0, ROOT)
try:
    runpy.run_path(os.path.join(ROOT, "main.py"), run_name="__main__")
finally:
    yf.download = _real_download     # don't leak the patch into other tests in the same process
    st.cache_data.clear()
