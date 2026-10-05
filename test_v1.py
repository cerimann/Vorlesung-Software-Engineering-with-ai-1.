from unittest.mock import MagicMock

import pandas as pd
import pytest

import v1


def test_month_bounds_cover_whole_month_without_overlap():
    jan_start, jan_end = v1.month_bounds(pd.Period("2009-01", freq="M"))
    feb_start, _ = v1.month_bounds(pd.Period("2009-02", freq="M"))
    assert jan_start == 1230768000  # 2009-01-01T00:00:00Z
    assert jan_end == feb_start - 1


def test_month_bounds_handle_leap_february():
    start, end = v1.month_bounds(pd.Period("2024-02", freq="M"))
    assert end - start + 1 == 29 * 24 * 3600


def test_fetch_month_returns_total_and_sends_filter():
    session = MagicMock()
    session.get.return_value.ok = True
    session.get.return_value.json.return_value = {"total": 15823}

    assert v1.fetch_month(session, pd.Period("2009-01", freq="M")) == 15823
    params = session.get.call_args.kwargs["params"]
    assert params["filter"] == "total"
    assert params["site"] == "stackoverflow"


def test_fetch_month_raises_on_quota_exhausted():
    session = MagicMock()
    session.get.return_value.ok = False
    session.get.return_value.json.return_value = {
        "error_id": 502, "error_message": "too many requests from this IP",
    }
    with pytest.raises(RuntimeError, match="quota"):
        v1.fetch_month(session, pd.Period("2009-01", freq="M"))


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache.csv"
    v1.save_cache({"2009-02": 2, "2009-01": 1}, path)
    assert v1.load_cache(path) == {"2009-01": 1, "2009-02": 2}


def test_fetch_range_only_requests_missing_months(tmp_path, monkeypatch):
    path = tmp_path / "cache.csv"
    v1.save_cache({"2009-01": 1}, path)
    requested = []
    monkeypatch.setattr(v1, "fetch_month", lambda s, p, k: requested.append(str(p)) or 7)
    monkeypatch.setattr(v1.time, "sleep", lambda _: None)

    counts = v1.fetch_range("2009-01", "2009-03", cache=path)

    assert requested == ["2009-02", "2009-03"]
    assert counts == {"2009-01": 1, "2009-02": 7, "2009-03": 7}


def test_build_series_moving_average_needs_full_window():
    counts = {str(p): i for i, p in enumerate(pd.period_range("2010-01", "2011-12", freq="M"))}
    df = v1.build_series(counts, "2010-01", "2011-12")

    assert df["ma12"].iloc[:11].isna().all()
    assert df["ma12"].iloc[11] == pytest.approx(sum(range(12)) / 12)
    assert df["ma12"].iloc[-1] == pytest.approx(sum(range(12, 24)) / 12)


def test_build_series_rejects_gaps():
    with pytest.raises(ValueError, match="2010-02"):
        v1.build_series({"2010-01": 1, "2010-03": 1}, "2010-01", "2010-03")
