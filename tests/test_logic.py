"""Offline tests for the volume-profile logic (vprofile.py) and the walk-forward mode."""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import vprofile as vp  # noqa: E402

HARNESS = str(ROOT / "tests" / "synthetic_app.py")


def bars(rows):
    return pd.DataFrame(rows, columns=["Low", "High", "Close", "Volume"])


def test_volume_is_spread_over_low_high_range_and_conserved():
    d = bars([[100, 110, 105, 1000.0], [100, 110, 101, 500.0]])
    edges, centers, prof = vp.volume_profile(d, n_bins=10)
    assert prof.sum() == pytest.approx(1500)
    assert np.allclose(prof, 150)               # uniform over the range, not piled on the close bin


def test_flat_bar_goes_to_close_bin():
    d = bars([[100, 110, 100, 10.0], [105, 105, 105, 99.0]])
    edges, centers, prof = vp.volume_profile(d, n_bins=10)
    assert prof.sum() == pytest.approx(109)
    assert prof[5] == pytest.approx(1 + 99)


def test_no_empty_bins_when_bars_overlap():
    rng = np.random.default_rng(0)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 365)))
    d = bars(np.c_[c * 0.97, c * 1.03, c, np.ones(365)])
    _, _, prof = vp.volume_profile(d, 99)
    assert (prof > 0).all()


def test_valid_intervals_respect_yahoo_limits():
    for period in ("2y", "5y", "10y"):
        assert "1h" not in vp.VALID_INTERVALS[period]
    assert set(vp.PERIODS) == set(vp.VALID_INTERVALS) and len(vp.PERIODS) == len(set(vp.PERIODS))


def test_ordinal_labels():
    assert [vp.ordinal(n) for n in (1, 2, 3, 11, 22, 94)] == ["1st", "2nd", "3rd", "11th", "22nd", "94th"]


def run(env, walk_forward=True, coin_units=False):
    os.environ["VP_SYNTH"] = env
    at = AppTest.from_file(HARNESS, default_timeout=120)
    at.run()
    if coin_units:
        at.radio[0].set_value("Coin units (USD volume ÷ close)").run()
    if walk_forward:
        at.radio[1].set_value("Walk-forward check").run()
    return at


def test_walk_forward_levels_ignore_later_data():
    """No lookahead: in walk-forward mode, changing bars after the formation period must not move the levels."""
    a, b = run("base"), run("alt")
    assert not a.exception and not b.exception
    assert a.caption[0].value == b.caption[0].value
    assert "levels above the 94th percentile" in a.caption[0].value
    # sanity: the altered future really is different (full-data levels do change)
    assert run("base", walk_forward=False).caption[0].value != run("alt", walk_forward=False).caption[0].value


def test_current_mode_and_coin_units_run():
    at = run("base", walk_forward=False, coin_units=True)
    assert not at.exception, [e.message for e in at.exception]


def test_no_data_shows_error_not_crash():
    at = run("empty", walk_forward=False)
    assert not at.exception
    assert at.error
