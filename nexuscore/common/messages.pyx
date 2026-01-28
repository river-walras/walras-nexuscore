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

from libc.stdint cimport uint64_t

from nexuscore.core.correctness cimport Condition
from nexuscore.core.message cimport Command
from nexuscore.core.message cimport Event
from nexuscore.core.rust.common cimport ComponentState
from nexuscore.core.uuid cimport UUID4
from nexuscore.model.identifiers cimport ComponentId
from nexuscore.model.identifiers cimport Identifier
from nexuscore.model.identifiers cimport TraderId


cdef dict _COMPONENT_STATE_MAP = {
    "PRE_INITIALIZED": ComponentState.PRE_INITIALIZED,
    "READY": ComponentState.READY,
    "STARTING": ComponentState.STARTING,
    "RUNNING": ComponentState.RUNNING,
    "STOPPING": ComponentState.STOPPING,
    "STOPPED": ComponentState.STOPPED,
    "RESUMING": ComponentState.RESUMING,
    "DEGRADING": ComponentState.DEGRADING,
    "DEGRADED": ComponentState.DEGRADED,
    "FAULTING": ComponentState.FAULTING,
    "FAULTED": ComponentState.FAULTED,
    "DISPOSING": ComponentState.DISPOSING,
    "DISPOSED": ComponentState.DISPOSED,
}

cdef dict _COMPONENT_STATE_STR_MAP = {v: k for k, v in _COMPONENT_STATE_MAP.items()}


cdef class ShutdownSystem(Command):
    """
    Represents a command to shut down a system and terminate the process.
    """

    def __init__(
        self,
        TraderId trader_id not None,
        Identifier component_id not None,
        UUID4 command_id not None,
        uint64_t ts_init,
        str reason = None,
        UUID4 correlation_id = None,
    ) -> None:
        super().__init__(command_id, ts_init, correlation_id)
        self.trader_id = trader_id
        self.component_id = component_id
        self.reason = reason
        self._command_id = command_id
        self._ts_init = ts_init

    def __eq__(self, Command other) -> bool:
        if other is None:
            return False
        return self._command_id == other.id

    def __hash__(self) -> int:
        return hash(self._command_id)

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"trader_id={self.trader_id.to_str()}, "
            f"component_id={self.component_id.to_str()}, "
            f"reason='{self.reason}', "
            f"command_id={self._command_id.to_str()})"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"trader_id={self.trader_id.to_str()}, "
            f"component_id={self.component_id.to_str()}, "
            f"reason='{self.reason}', "
            f"command_id={self._command_id.to_str()}, "
            f"ts_init={self._ts_init})"
        )

    @staticmethod
    cdef ShutdownSystem from_dict_c(dict values):
        Condition.not_none(values, "values")
        return ShutdownSystem(
            trader_id=TraderId(values["trader_id"]),
            component_id=ComponentId(values["component_id"]),
            reason=values["reason"],
            command_id=UUID4.from_str_c(values["command_id"]),
            ts_init=values["ts_init"],
            correlation_id=UUID4.from_str_c(values["correlation_id"]) if values.get("correlation_id") else None,
        )

    @staticmethod
    cdef dict to_dict_c(ShutdownSystem obj):
        Condition.not_none(obj, "obj")
        return {
            "type": "ShutdownSystem",
            "trader_id": obj.trader_id.to_str(),
            "component_id": obj.component_id.to_str(),
            "reason": obj.reason,
            "command_id": obj._command_id.to_str(),
            "ts_init": obj._ts_init,
        }

    @staticmethod
    def from_dict(dict values) -> ShutdownSystem:
        return ShutdownSystem.from_dict_c(values)

    @staticmethod
    def to_dict(ShutdownSystem obj):
        return ShutdownSystem.to_dict_c(obj)


cdef class ComponentStateChanged(Event):
    """
    Represents an event which includes information on the state of a component.
    """

    def __init__(
        self,
        TraderId trader_id not None,
        Identifier component_id not None,
        str component_type not None,
        ComponentState state,
        dict config not None,
        UUID4 event_id not None,
        uint64_t ts_event,
        uint64_t ts_init,
    ) -> None:
        self.trader_id = trader_id
        self.component_id = component_id
        self.component_type = component_type
        self.state = state
        self.config = config
        self._event_id = event_id
        self._ts_event = ts_event
        self._ts_init = ts_init

    def __eq__(self, Event other) -> bool:
        if other is None:
            return False
        return self._event_id == other.id

    def __hash__(self) -> int:
        return hash(self._event_id)

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"trader_id={self.trader_id.to_str()}, "
            f"component_id={self.component_id.to_str()}, "
            f"component_type={self.component_type}, "
            f"state={_COMPONENT_STATE_STR_MAP.get(self.state, str(self.state))}, "
            f"config={self.config}, "
            f"event_id={self._event_id.to_str()})"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"trader_id={self.trader_id.to_str()}, "
            f"component_id={self.component_id.to_str()}, "
            f"component_type={self.component_type}, "
            f"state={_COMPONENT_STATE_STR_MAP.get(self.state, str(self.state))}, "
            f"config={self.config}, "
            f"event_id={self._event_id.to_str()}, "
            f"ts_init={self._ts_init})"
        )

    @property
    def id(self) -> UUID4:
        return self._event_id

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init

    @staticmethod
    cdef ComponentStateChanged from_dict_c(dict values):
        Condition.not_none(values, "values")
        return ComponentStateChanged(
            trader_id=TraderId(values["trader_id"]),
            component_id=ComponentId(values["component_id"]),
            component_type=values["component_type"],
            state=_COMPONENT_STATE_MAP[values["state"]],
            config=values["config"],
            event_id=UUID4.from_str_c(values["event_id"]),
            ts_event=values["ts_event"],
            ts_init=values["ts_init"],
        )

    @staticmethod
    cdef dict to_dict_c(ComponentStateChanged obj):
        Condition.not_none(obj, "obj")
        return {
            "type": "ComponentStateChanged",
            "trader_id": obj.trader_id.to_str(),
            "component_id": obj.component_id.to_str(),
            "component_type": obj.component_type,
            "state": _COMPONENT_STATE_STR_MAP.get(obj.state, str(obj.state)),
            "config": obj.config,
            "event_id": obj._event_id.to_str(),
            "ts_event": obj._ts_event,
            "ts_init": obj._ts_init,
        }

    @staticmethod
    def from_dict(dict values) -> ComponentStateChanged:
        return ComponentStateChanged.from_dict_c(values)

    @staticmethod
    def to_dict(ComponentStateChanged obj):
        return ComponentStateChanged.to_dict_c(obj)
