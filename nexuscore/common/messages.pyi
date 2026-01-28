from __future__ import annotations

from typing import Any

from nexuscore.core.message import Command, Event
from nexuscore.core.rust.common import ComponentState
from nexuscore.core.uuid import UUID4
from nexuscore.model.identifiers import ComponentId, Identifier, TraderId


class ShutdownSystem(Command):
    trader_id: TraderId
    component_id: Identifier
    reason: str | None
    def __init__(
        self,
        trader_id: TraderId,
        component_id: Identifier,
        command_id: UUID4,
        ts_init: int,
        reason: str | None = ...,
        correlation_id: UUID4 | None = ...,
    ) -> None: ...
    @staticmethod
    def from_dict(values: dict[str, Any]) -> ShutdownSystem: ...
    @staticmethod
    def to_dict(obj: ShutdownSystem) -> dict[str, Any]: ...


class ComponentStateChanged(Event):
    trader_id: TraderId
    component_id: Identifier
    component_type: str
    state: ComponentState
    config: dict[str, Any]
    def __init__(
        self,
        trader_id: TraderId,
        component_id: Identifier,
        component_type: str,
        state: ComponentState,
        config: dict[str, Any],
        event_id: UUID4,
        ts_event: int,
        ts_init: int,
    ) -> None: ...
    @property
    def id(self) -> UUID4: ...
    @property
    def ts_event(self) -> int: ...
    @property
    def ts_init(self) -> int: ...
    @staticmethod
    def from_dict(values: dict[str, Any]) -> ComponentStateChanged: ...
    @staticmethod
    def to_dict(obj: ComponentStateChanged) -> dict[str, Any]: ...
