"""Characterize nexuscore.core.datetime behaviour across a fixed input battery.

Run under an interpreter that has the compiled ``nexuscore`` importable and dump
JSON to stdout.  Used to prove the pandas removal is behaviour-preserving:
capture once against the pandas-backed build, once against the new build, diff.

    python tools/characterize_datetime.py > golden.json
"""

import datetime as dt
import json

from nexuscore.core import datetime as nd


UTC = dt.timezone.utc
JST = dt.timezone(dt.timedelta(hours=9))


def _cases():
    """(label, value) pairs covering every accepted input shape."""
    cases = [
        ("int_secs_like", 1700000000),
        ("int_nanos", 1700000000000000000),
        ("int_zero", 0),
        ("float_secs_like", 1700000000.0),
        ("float_frac", 1700000000.5),
        ("str_iso_z", "2024-01-01T00:00:00Z"),
        ("str_iso_ns", "2024-01-01T00:00:00.123456789Z"),
        ("str_iso_us", "2024-01-01T00:00:00.123456Z"),
        ("str_iso_ms", "2024-01-01T00:00:00.123Z"),
        ("str_iso_offset", "2024-01-01T09:00:00+09:00"),
        ("str_iso_naive", "2024-01-01T00:00:00"),
        ("str_date_only", "2024-01-01"),
        ("str_loose_slash", "2024/01/01 12:30"),
        ("str_loose_verbose", "Jan 1 2024 12:30pm"),
        ("str_garbage", "not a date"),
        ("str_empty", ""),
        ("bool_true", True),
        ("list_bad", [1, 2]),
        ("date_obj", dt.date(2024, 1, 1)),
        ("dt_naive", dt.datetime(2024, 1, 1)),
        ("dt_utc", dt.datetime(2024, 1, 1, tzinfo=UTC)),
        ("dt_jst", dt.datetime(2024, 1, 1, 9, tzinfo=JST)),
        ("dt_micros", dt.datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)),
        ("dt_pre_epoch", dt.datetime(1969, 12, 31, 23, 59, 59, tzinfo=UTC)),
        ("dt_far_future", dt.datetime(2200, 6, 15, 12, 34, 56, 789012, tzinfo=UTC)),
    ]
    try:
        import pandas as pd
    except ImportError:
        pass
    else:
        cases += [
            ("pdts_ns", pd.Timestamp("2024-01-01T00:00:00.123456789Z")),
            ("pdts_naive", pd.Timestamp("2024-01-01")),
            ("pdts_jst", pd.Timestamp("2024-01-01T09:00:00+09:00")),
        ]
    return cases


def _call(fn, *args):
    try:
        out = fn(*args)
    except Exception as exc:  # noqa: BLE001 - the exception type IS the behaviour
        return f"!{type(exc).__name__}"
    if isinstance(out, dt.datetime):
        # Normalise pandas.Timestamp repr differences away; compare the instant.
        return f"dt:{out.isoformat()}"
    return out


def main():
    result = {}

    for label, value in _cases():
        result[f"dt_to_unix_nanos/{label}"] = _call(nd.dt_to_unix_nanos, value)
        result[f"maybe_dt_to_unix_nanos/{label}"] = _call(
            nd.maybe_dt_to_unix_nanos, value
        )
        result[f"time_object_to_dt/{label}"] = _call(nd.time_object_to_dt, value)
        result[f"is_tz_aware/{label}"] = _call(nd.is_tz_aware, value)
        result[f"is_tz_naive/{label}"] = _call(nd.is_tz_naive, value)
        result[f"ensure_pydatetime_utc/{label}"] = _call(nd.ensure_pydatetime_utc, value)
        if isinstance(value, dt.datetime):
            result[f"as_utc_timestamp/{label}"] = _call(nd.as_utc_timestamp, value)
            result[f"is_datetime_utc/{label}"] = _call(nd.is_datetime_utc, value)
            result[f"format_iso8601/{label}"] = _call(nd.format_iso8601, value, True)
            result[f"format_iso8601_ms/{label}"] = _call(nd.format_iso8601, value, False)

    result["maybe_dt_to_unix_nanos/none"] = _call(nd.maybe_dt_to_unix_nanos, None)
    result["time_object_to_dt/none"] = _call(nd.time_object_to_dt, None)
    result["ensure_pydatetime_utc/none"] = _call(nd.ensure_pydatetime_utc, None)
    result["maybe_unix_nanos_to_dt/none"] = _call(nd.maybe_unix_nanos_to_dt, None)
    result["format_optional_iso8601/none"] = _call(nd.format_optional_iso8601, None)

    for nanos in (0, 1, 999_999_999, 1_704_067_200_123_456_789, 2**63):
        result[f"unix_nanos_to_dt/{nanos}"] = _call(nd.unix_nanos_to_dt, nanos)
        result[f"maybe_unix_nanos_to_dt/{nanos}"] = _call(nd.maybe_unix_nanos_to_dt, nanos)
        result[f"unix_nanos_to_iso8601/{nanos}"] = _call(nd.unix_nanos_to_iso8601, nanos, True)
        result[f"unix_nanos_to_iso8601_ms/{nanos}"] = _call(
            nd.unix_nanos_to_iso8601, nanos, False
        )

    for secs in (0.0, 1.5, -1.0, 1e-9, 86400.0):
        result[f"secs_to_nanos/{secs}"] = _call(nd.secs_to_nanos, secs)
        result[f"secs_to_millis/{secs}"] = _call(nd.secs_to_millis, secs)
    for millis in (0.0, 1.5, -1.0, 1000.0):
        result[f"millis_to_nanos/{millis}"] = _call(nd.millis_to_nanos, millis)
    for micros in (0.0, 1.5, -1.0, 1000.0):
        result[f"micros_to_nanos/{micros}"] = _call(nd.micros_to_nanos, micros)
    for nanos in (0, 1, 1_500_000_000, 2**63):
        result[f"nanos_to_secs/{nanos}"] = _call(nd.nanos_to_secs, nanos)
        result[f"nanos_to_millis/{nanos}"] = _call(nd.nanos_to_millis, nanos)
        result[f"nanos_to_micros/{nanos}"] = _call(nd.nanos_to_micros, nanos)

    pairs = [
        (None, None),
        (None, "2024-01-01T00:00:00Z"),
        ("2024-01-01T00:00:00Z", None),
        ("2024-01-01T00:00:00Z", "2024-06-01T00:00:00Z"),
        (dt.datetime(2024, 1, 1, tzinfo=UTC), "2023-01-01T00:00:00Z"),
    ]
    for i, (a, b) in enumerate(pairs):
        result[f"max_date/{i}"] = _call(nd.max_date, a, b)
        result[f"min_date/{i}"] = _call(nd.min_date, a, b)

    json.dump(result, __import__("sys").stdout, indent=1, sort_keys=True, default=str)


if __name__ == "__main__":
    main()
