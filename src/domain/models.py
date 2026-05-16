from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BBox:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0:
            raise ValueError(f"width must be >= 0, got {self.width}")
        if self.height < 0:
            raise ValueError(f"height must be >= 0, got {self.height}")

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class Keypoint:
    name: str
    x: int
    y: int
    confidence: float = 1.0

    def as_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Pose:
    keypoints: tuple[Keypoint, ...]

    def __init__(self, keypoints: Sequence[Keypoint]) -> None:
        object.__setattr__(self, "keypoints", tuple(keypoints))
        object.__setattr__(self, "_index", {kp.name: kp for kp in keypoints})

    def get(self, name: str) -> Keypoint | None:
        return self._index.get(name)

    def has_all(self, names: Sequence[str]) -> bool:
        return all(name in self._index for name in names)
