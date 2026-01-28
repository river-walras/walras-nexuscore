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

from cpython.datetime cimport datetime
from libc.stdint cimport uint64_t


cpdef unix_nanos_to_dt(uint64_t nanos)
cpdef uint64_t secs_to_nanos(double secs)
cpdef uint64_t secs_to_millis(double secs)
cpdef uint64_t millis_to_nanos(double millis)
cpdef uint64_t micros_to_nanos(double micros)
cpdef double nanos_to_secs(uint64_t nanos)
cpdef uint64_t nanos_to_millis(uint64_t nanos)
cpdef uint64_t nanos_to_micros(uint64_t nanos)
cpdef dt_to_unix_nanos(dt)
cpdef str unix_nanos_to_iso8601(uint64_t unix_nanos, bint nanos_precision=*)
cpdef str format_iso8601(datetime dt_value, bint nanos_precision=*)
cpdef str format_optional_iso8601(datetime dt_value, bint nanos_precision=*)
cpdef maybe_unix_nanos_to_dt(nanos)
cpdef maybe_dt_to_unix_nanos(dt_value)
cpdef bint is_datetime_utc(datetime dt_value)
cpdef bint is_tz_aware(time_object)
cpdef bint is_tz_naive(time_object)
cpdef datetime as_utc_timestamp(datetime dt_value)
cpdef object as_utc_index(time_object)
cpdef datetime time_object_to_dt(time_object)
