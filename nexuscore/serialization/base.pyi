from __future__ import annotations

from typing import Any


_EXTERNAL_PUBLISHABLE_TYPES: set[type]


class Serializer:
    def __init__(self) -> None: ...
    def serialize(self, obj: object) -> bytes: ...
    def deserialize(self, obj_bytes: bytes) -> object: ...
