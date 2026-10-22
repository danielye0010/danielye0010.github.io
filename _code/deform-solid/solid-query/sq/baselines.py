"""Two conservative-in-exact-arithmetic baselines, equal explicit work limits."""
from dataclasses import dataclass, asdict
from collections import deque
import numpy as np
from .geometry import Box


@dataclass
class Stats:
    nodes: int = 0
    splits: int = 0
    map_evals: int = 0
    jac_evals: int = 0
    newton_iterations: int = 0
    fallback_steps: int = 0
    candidates: int = 0
    peak_pending: int = 0
    empty_geometry: int = 0
    empty_spatial: int = 0
    terminal_mixed: int = 0
    max_residual: float = 0.


@dataclass
class Result:
    status: str
    stats: Stats
    witness: list | None = None
    reason: str = ""

    def as_dict(self):
        return {"status": self.status, "stats": asdict(self.stats), "witness": self.witness, "reason": self.reason}


class Baseline:
    def __init__(self, field, solid, config):
        self.field, self.solid, self.cfg = field, solid, config

    def witness(self, x, query, stats):
        if not self.solid.interior(x, self.field.guard):
            return False
        y = self.field.evaluate(x, stats)
        return bool(np.all(y > query.lo+self.field.guard) and np.all(y < query.hi-self.field.guard))

    def terminal(self, box, depth):
        return depth >= self.cfg["max_depth"] or box.width.max() <= self.cfg["min_width"]

    def pop(self, pending):
        return pending.popleft() if self.cfg.get("traversal", "depth") == "breadth" else pending.pop()

    def push(self, pending, items):
        pending.extend(items if self.cfg.get("traversal", "depth") == "breadth" else items[::-1])


class Forward(Baseline):
    name = "A_forward"

    def query(self, query):
        f, stats = self.field, Stats()
        ids = f.candidates(query)
        stats.candidates = len(ids)
        # Center-first order is fixed and shared through candidate ordering.
        if not len(ids):
            return Result("DISJOINT", stats, reason="no FE-cell image AABB overlaps query")
        distance = np.sum(((f.image_lo[ids]+f.image_hi[ids])/2-query.center)**2, axis=1)
        ids = ids[np.argsort(distance, kind="stable")]
        stack = deque((int(e), Box(f.ref_lo[e], f.ref_hi[e]), 0) for e in
                      (ids if self.cfg.get("traversal", "depth") == "breadth" else ids[::-1]))
        unresolved = False
        while stack and stats.nodes < self.cfg["max_nodes"]:
            stats.peak_pending = max(stats.peak_pending, len(stack))
            eid, box, depth = self.pop(stack)
            stats.nodes += 1
            if self.solid.classify(box, f.guard) == "EMPTY":
                stats.empty_geometry += 1
                continue
            if not f.cell_bounds(eid, box, stats).overlaps(query):
                stats.empty_spatial += 1
                continue
            if self.witness(box.center, query, stats):
                return Result("INTERSECTS", stats, box.center.tolist(), "strict interior forward witness")
            children = box.split()
            if self.terminal(box, depth) or children is None:
                unresolved = True
                stats.terminal_mixed += 1
            else:
                self.push(stack, [(eid, b, depth+1) for b in children])
                stats.splits += 1
        if stack or unresolved:
            return Result("UNRESOLVED", stats, reason="work/width/depth limit with possible overlap")
        return Result("DISJOINT", stats, reason="all reference-cell subboxes excluded")


def newton(field, target, stats, initial=None):
    """Unconstrained global-extension solve; posterior validity does not require convergence."""
    x = target.copy() if initial is None else initial.copy()
    for _ in range(16):
        fx = field.evaluate(x, stats)
        residual = fx-target
        norm = float(np.max(np.abs(residual)))
        stats.newton_iterations += 1
        if norm <= 2e-14:
            break
        J = field.jacobian(x, stats)
        try:
            step = np.linalg.solve(J, residual)
        except np.linalg.LinAlgError:
            step = residual
        accepted = False
        scale = 1.
        for _ in range(8):
            trial = x-scale*step
            if np.max(np.abs(field.evaluate(trial, stats)-target)) < norm:
                x, accepted = trial, True
                break
            scale /= 2
        if not accepted:
            x -= residual  # fixed point x <- target-u(clamp(x))
            stats.fallback_steps += 1
    res = float(np.max(np.abs(field.evaluate(x, stats)-target)))
    stats.max_residual = max(stats.max_residual, res)
    return x, res


class Inverse(Baseline):
    name = "B_inverse"

    def query(self, query):
        f, stats = self.field, Stats()
        ids = f.candidates(query)
        stats.candidates = len(ids)
        if not len(ids):
            return Result("DISJOINT", stats, reason="no FE-cell image AABB overlaps query")
        stack = deque([(query, 0, None)])
        unresolved = False
        while stack and stats.nodes < self.cfg["max_nodes"]:
            stats.peak_pending = max(stats.peak_pending, len(stack))
            box, depth, initial = self.pop(stack)
            stats.nodes += 1
            if not len(f.candidates(box)):
                stats.empty_spatial += 1
                continue
            x, residual = newton(f, box.center, stats, initial)
            # All y in box have a unique GLOBAL extension inverse. Segment
            # argument across cell faces gives ||X(y)-x||inf <= alpha*(r+res).
            # No assumption that a root lies in the physical grid is needed.
            radius = f.alpha * (box.width.max()/2 + residual + f.guard) + f.guard
            inverse_box = Box(x-radius, x+radius)
            if self.solid.classify(inverse_box, f.guard) == "EMPTY":
                stats.empty_geometry += 1
                continue
            if self.witness(x, query, stats):
                return Result("INTERSECTS", stats, x.tolist(), "strict interior forward witness from Newton iterate")
            children = box.split()
            if self.terminal(box, depth) or children is None:
                unresolved = True
                stats.terminal_mixed += 1
            else:
                self.push(stack, [(b, depth+1, x) for b in children])
                stats.splits += 1
        if stack or unresolved:
            return Result("UNRESOLVED", stats, reason="work/width/depth limit with possible overlap")
        return Result("DISJOINT", stats, reason="all deformed-query subboxes excluded")
