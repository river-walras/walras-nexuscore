from __future__ import annotations

from typing import Callable


class InvalidStateTrigger(Exception):
    pass


class FiniteStateMachine:
    state: int
    def __init__(
        self,
        state_transition_table: dict[tuple[int, int], int],
        initial_state: int,
        trigger_parser: Callable[[int], str] | None = ...,
        state_parser: Callable[[int], str] | None = ...,
    ) -> None: ...
    @property
    def state_string(self) -> str: ...
    def trigger(self, trigger: int) -> None: ...
