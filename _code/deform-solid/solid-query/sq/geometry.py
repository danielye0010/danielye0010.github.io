"""Closed box minus OPEN z-through cylinders; decisions require strict margins."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Box:
    lo: np.ndarray
    hi: np.ndarray

    def __post_init__(self):
        lo, hi = np.asarray(self.lo, float), np.asarray(self.hi, float)
        if lo.shape != (3,) or hi.shape != (3,) or not np.all(np.isfinite([lo, hi])) or np.any(lo > hi):
            raise ValueError("finite ordered three-dimensional box required")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    @property
    def center(self):
        return self.lo + (self.hi - self.lo) / 2

    @property
    def width(self):
        return self.hi - self.lo

    def split(self):
        axis = int(np.argmax(self.width))
        mid = self.center[axis]
        if not self.lo[axis] < mid < self.hi[axis]:
            return None
        left, right = self.hi.copy(), self.lo.copy()
        left[axis], right[axis] = mid, mid
        return Box(self.lo, left), Box(right, self.hi)

    def overlaps(self, other, guard=0.):
        return bool(np.all(self.hi >= other.lo - guard) and np.all(other.hi >= self.lo - guard))


class Solid:
    # Dyadic parameters: exact analytic geometry, independent of FE grid.
    lo = np.full(3, 1 / 16)
    hi = np.full(3, 15 / 16)
    holes = np.array([[5/16, 1/2, 7/256], [3/8, 1/2, 7/256],
                      [29/32, 11/16, 3/128], [5/8, 9/32, 1/64]])

    def classify(self, box, guard=0.):
        """EMPTY excludes all solid; FULL includes only strict solid interior."""
        if np.any(box.hi < self.lo - guard) or np.any(box.lo > self.hi + guard):
            return "EMPTY"
        delta_lo = box.lo[:2] - self.holes[:, :2]
        delta_hi = box.hi[:2] - self.holes[:, :2]
        far = np.maximum(np.abs(delta_lo), np.abs(delta_hi))
        far2 = np.sum(far**2, axis=1)
        if np.any(far2 < self.holes[:, 2]**2 - guard):
            return "EMPTY"
        near = np.maximum(np.maximum(delta_lo, -delta_hi), 0.)
        near2 = np.sum(near**2, axis=1)
        if (np.all(box.lo > self.lo + guard) and np.all(box.hi < self.hi - guard)
                and np.all(near2 > self.holes[:, 2]**2 + guard)):
            return "FULL"
        return "MIXED"

    def interior(self, point, guard=0.):
        return self.classify(Box(point, point), guard) == "FULL"

    def as_dict(self):
        return {"body_lo": self.lo.tolist(), "body_hi": self.hi.tolist(),
                "holes_xy_radius": self.holes.tolist(),
                "semantics": "closed body minus open z-through cylinders"}
