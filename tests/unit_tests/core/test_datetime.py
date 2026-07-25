"""Behaviour tests for `nexuscore.core.datetime` after the pandas removal.

`tests/golden_datetime.json` is a capture of the 0.3.0 module, which imported
pandas eagerly and routed most conversions through `pandas.Timestamp`. The
battery is replayed here and compared against that capture so the rewrite stays
behaviour-preserving; the handful of deliberate departures are listed in
`KNOWN_DIFFERENCES`.
"""

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

from nexuscore.core import datetime as nd

sys.path.insert(0, str(Path(__file__).parents[3] / "tools"))
from characterize_datetime import _cases, _call  # noqa: E402


GOLDEN = json.loads(
    (Path(__file__).parents[2] / "golden_datetime.json").read_text()
)

# Inputs whose behaviour intentionally changed when pandas.Timestamp stopped
# mediating the conversion. Both are inputs no caller passes deliberately.
KNOWN_DIFFERENCES = {
    # `pandas.Timestamp(True)` raised, so bools used to fall through to a
    # seconds heuristic. bool is an int subclass, so True now means 1 nanosecond.
    "dt_to_unix_nanos/bool_true": (1000000000, 1),
    "maybe_dt_to_unix_nanos/bool_true": (1000000000, 1),
    # `pandas.Timestamp("")` returned NaT, whose .value is INT64_MIN and
    # overflowed the uint64 cast. An empty string is now reported as invalid.
    "dt_to_unix_nanos/str_empty": ("!OverflowError", "!ValueError"),
    "maybe_dt_to_unix_nanos/str_empty": ("!OverflowError", "!ValueError"),
}


def _replay():
    """Re-run the characterization battery against the current build."""
    out = {}
    for label, value in _cases():
        out[f"dt_to_unix_nanos/{label}"] = _call(nd.dt_to_unix_nanos, value)
        out[f"maybe_dt_to_unix_nanos/{label}"] = _call(nd.maybe_dt_to_unix_nanos, value)
        out[f"time_object_to_dt/{label}"] = _call(nd.time_object_to_dt, value)
        out[f"is_tz_aware/{label}"] = _call(nd.is_tz_aware, value)
        out[f"ensure_pydatetime_utc/{label}"] = _call(nd.ensure_pydatetime_utc, value)
    return out


def test_battery_matches_pandas_era_golden():
    replayed = _replay()
    mismatches = {}
    for key, actual in replayed.items():
        if key not in GOLDEN:
            continue  # pandas-only case, absent when the capture ran without it
        expected = KNOWN_DIFFERENCES.get(key, (None, None))[1]
        if key in KNOWN_DIFFERENCES:
            if actual != expected:
                mismatches[key] = (f"documented change -> {expected}", actual)
        elif actual != GOLDEN[key]:
            mismatches[key] = (GOLDEN[key], actual)

    assert not mismatches, "\n".join(
        f"{k}: expected {exp!r}, got {act!r}" for k, (exp, act) in sorted(mismatches.items())
    )


def test_known_differences_are_still_reachable():
    """Guard against the golden and the exception list drifting apart."""
    for key, (old, _new) in KNOWN_DIFFERENCES.items():
        assert GOLDEN[key] == old, f"{key} no longer starts from {old!r}"


# --- nanosecond fidelity -------------------------------------------------


def test_iso_string_keeps_nanoseconds():
    # datetime.fromisoformat truncates to microseconds; the fractional digits
    # are re-applied so the low three survive.
    assert nd.dt_to_unix_nanos("2024-01-01T00:00:00.123456789Z") == 1704067200123456789


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-01-01T00:00:00.1Z", 1704067200100000000),
        ("2024-01-01T00:00:00.123Z", 1704067200123000000),
        ("2024-01-01T00:00:00.123456Z", 1704067200123456000),
        ("2024-01-01T00:00:00.000000001Z", 1704067200000000001),
        # More than nanosecond resolution truncates rather than overflowing.
        ("2024-01-01T00:00:00.1234567891Z", 1704067200123456789),
    ],
)
def test_fractional_second_widths(value, expected):
    assert nd.dt_to_unix_nanos(value) == expected


def test_conversion_uses_exact_integer_arithmetic():
    # `timestamp() * 1e9` cannot represent these magnitudes: float64 is exact
    # only to 2**53, so the low digits used to be wrong.
    value = dt.datetime(2200, 6, 15, 12, 34, 56, 789012, tzinfo=dt.timezone.utc)
    assert nd.dt_to_unix_nanos(value) == 7272419696789012000
    assert nd.dt_to_unix_nanos(value) % 1000 == 0

    micros = dt.datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=dt.timezone.utc)
    assert nd.dt_to_unix_nanos(micros) == 1704067200123456000


def test_timezone_normalisation():
    jst = dt.timezone(dt.timedelta(hours=9))
    assert nd.dt_to_unix_nanos(dt.datetime(2024, 1, 1, 9, tzinfo=jst)) == 1704067200000000000
    # tz-naive input is read as UTC
    assert nd.dt_to_unix_nanos(dt.datetime(2024, 1, 1)) == 1704067200000000000


def test_non_iso_string_uses_dateutil():
    assert nd.dt_to_unix_nanos("2024/01/01 12:30") == 1704112200000000000
    assert nd.dt_to_unix_nanos("Jan 1 2024 12:30pm") == 1704112200000000000


def test_invalid_string_raises_value_error():
    with pytest.raises(ValueError, match="Invalid datetime string"):
        nd.dt_to_unix_nanos("not a date")


def test_unsupported_type_raises_type_error():
    with pytest.raises(TypeError, match="Unsupported datetime type"):
        nd.dt_to_unix_nanos([1, 2])


def test_is_tz_aware_rejects_plain_sequences():
    # str and list both expose an `index` attribute; they must not be mistaken
    # for pandas objects.
    for value in ("2024-01-01T00:00:00Z", [1, 2]):
        with pytest.raises(ValueError, match="Cannot check timezone awareness"):
            nd.is_tz_aware(value)


# --- pandas interop, without importing pandas in the module --------------


try:
    import pandas as pd
except ImportError:  # pragma: no cover - exercised in the pandas-free CI leg
    pd = None

# Not `pytest.importorskip` at module scope: that would skip the whole file,
# including the import-cost guarantees below, which matter most without pandas.
requires_pandas = pytest.mark.skipif(pd is None, reason="pandas interop check")


@requires_pandas
def test_pandas_timestamp_nanoseconds_round_trip():
    ts = pd.Timestamp("2024-01-01T00:00:00.123456789Z")
    assert nd.dt_to_unix_nanos(ts) == 1704067200123456789
    assert nd.dt_to_unix_nanos(ts) == ts.value


@requires_pandas
def test_pandas_timestamp_tz_handling():
    assert nd.is_tz_aware(pd.Timestamp("2024-01-01T09:00:00+09:00")) is True
    assert nd.is_tz_aware(pd.Timestamp("2024-01-01")) is False


@requires_pandas
def test_ensure_pydatetime_utc_floors_nanoseconds():
    out = nd.ensure_pydatetime_utc(pd.Timestamp("2024-01-01T00:00:00.123456789Z"))
    assert out == dt.datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=dt.timezone.utc)
    assert type(out) is dt.datetime


@requires_pandas
def test_as_utc_index_without_pandas_import():
    frame = pd.DataFrame(
        {"v": [1, 2]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    out = nd.as_utc_index(frame)
    assert str(out.index.dtype) == "datetime64[ns, UTC]"
    assert nd.is_tz_aware(out) is True


# --- import-cost guarantees ----------------------------------------------


def _probe(code):
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_importing_nexuscore_does_not_import_pandas():
    out = _probe(
        "import sys, nexuscore;"
        "print(int('pandas' in sys.modules), int('numpy' in sys.modules))"
    )
    assert out == "0 0", f"pandas/numpy leaked into the import graph: {out}"


def test_dateutil_is_imported_lazily():
    out = _probe(
        "import sys;"
        "from nexuscore.core.datetime import dt_to_unix_nanos as f;"
        "f('2024-01-01T00:00:00.123456789Z');"
        "before = 'dateutil' in sys.modules;"
        "f('2024/01/01 12:30');"
        "print(int(before), int('dateutil' in sys.modules))"
    )
    assert out == "0 1", f"expected dateutil to load only on the non-ISO path: {out}"
