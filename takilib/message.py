from __future__ import annotations

from typing import Sequence

from enum import Enum, auto


class Message:
    class Kind(Enum):
        choice = auto()
        info = auto()
        bad_input=auto()

    def __init__(self, msg: str, src, dst: Sequence, kind: Message.Kind):
        self.msg = msg
        self.src = src
        self.dst = dst
        self.kind = kind
