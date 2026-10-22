"""Continuous structured Q1 map. All-cell derivative ranges, not nodal det tests."""
from itertools import product
import numpy as np
from .geometry import Box

BITS = np.array(list(product((0, 1), repeat=3)), dtype=int)
AFFINE_A = np.array([[1+1/16, 1/8, 1/32], [1/32, 1-1/32, 1/16],
                     [-1/64, 1/32, 1+1/32]])
AFFINE_B = np.array([1/32, -1/64, 1/64])


def prescribed_u(kind, x):
    x = np.asarray(x)
    if kind == "identity":
        return np.zeros_like(x)
    if kind == "affine":
        return x @ (AFFINE_A - np.eye(3)).T + AFFINE_B
    if kind != "nonlinear":
        raise ValueError(kind)
    # Piecewise linear tent has derivative jumps at 1/4, 1/2, 3/4.
    f = np.interp(x, [0, .25, .5, .75, 1], [0, .75, 1, .25, 0])
    a, b, c = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([b*c/16+a*b/64, 3*a*c/64-b*c/64,
                     a*b/32+a*b*c/64], axis=-1)


def basis(t):
    return np.prod(np.where(BITS[None, :, :] == 1, t[:, None, :], 1-t[:, None, :]), axis=2)


class Field:
    def __init__(self, kind="nonlinear", n=4, guard=2e-12, inverse_bounds=True):
        if n not in (4, 8):
            raise ValueError("frozen grids are 4 and 8 (same prescribed field)")
        self.kind, self.n, self.h, self.guard = kind, n, 1/n, guard
        self.indices = np.array(list(product(range(n), repeat=3)))
        self.ref_lo = self.indices / n
        self.ref_hi = (self.indices + 1) / n
        points = (self.indices[:, None, :] + BITS[None, :, :]) / n
        self.u_nodes = prescribed_u(kind, points)
        self.nodes = points + self.u_nodes
        self.image_lo = self.nodes.min(axis=1) - guard
        self.image_hi = self.nodes.max(axis=1) + guard
        common = (self.indices, self.ref_lo, self.ref_hi, self.u_nodes,
                  self.nodes, self.image_lo, self.image_hi)
        self.storage_bytes = sum(a.nbytes for a in common)
        if not inverse_bounds:
            return
        # Each derivative column is bilinear; its extrema are at the 4
        # corners in the OTHER coordinates. Their convex hull bounds the
        # whole cell, including one-sided face limits.
        ranges = []
        for axis in range(3):
            low = np.flatnonzero(BITS[:, axis] == 0)
            high = [np.flatnonzero(np.all(BITS == (BITS[j]+np.eye(3, dtype=int)[axis]), axis=1))[0] for j in low]
            deriv = (self.u_nodes[:, high] - self.u_nodes[:, low]) * n
            ranges.append(np.max(np.abs(deriv), axis=1))
        self.G_cells = np.stack(ranges, axis=2)
        self.G = self.G_cells.max(axis=0) + guard
        self.q = float(np.max(np.sum(self.G, axis=1)))
        if self.q >= 1:
            raise ValueError("contraction/injectivity gate failed")
        self.alpha = 1/(1-self.q)
        self.storage_bytes += self.G_cells.nbytes + self.G.nbytes

    def candidates(self, box):
        # Closed overlap: cell interfaces cannot fall through a strict gap.
        hit = np.all(self.image_hi >= box.lo, axis=1) & np.all(self.image_lo <= box.hi, axis=1)
        return np.flatnonzero(hit)

    def _coordinates(self, x):
        z = np.clip(x, 0, 1)
        ijk = np.minimum(np.floor(z*self.n).astype(int), self.n-1)
        eid = (ijk[..., 0]*self.n + ijk[..., 1])*self.n + ijk[..., 2]
        return eid, z*self.n-ijk

    def evaluate(self, x, stats=None):
        x = np.asarray(x, float)
        flat = x.reshape(-1, 3)
        if stats is not None:
            stats.map_evals += len(flat)
        eid, t = self._coordinates(flat)
        u = np.einsum("pv,pvj->pj", basis(t), self.u_nodes[eid])
        # Global extension x+u(clamp(x)): identical on physical domain.
        return (flat+u).reshape(x.shape)

    def jacobian(self, x, stats=None):
        if stats is not None:
            stats.jac_evals += 1
        eid, t = self._coordinates(np.asarray(x)[None, :])
        t, nodes = t[0], self.u_nodes[eid[0]]
        J = np.eye(3)
        for axis in range(3):
            if x[axis] < 0 or x[axis] > 1:
                continue  # derivative of clamped displacement is zero
            weights = np.where(BITS[:, axis] == 1, 1., -1.) * self.n
            for k in range(3):
                if k != axis:
                    weights *= np.where(BITS[:, k] == 1, t[k], 1-t[k])
            J[:, axis] += weights @ nodes
        return J

    def cell_bounds(self, eid, box, stats=None):
        corners = np.where(BITS, box.hi, box.lo)
        t = (corners-self.ref_lo[eid])*self.n
        if stats is not None:
            stats.map_evals += 8
        mapped = corners + basis(t) @ self.u_nodes[eid]
        return Box(mapped.min(axis=0)-self.guard, mapped.max(axis=0)+self.guard)

    def assumptions(self):
        return {"kind": self.kind, "grid_n": self.n, "cells": self.n**3,
            "G_abs_Du_global": self.G.tolist(), "q_inf_upper_float": self.q,
            "inverse_lipschitz_inf": self.alpha,
            "sigma_min_lower_2": max(0., 1-float(np.linalg.norm(self.G, 2))),
            "det_positive_argument": "I+t Du never singular for 0<=t<=1; continuous from det(I)=1",
            "coverage": "x+u(clamp(x)) is a global contraction perturbation of identity; physical solid is in [0,1]^3",
            "floating_point_status": "binary64 with absolute guards; NOT formal directed-rounding certification"}
