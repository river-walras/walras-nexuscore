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

import time
from datetime import datetime
from datetime import timedelta

import pytest
from datetime import timezone
from zoneinfo import ZoneInfo

from nexuscore import LiveClock, TimeEvent


class TestLiveClock:
    def setup_method(self):
        # Fixture Setup
        self.handler = []
        self.clock = LiveClock()
        self.clock.register_default_handler(self.handler.append)

    def teardown_method(self):
        self.clock.cancel_timers()

    def test_instantiated_clock(self):
        # Arrange, Act, Assert
        assert self.clock.timer_count == 0

    def test_timestamp_is_monotonic(self):
        # Arrange, Act
        result1 = self.clock.timestamp()
        result2 = self.clock.timestamp()
        result3 = self.clock.timestamp()
        result4 = self.clock.timestamp()
        result5 = self.clock.timestamp()

        # Assert
        assert isinstance(result1, float)
        assert result1 > 0.0
        assert result5 >= result4
        assert result4 >= result3
        assert result3 >= result2
        assert result2 >= result1

    def test_timestamp_ms_is_monotonic(self):
        # Arrange, Act
        result1 = self.clock.timestamp_ms()
        result2 = self.clock.timestamp_ms()
        result3 = self.clock.timestamp_ms()
        result4 = self.clock.timestamp_ms()
        result5 = self.clock.timestamp_ms()

        # Assert
        assert isinstance(result1, int)
        assert result1 > 0
        assert result5 >= result4
        assert result4 >= result3
        assert result3 >= result2
        assert result2 >= result1

    def test_timestamp_us_is_monotonic(self):
        # Arrange, Act
        result1 = self.clock.timestamp_us()
        result2 = self.clock.timestamp_us()
        result3 = self.clock.timestamp_us()
        result4 = self.clock.timestamp_us()
        result5 = self.clock.timestamp_us()

        # Assert
        assert isinstance(result1, int)
        assert result1 > 0
        assert result5 >= result4
        assert result4 >= result3
        assert result3 >= result2
        assert result2 >= result1

    def test_timestamp_ns_is_monotonic(self):
        # Arrange, Act
        result1 = self.clock.timestamp_ns()
        result2 = self.clock.timestamp_ns()
        result3 = self.clock.timestamp_ns()
        result4 = self.clock.timestamp_ns()
        result5 = self.clock.timestamp_ns()

        # Assert
        assert isinstance(result1, int)
        assert result1 > 0
        assert result5 >= result4
        assert result4 >= result3
        assert result3 >= result2
        assert result2 >= result1

    def test_utc_now(self):
        # Arrange, Act
        result = self.clock.utc_now()

        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_local_now(self):
        # Arrange, Act
        result = self.clock.local_now(ZoneInfo("Australia/Sydney"))

        # Assert
        assert isinstance(result, datetime)
        assert str(result).endswith("+11:00") or str(result).endswith("+10:00")

    def test_set_time_alert_in_the_past(self):
        # Arrange
        name = "TEST_ALERT"
        interval = timedelta(hours=1)
        alert_time = self.clock.utc_now() - interval

        # Act - will fire immediately
        self.clock.set_time_alert(name, alert_time)
        time.sleep(1.0)

        # Assert
        assert len(self.handler) == 1
        assert isinstance(self.handler[0], TimeEvent)

    def test_set_time_alert(self):
        # Arrange
        name = "TEST_ALERT"
        interval = timedelta(milliseconds=100)
        alert_time = self.clock.utc_now() + interval

        # Act
        self.clock.set_time_alert(name, alert_time)
        time.sleep(1.0)

        # Assert
        assert len(self.handler) == 1
        assert isinstance(self.handler[0], TimeEvent)

    def test_cancel_time_alert(self):
        # Arrange
        name = "TEST_ALERT"
        interval = timedelta(milliseconds=300)
        alert_time = self.clock.utc_now() + interval

        self.clock.set_time_alert(name, alert_time)

        # Act
        self.clock.cancel_timer(name)

        # Assert
        assert self.clock.timer_count == 0
        assert len(self.handler) == 0

    def test_set_multiple_time_alerts(self):
        # Arrange
        alert_time1 = self.clock.utc_now() + timedelta(milliseconds=200)
        alert_time2 = self.clock.utc_now() + timedelta(milliseconds=300)

        # Act
        self.clock.set_time_alert("TEST_ALERT1", alert_time1)
        self.clock.set_time_alert("TEST_ALERT2", alert_time2)
        time.sleep(2.0)

        # Assert
        assert self.clock.timer_count == 0
        assert len(self.handler) >= 2
        assert isinstance(self.handler[0], TimeEvent)
        assert isinstance(self.handler[1], TimeEvent)

    def test_set_timer_with_immediate_start_time(self):
        # Arrange
        name = "TEST_TIMER"

        # Act
        self.clock.set_timer(
            name=name,
            interval=timedelta(milliseconds=100),
            start_time=None,
            stop_time=None,
        )

        time.sleep(2.0)

        # Assert
        assert self.clock.timer_names == [name]
        assert isinstance(self.handler[0], TimeEvent)

    def test_set_timer(self):
        # Arrange
        name = "TEST_TIMER"
        interval = timedelta(milliseconds=100)
        start_time = self.clock.utc_now() + interval

        # Act
        self.clock.set_timer(
            name=name,
            interval=interval,
            start_time=start_time,
            stop_time=None,
        )

        time.sleep(2.0)

        # Assert
        assert self.clock.timer_names == [name]
        assert len(self.handler) > 0
        assert isinstance(self.handler[0], TimeEvent)

    def test_set_timer_with_stop_time(self):
        # Arrange
        name = "TEST_TIMER"
        interval = timedelta(milliseconds=100)
        start_time = self.clock.utc_now()
        stop_time = start_time + interval

        # Act
        self.clock.set_timer(
            name=name,
            interval=interval,
            start_time=start_time,
            stop_time=stop_time,
        )

        time.sleep(2.0)

        # Assert
        assert self.clock.timer_count == 0
        assert len(self.handler) > 0
        assert isinstance(self.handler[0], TimeEvent)

    def test_cancel_timer(self):
        # Arrange
        name = "TEST_TIMER"
        interval = timedelta(milliseconds=100)

        self.clock.set_timer(name=name, interval=interval)

        # Act
        time.sleep(0.3)
        self.clock.cancel_timer(name)
        time.sleep(1.0)

        # Assert
        assert self.clock.timer_count == 0
        assert len(self.handler) <= 6

    def test_set_repeating_timer(self):
        # Arrange
        name = "TEST_TIMER"
        interval = timedelta(milliseconds=100)
        start_time = self.clock.utc_now()

        # Act
        self.clock.set_timer(
            name=name,
            interval=interval,
            start_time=start_time,
            stop_time=None,
        )

        time.sleep(2.0)

        # Assert
        assert len(self.handler) > 0
        assert isinstance(self.handler[0], TimeEvent)

    def test_cancel_repeating_timer(self):
        # Arrange
        name = "TEST_TIMER"
        interval = timedelta(milliseconds=100)
        start_time = self.clock.utc_now()
        stop_time = start_time + timedelta(seconds=5)

        self.clock.set_timer(
            name=name,
            interval=interval,
            start_time=start_time,
            stop_time=stop_time,
        )

        # Act
        time.sleep(0.3)
        self.clock.cancel_timer(name)
        time.sleep(1.0)

        # Assert
        assert len(self.handler) <= 6

    def test_set_two_repeating_timers(self):
        # Arrange
        interval = timedelta(milliseconds=100)
        start_time = self.clock.utc_now() + timedelta(milliseconds=100)

        # Act
        self.clock.set_timer(
            name="TEST_TIMER1",
            interval=interval,
            start_time=start_time,
            stop_time=None,
        )

        self.clock.set_timer(
            name="TEST_TIMER2",
            interval=interval,
            start_time=start_time,
            stop_time=None,
        )

        time.sleep(1.0)

        # Assert
        assert len(self.handler) >= 2

    def test_cython_validation_prevents_rust_panic_live_clock_time_alert(self):
        # Arrange
        clock = LiveClock()
        clock.register_default_handler(lambda event: None)  # Add default handler
        current_time_ns = clock.timestamp_ns()
        past_alert_time = current_time_ns - 1_000_000_000  # 1 second in the past

        # Act & Assert - Cython validation should catch this before Rust
        with pytest.raises(ValueError) as exc_info:
            clock.set_time_alert_ns(
                name="past_alert_live",
                alert_time_ns=past_alert_time,
                allow_past=False,
            )

        assert "would be in the past" in str(exc_info.value) or "was in the past" in str(
            exc_info.value,
        )
        assert "past_alert_live" in str(exc_info.value)
        assert clock.timer_count == 0  # No timer should be created

    def test_cython_validation_prevents_rust_panic_live_clock_timer(self):
        # Arrange
        clock = LiveClock()
        clock.register_default_handler(lambda event: None)  # Add default handler
        current_time_ns = clock.timestamp_ns()
        past_start_time = current_time_ns - 2_000_000_000  # 2 seconds in the past
        interval = 500_000_000  # 0.5 second interval

        # Act & Assert - Next event would be 1.5 seconds ago, still in past
        with pytest.raises(ValueError) as exc_info:
            clock.set_timer_ns(
                name="past_timer_live",
                interval_ns=interval,
                start_time_ns=past_start_time,
                stop_time_ns=0,
                allow_past=False,
                fire_immediately=False,
            )

        assert "would be in the past" in str(exc_info.value)
        assert "past_timer_live" in str(exc_info.value)
        assert clock.timer_count == 0  # No timer should be created

    def test_cython_validation_allows_zero_start_time_live_clock(self):
        # Arrange
        clock = LiveClock()
        clock.register_default_handler(lambda event: None)  # Add default handler

        # Act - Zero start time should always work (uses current time)
        clock.set_timer_ns(
            name="zero_start_live",
            interval_ns=100_000_000,  # 0.1 second interval
            start_time_ns=0,  # Zero start time
            stop_time_ns=0,
            allow_past=False,
            fire_immediately=True,
        )

        # Assert
        assert clock.timer_count == 1
        assert "zero_start_live" in clock.timer_names

        # Cleanup
        clock.cancel_timer("zero_start_live")
