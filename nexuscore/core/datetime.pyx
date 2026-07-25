# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
This module provides efficient functions for performing standard datetime related operations.

Functions include awareness/tz checks and conversions, as well as ISO 8601 (RFC 3339) conversion.
"""

import datetime as dt
import re

cimport cpython.datetime
from cpython.datetime cimport datetime
from cpython.datetime cimport datetime_tzinfo
from libc.stdint cimport uint64_t

from nexuscore.core.correctness cimport Condition


# UNIX epoch is the UTC time at 00:00:00 on 1/1/1970
# https://en.wikipedia.org/wiki/Unix_time
cdef datetime UNIX_EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

# Sub-second digits of an ISO 8601 time component. `datetime.fromisoformat`
# truncates these to microseconds, so they are stripped before parsing and
# re-applied afterwards to keep nanosecond resolution.
cdef object _ISO_FRACTION_RE = re.compile(r"(?<=\d{2}:\d{2}:\d{2})\.(\d+)")


cpdef uint64_t secs_to_nanos(double secs):
    if secs < 0:
        return 0
    return <uint64_t>(secs * 1_000_000_000.0)


cpdef uint64_t secs_to_millis(double secs):
    if secs < 0:
        return 0
    return <uint64_t>(secs * 1_000.0)


cpdef uint64_t millis_to_nanos(double millis):
    if millis < 0:
        return 0
    return <uint64_t>(millis * 1_000_000.0)


cpdef uint64_t micros_to_nanos(double micros):
    if micros < 0:
        return 0
    return <uint64_t>(micros * 1_000.0)


cpdef double nanos_to_secs(uint64_t nanos):
    return nanos / 1_000_000_000.0


cpdef uint64_t nanos_to_millis(uint64_t nanos):
    return nanos // 1_000_000


cpdef uint64_t nanos_to_micros(uint64_t nanos):
    return nanos // 1_000


cdef inline datetime _as_utc_datetime(datetime dt_obj):
    if datetime_tzinfo(dt_obj) is None:
        return dt_obj.replace(tzinfo=dt.timezone.utc)
    if datetime_tzinfo(dt_obj) is not dt.timezone.utc:
        return dt_obj.astimezone(dt.timezone.utc)
    return dt_obj


cdef inline object _dt_to_nanos_int(datetime dt_obj):
    # Exact UTC nanoseconds since the epoch, as a Python int (may be negative).
    # Integer arithmetic on the timedelta rather than `timestamp() * 1e9`: a
    # float64 holds only 2**53 integers exactly, so nanosecond magnitudes
    # (~1.7e18) lose their low digits.
    cdef object delta = _as_utc_datetime(dt_obj) - UNIX_EPOCH
    return (
        (delta.days * 86_400 + delta.seconds) * 1_000_000_000
        + delta.microseconds * 1_000
    )


cdef inline object _datetime_like_to_nanos_int(datetime dt_obj):
    # `pandas.Timestamp` subclasses `datetime` and exposes `.value` as UTC
    # nanoseconds since the epoch. Reading it duck-typed preserves nanosecond
    # inputs exactly without importing pandas.
    cdef object value = getattr(dt_obj, "value", None)
    if type(value) is int:
        return value
    return _dt_to_nanos_int(dt_obj)


cdef inline object _date_to_nanos_int(object date_obj):
    return _dt_to_nanos_int(
        dt.datetime(
            date_obj.year,
            date_obj.month,
            date_obj.day,
            tzinfo=dt.timezone.utc,
        )
    )


cdef object _parse_non_iso(str value):
    # Fall back to dateutil (the date parser pandas itself defers to) for the
    # formats ISO 8601 does not cover. Imported lazily: ISO 8601 handles the hot
    # paths, and dateutil costs ~3.5 MB resident that most processes never need.
    try:
        from dateutil.parser import parse as dateutil_parse
    except ImportError:
        raise ValueError(f"Invalid datetime string: {value!r}") from None

    try:
        return dateutil_parse(value)
    except (ValueError, OverflowError, TypeError):
        raise ValueError(f"Invalid datetime string: {value!r}") from None


cdef inline object _str_to_nanos_int(str value):
    cdef object match = _ISO_FRACTION_RE.search(value)
    cdef str digits = ""
    cdef str trimmed = value
    if match is not None:
        digits = match.group(1)
        trimmed = value[:match.start()] + value[match.end():]

    cdef datetime parsed
    try:
        parsed = dt.datetime.fromisoformat(trimmed)
    except ValueError:
        # dateutil resolves to microseconds; no fraction to re-apply.
        return _dt_to_nanos_int(_parse_non_iso(value))

    return _dt_to_nanos_int(parsed) + int(digits.ljust(9, "0")[:9])


cpdef unix_nanos_to_dt(uint64_t nanos):
    """
    Return the datetime (UTC) from the given UNIX timestamp (nanoseconds).

    Parameters
    ----------
    nanos : uint64_t
        The UNIX timestamp (nanoseconds) to convert.

    Returns
    -------
    datetime

    """
    return dt.datetime.fromtimestamp(nanos / 1e9, tz=dt.timezone.utc)


cpdef dt_to_unix_nanos(dt_value):
    """
    Return the UNIX timestamp (nanoseconds) from the given datetime (UTC).

    Parameters
    ----------
    dt_value : datetime | date | str | int | float
        The datetime to convert. Integers and floats are interpreted as
        nanoseconds since the epoch.

    Returns
    -------
    uint64_t

    Warnings
    --------
    Nanosecond precision is preserved for ``pandas.Timestamp`` inputs and for
    ISO 8601 strings carrying more than six fractional digits. Plain Python
    ``datetime`` objects only carry microseconds.

    """
    Condition.not_none(dt_value, "dt")

    # `datetime` before `date`: the former subclasses the latter.
    if isinstance(dt_value, datetime):
        return <uint64_t>_datetime_like_to_nanos_int(dt_value)

    if isinstance(dt_value, dt.date):
        return <uint64_t>_date_to_nanos_int(dt_value)

    if isinstance(dt_value, (int, float)):
        return <uint64_t>int(dt_value)

    if isinstance(dt_value, str):
        return <uint64_t>_str_to_nanos_int(dt_value)

    raise TypeError(f"Unsupported datetime type: {type(dt_value)}")


cpdef str unix_nanos_to_iso8601(uint64_t unix_nanos, bint nanos_precision = True):
    """
    Convert the given `unix_nanos` to an ISO 8601 (RFC 3339) format string.

    Parameters
    ----------
    unix_nanos : int
        The UNIX timestamp (nanoseconds) to be converted.
    nanos_precision : bool, default True
        If True, use nanosecond precision. If False, use millisecond precision.

    Returns
    -------
    str

    """
    cdef uint64_t secs = unix_nanos // 1_000_000_000
    cdef uint64_t frac = unix_nanos % 1_000_000_000
    cdef str base = dt.datetime.fromtimestamp(secs, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    if nanos_precision:
        return f"{base}.{frac:09d}Z"
    return f"{base}.{frac // 1_000_000:03d}Z"


cpdef str format_iso8601(datetime dt_value, bint nanos_precision = True):
    """
    Format the given datetime as an ISO 8601 (RFC 3339) specification string.

    Parameters
    ----------
    dt_value : datetime
        The datetime to format.
    nanos_precision : bool, default True
        If True, use nanosecond precision. If False, use millisecond precision.

    Returns
    -------
    str

    """
    Condition.not_none(dt_value, "dt")

    cdef uint64_t nanos = dt_to_unix_nanos(dt_value)
    return unix_nanos_to_iso8601(nanos, nanos_precision)


cpdef str format_optional_iso8601(datetime dt_value, bint nanos_precision = True):
    """
    Format the given optional datetime as an ISO 8601 (RFC 3339) specification string.

    If value is `None` then will return the string "None".

    Parameters
    ----------
    dt_value : datetime, optional
        The datetime to format.
    nanos_precision : bool, default True
        If True, use nanosecond precision. If False, use millisecond precision.

    Returns
    -------
    str

    """
    if dt_value is None:
        return str(None)

    return format_iso8601(dt_value, nanos_precision)


cpdef maybe_unix_nanos_to_dt(nanos):
    """
    Return the datetime (UTC) from the given UNIX timestamp (nanoseconds), or ``None``.

    If nanos is ``None``, then will return ``None``.

    Parameters
    ----------
    nanos : int, optional
        The UNIX timestamp (nanoseconds) to convert.

    Returns
    -------
    datetime or ``None``

    """
    if nanos is None:
        return None
    else:
        return dt.datetime.fromtimestamp(nanos / 1e9, tz=dt.timezone.utc)


cpdef maybe_dt_to_unix_nanos(dt_value):
    """
    Return the UNIX timestamp (nanoseconds) from the given datetime, or ``None``.

    If dt is ``None``, then will return ``None``.

    Parameters
    ----------
    dt_value : datetime, optional
        The datetime to convert.

    Returns
    -------
    int64 or ``None``

    Warnings
    --------
    If the input is not ``None`` then this function supports ``datetime`` inputs.

    """
    if dt_value is None:
        return None

    return <uint64_t>dt_to_unix_nanos(dt_value)


cpdef bint is_datetime_utc(datetime dt_value):
    """
    Return a value indicating whether the given timestamp is timezone aware UTC.

    Parameters
    ----------
    dt_value : datetime
        The datetime to check.

    Returns
    -------
    bool
        True if timezone aware UTC, else False.

    """
    Condition.not_none(dt_value, "dt")

    return datetime_tzinfo(dt_value) == dt.timezone.utc


cpdef bint is_tz_aware(time_object):
    """
    Return a value indicating whether the given object is timezone aware.

    Parameters
    ----------
    time_object : datetime, pd.Timestamp, pd.Series, pd.DataFrame
        The time object to check.

    Returns
    -------
    bool
        True if timezone aware, else False.

    """
    Condition.not_none(time_object, "time_object")

    # `pandas.Timestamp` subclasses `datetime`, so it lands here too.
    if isinstance(time_object, datetime):
        return datetime_tzinfo(time_object) is not None

    # pandas Series/DataFrame duck-type, checked without importing pandas.
    # Keyed on `tz_localize` rather than `index`: str and list also carry an
    # `index` attribute (the method), which would swallow them into this branch.
    cdef object index
    if hasattr(time_object, "tz_localize"):
        index = time_object.index
        return hasattr(index, "tz") or index.tz is not None

    raise ValueError(f"Cannot check timezone awareness of a {type(time_object)} object")


cpdef bint is_tz_naive(time_object):
    """
    Return a value indicating whether the given object is timezone naive.

    Parameters
    ----------
    time_object : datetime, pd.Timestamp, pd.DataFrame
        The time object to check.

    Returns
    -------
    bool
        True if object timezone naive, else False.

    """
    return not is_tz_aware(time_object)


cpdef datetime as_utc_timestamp(datetime dt_value):
    """
    Ensure the given timestamp is tz-aware UTC.

    Parameters
    ----------
    dt_value : datetime
        The timestamp to check.

    Returns
    -------
    datetime

    """
    Condition.not_none(dt_value, "dt")

    if dt_value.tzinfo is None:  # tz-naive
        return dt_value.replace(tzinfo=dt.timezone.utc)
    if dt_value.tzinfo != dt.timezone.utc:
        return dt_value.astimezone(dt.timezone.utc)
    return dt_value  # Already UTC


cpdef object as_utc_index(data):
    """
    Ensure the given data has a DateTimeIndex which is tz-aware UTC.

    Parameters
    ----------
    data : pandas.Series or pandas.DataFrame.
        The object to ensure is UTC.

    Returns
    -------
    pd.Series, pd.DataFrame or ``None``

    """
    Condition.not_none(data, "data")

    if data.empty:
        return data

    # Ensure the index is localized to UTC
    if data.index.tzinfo is None:  # tz-naive
        data = data.tz_localize(dt.timezone.utc)
    elif data.index.tzinfo != dt.timezone.utc:
        data = data.tz_convert(None).tz_localize(dt.timezone.utc)

    # Check if the index is in nanosecond resolution, convert if not.
    # Equivalent to `pandas.api.types.is_datetime64_ns_dtype` without importing
    # pandas: that predicate matches datetime64[ns] and datetime64[ns, <tz>].
    if not str(data.index.dtype).startswith("datetime64[ns"):
        data.index = data.index.astype("datetime64[ns, UTC]")

    return data


cpdef datetime time_object_to_dt(time_object):
    """
    Return the datetime (UTC) from the given UNIX timestamp as integer (nanoseconds), string or pd.Timestamp.

    Parameters
    ----------
    time_object : datetime | str | int | None
        The time object to convert.

    Returns
    -------
    datetime or ``None``
        Returns None if the input is None.

    """
    if time_object is None:
        return None

    # `pandas.Timestamp` subclasses `datetime`, so it lands here too.
    if isinstance(time_object, datetime):
        return as_utc_timestamp(time_object)

    if isinstance(time_object, dt.date):
        return dt.datetime(
            time_object.year,
            time_object.month,
            time_object.day,
            tzinfo=dt.timezone.utc,
        )

    # Unlike `dt_to_unix_nanos`, a bare number here means seconds.
    if isinstance(time_object, (int, float)):
        return dt.datetime.fromtimestamp(time_object, tz=dt.timezone.utc)

    if isinstance(time_object, str):
        return as_utc_timestamp(dt.datetime.fromisoformat(time_object))

    raise TypeError(f"Unsupported time object type: {type(time_object)}")



def max_date(date1: dt.datetime | str | int | None = None, date2: str | int | None = None) -> dt.datetime | None:
    """
    Return the maximum date as a datetime (UTC).

    Parameters
    ----------
    date1 : datetime | str | int | None, optional
        The first date to compare. Can be a string, integer (timestamp), or None. Default is None.
    date2 : datetime | str | int | None, optional
        The second date to compare. Can be a string, integer (timestamp), or None. Default is None.

    Returns
    -------
    datetime | None
        The maximum date, or None if both input dates are None.

    """
    if date1 is None and date2 is None:
        return None

    if date1 is None:
        return time_object_to_dt(date2)

    if date2 is None:
        return time_object_to_dt(date1)

    return max(time_object_to_dt(date1), time_object_to_dt(date2))


def min_date(date1: dt.datetime | str | int | None = None, date2: str | int | None = None) -> dt.datetime | None:
    """
    Return the minimum date as a datetime (UTC).

    Parameters
    ----------
    date1 : datetime | str | int | None, optional
        The first date to compare. Can be a string, integer (timestamp), or None. Default is None.
    date2 : datetime | str | int | None, optional
        The second date to compare. Can be a string, integer (timestamp), or None. Default is None.

    Returns
    -------
    datetime | None
        The minimum date, or None if both input dates are None.

    """
    if date1 is None and date2 is None:
        return None

    if date1 is None:
        return time_object_to_dt(date2)

    if date2 is None:
        return time_object_to_dt(date1)

    return min(time_object_to_dt(date1), time_object_to_dt(date2))


def ensure_pydatetime_utc(timestamp) -> dt.datetime | None:
    """
    Convert an optional ``pandas.Timestamp`` to a timezone-aware ``datetime`` in UTC.

    The underlying Python ``datetime`` type only supports microsecond precision. When
    the provided ``timestamp`` contains non-zero nanoseconds these **cannot** be
    represented and are therefore truncated to microseconds before the conversion
    takes place.  This avoids the "Discarding nonzero nanoseconds in conversion"
    ``UserWarning`` raised by pandas when calling :py:meth:`Timestamp.to_pydatetime`.

    Parameters
    ----------
    timestamp : pandas.Timestamp or datetime, optional
        The timestamp to convert. If ``None`` the function immediately returns
        ``None``.

    Returns
    -------
    datetime.datetime | None
        The converted timestamp with tz-info set to ``UTC`` or ``None`` if the
        input was ``None``.

    """
    if timestamp is None:
        return None

    # ``pandas.Timestamp`` duck-type, checked before the ``datetime`` branch it
    # would otherwise match: it carries nanoseconds a ``datetime`` cannot hold.
    # ``to_pydatetime`` emits a warning when nanoseconds are present, so we
    # truncate to the closest microsecond to silence it while keeping
    # deterministic behaviour.
    if hasattr(timestamp, "to_pydatetime"):
        if timestamp.nanosecond:
            timestamp = timestamp.floor("us")
        return timestamp.tz_convert("UTC").to_pydatetime()

    if isinstance(timestamp, datetime):
        return as_utc_timestamp(timestamp)

    raise TypeError(f"Unsupported timestamp type: {type(timestamp)}")
