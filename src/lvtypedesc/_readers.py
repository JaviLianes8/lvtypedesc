"""Bounded big-endian readers for the fields inside one descriptor."""

from __future__ import annotations

from ._errors import TypeDescError

U32_VARIABLE = 0xFFFFFFFF


class Fields:
    """Reads the fields of the descriptor at ``start`` without passing its ``end``."""

    def __init__(self, data: bytes, start: int, end: int) -> None:
        self.data = data
        self.start = start
        self.end = end
        self.pos = start + 4

    def _take(self, size: int) -> bytes:
        if self.pos + size > self.end:
            raise TypeDescError(f"descriptor at offset {self.start} is too short for its fields")
        chunk = self.data[self.pos : self.pos + size]
        self.pos += size
        return chunk

    def u16(self) -> int:
        return int.from_bytes(self._take(2), "big")

    def i16(self) -> int:
        return int.from_bytes(self._take(2), "big", signed=True)

    def u32(self) -> int:
        return int.from_bytes(self._take(4), "big")

    def pstr(self) -> str:
        size = self._take(1)[0]
        return self._take(size).decode("latin-1")

    def label(self) -> str | None:
        """The appended name, which starts at the next even offset, or None if absent."""
        if (self.pos - self.start) % 2:
            self.pos += 1
        if self.pos >= self.end:
            return None
        if self.pos + 1 + self.data[self.pos] > self.end:
            raise TypeDescError(f"name of the descriptor at offset {self.start} runs past it")
        return self.pstr()


def header(data: bytes, offset: int, limit: int) -> tuple[int, int, int]:
    """Return ``(end, code, flags)`` of the descriptor at ``offset``, checked against
    ``limit`` (the end of the enclosing descriptor or of the input)."""
    if offset + 4 > limit:
        raise TypeDescError(f"truncated: need a 4-byte header at offset {offset}")
    length = int.from_bytes(data[offset : offset + 2], "big")
    if length < 4:
        raise TypeDescError(f"length {length} too small at offset {offset}")
    if offset + length > limit:
        where = "the input" if limit == len(data) else "its parent"
        raise TypeDescError(f"descriptor at offset {offset} runs past {where}")
    return offset + length, data[offset + 3], data[offset + 2]


def size_word(value: int) -> int:
    """Map a 32-bit size word to ``VARIABLE`` (-1) or the fixed size."""
    return -1 if value == U32_VARIABLE else value
