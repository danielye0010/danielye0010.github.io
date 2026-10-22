"""The existing closed analytic box minus open, nonoverlapping z cylinders."""
from dataclasses import dataclass
import numpy as np
from .deformation import engine


@dataclass(frozen=True)
class AnalyticCSG:
    lo: object = None
    hi: object = None
    holes: object = None

    def __post_init__(self):
        original = engine.frozen.Solid
        lo = np.array(original.lo if self.lo is None else self.lo, float, copy=True)
        hi = np.array(original.hi if self.hi is None else self.hi, float, copy=True)
        holes = np.array(original.holes if self.holes is None else self.holes, float, copy=True).reshape(-1, 3)
        if lo.shape != (3,) or hi.shape != (3,) or not np.isfinite(np.r_[lo, hi, holes.ravel()]).all():
            raise ValueError('Finite body bounds and xy-radius holes required')
        if np.any(lo >= hi) or np.any(lo < 0) or np.any(hi > 1):
            raise ValueError('Positive body inside the validated reference cube required')
        if len(holes):
            if np.any(holes[:, 2] <= 0) or np.any(holes[:, :2]-holes[:, 2, None] <= lo[:2]) or np.any(holes[:, :2]+holes[:, 2, None] >= hi[:2]):
                raise ValueError('Positive through holes strictly inside the box required')
            for i, h in enumerate(holes):
                if np.any(np.linalg.norm(holes[:i, :2]-h[:2], axis=1) <= holes[:i, 2]+h[2]):
                    raise ValueError('This analytic family requires disjoint holes')
        for value in (lo, hi, holes):
            value.setflags(write=False)
        object.__setattr__(self, 'lo', lo)
        object.__setattr__(self, 'hi', hi)
        object.__setattr__(self, 'holes', holes)

    def value_gradient(self, x):
        x = np.asarray(x, float).reshape(-1, 3)
        box = np.concatenate([self.lo-x, x-self.hi], axis=1)
        radial = x[:, None, :2]-self.holes[None, :, :2]
        norm = np.linalg.norm(radial, axis=2)
        values = np.concatenate([box, self.holes[:, 2]-norm], axis=1)
        active = values.argmax(axis=1)
        value = values[np.arange(len(x)), active]
        gradient = np.zeros_like(x)
        for j in range(6):
            gradient[active == j, j % 3] = -1 if j < 3 else 1
        for j in range(len(self.holes)):
            ids = active == j+6
            gradient[ids, :2] = -radial[ids, j]/np.maximum(norm[ids, j, None], 1e-300)
        return value, gradient, active

    def value(self, x):
        shape = np.asarray(x).shape[:-1]
        return self.value_gradient(x)[0].reshape(shape)

    def with_last_radius(self, radius):
        h = self.holes.copy()
        if not len(h):
            raise ValueError('No last hole to resize')
        h[-1, 2] = radius
        return AnalyticCSG(self.lo, self.hi, h)

    @property
    def lipschitz_inf(self):
        return np.sqrt(2) if len(self.holes) else 1.

    def as_dict(self):
        return dict(body_lo=self.lo.tolist(), body_hi=self.hi.tolist(),
                    holes_xy_radius=self.holes.tolist(),
                    semantics='closed box minus open z-through cylinders')
