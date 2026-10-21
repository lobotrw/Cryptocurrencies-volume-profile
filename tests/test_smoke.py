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


def test_interval_choices_follow_period(monkeypatch):
    at = run("BTC-USD", "10y", "1d", monkeypatch)
    assert "1h" not in at.selectbox[2].options       # Yahoo has no 1h data beyond 730 days
    assert not at.exception
