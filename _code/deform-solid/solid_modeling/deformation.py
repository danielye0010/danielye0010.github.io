"""Read-only reuse of Exp07-A's independently validated active-set Newton."""
from pathlib import Path
import importlib.util
import sys
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'experiments/exp07a_residual_chart_eligibility/engine.py'
spec = importlib.util.spec_from_file_location('_section_exp07_engine', SOURCE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class Deformation:
    """The four frozen globally invertible, clamped Q1 controls; no fitted map.

    forward_reference deliberately calls the original Q1 interpolation rather
    than the fast evaluator used by inverse(), for independent geometry checks.
    """
    def __init__(self, name='nonlinear_high'):
        if name not in ('identity', 'affine', 'nonlinear_mild', 'nonlinear_high'):
            raise ValueError('Use one of the four validated Exp06/07-A fields')
        self.name = name
        self.model = engine.Model(name)
        self.field = self.model.field
        self.q_inf = self.model.q

    def inverse(self, y, field_tolerance=1e-10):
        y = np.asarray(y, float).reshape(-1, 3)
        if not np.isfinite(y).all():
            raise ValueError('Finite spatial coordinates required')
        x, residual, detail = engine.solve(self.model, y)
        _, inverse_bound, field_bound = self.model.bound(residual)
        if len(y) and field_bound.max() > field_tolerance:
            raise ValueError('Inverse field tolerance below attained guarded residual bound')
        return x, inverse_bound, detail

    def forward(self, x):
        shape = np.asarray(x).shape
        return self.model.forward(np.asarray(x, float).reshape(-1, 3)).reshape(shape)

    def forward_reference(self, x):
        return self.field.evaluate(np.asarray(x, float))

    def jacobian(self, x):
        return self.model.jacobian(np.asarray(x, float).reshape(-1, 3))

    def as_dict(self):
        return dict(name=self.name, source=str(SOURCE), q_inf=self.q_inf,
                    inverse='unchanged Exp07-A damped active-set Newton',
                    floating_status='guarded binary64; no directed rounding')
