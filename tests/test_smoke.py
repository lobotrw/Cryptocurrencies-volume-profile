"""Smoke tests (need network: Yahoo Finance). The app must never raise, including for
period/interval combinations Yahoo returns no data for."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "main.py")


def run(symbol, period, interval, monkeypatch):
    monkeypatch.chdir(ROOT)
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.selectbox[0].set_value(symbol)
    at.selectbox[1].set_value(period)
    at.selectbox[2].set_value(interval)
    at.run()
    return at


@pytest.mark.parametrize("symbol,period,interval", [
    ("BTC-USD", "1y", "1d"), ("ETH-USD", "5y", "1wk"), ("SOL-USD", "1mo", "1h"),
])
def test_normal_cases_draw_a_chart(symbol, period, interval, monkeypatch):
    at = run(symbol, period, interval, monkeypatch)
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error


@pytest.mark.parametrize("symbol,period,interval", [
    ("BTC-USD", "10y", "1h"),   # Yahoo: 1h data only for the last 730 days -> empty frame
    ("BTC-USD", "1d", "1d"),    # a single bar
])
def test_no_data_shows_error_instead_of_crash(symbol, period, interval, monkeypatch):
    at = run(symbol, period, interval, monkeypatch)
    assert not at.exception, [e.message for e in at.exception]
    assert at.error
