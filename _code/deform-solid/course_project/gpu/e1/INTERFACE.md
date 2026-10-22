# E1 C ABI v1 and arithmetic scope

`include/e1.h` is the authoritative C-compatible layout and enum definition.
Use its `E1Model`, `E1Options`, `E1Plane`, `E1Window`, and `E1Output` with ordinary
8-byte double/64-bit pointer alignment on the tested Windows x64 platform.
The header is C++17 with exported C linkage. The runtime reports ABI version 1.
All input/output buffers are caller-owned, contiguous, nonaliasing, and live
through the call. Nothing is allocated or retained by the DLL. No global state
is mutated. Batch rows preserve order, including duplicates and failures.

`e1_evaluate_xyz` takes three coordinate arrays. `e1_evaluate_nodes` takes an
orthonormal plane, finite ordered window, power-of-two N<=2^20, and optional
uint64 node IDs. With IDs=nullptr it evaluates dense IDs 0..count-1. The row ID
is `j*(N+1)+i`; coordinate is `lo+(hi-lo)*(i,j)/N`. Node coordinates are ordinary
floating arithmetic; small differences from E0's interval-midpoint construction
are checked against saved data. Plane/world and reference/spatial coordinates,
dimensionless units, and the exterior extension retain the Python conventions.
The supported model IDs are identity=0, affine=1, mild=2, strong=3. Their
separable tent formulas exactly represent the original 4x4x4 piecewise-Q1 family;
no arbitrary FE mesh, affine composition, or replacement smooth warp is accepted.
The caller can supply the original valid analytic box/through-hole arrays.

Defaults: 30 Newton iterations, eight halved line-search attempts, infinity-norm
stop 1e-14, final residual acceptance 3e-13, field guard tolerance 1e-10. A
partial-pivot 3x3 elimination replaces NumPy's LAPACK call, preserving the Newton
and damping/fallback algorithm. FE knots select the right cell, 1 selects the
last cell, boundary derivative activity includes 0/1, and exterior displacement
columns are clamped. Zero iterations and zero line-search steps are explicit
stricter failure controls; defaults are unchanged. Tolerances cannot be relaxed
through this ABI. The maximum field tolerance is 1e-10.

Return code 0 means a structurally usable call, including row failures; 1 means
an invalid batch configuration. For invalid configuration with usable output
buffers, rows are initialized as invalid. Missing mandatory pointers cannot be
written. Empty batches return 0 without dereferencing buffers. Invalid IDs
produce invalid rows rather than dropping them. Nonfinite XYZ inputs produce
explicit failed rows; Python's wrapper rejects its entire batch, so this is a
documented row-local error adaptation. E0's injected failed-node control is
represented by optional per-row force flags, distinct from actual solver failure.

Numeric statuses: 1 success, 2 nonconverged, 3 nonfinite, 4 unsupported map,
5 invalid request, 6 field tolerance unattained, 7 singular solve, 8 injected
failure. Failed values are NaN and guarded signs are zero. Available failed
iterate/residual data are diagnostic only. Iterations and fixed-point fallbacks
are stored per row. A maximum-iteration failure is tested against the original
Python engine's unchanged final acceptance check.

## Concrete E0 interface issue and resolution

E0's proposed interface uses `qualification` for an actual enclosing interval.
Ordinary native arithmetic has no validated interval kernel, so using a generic
success flag there would silently transfer a certificate. E1 therefore adds
`numeric_status` and retains `qualification=0` for every row. On dense success,
failure_reason=5 means **unsupported enclosure arithmetic**, not a failed
Newton solve. Numerical failures have their own reasons. Field intervals remain
[-inf,+inf] and certified inverse error remains +inf. Do not feed these outputs
to conservative tile exclusion. No E0 file was changed to introduce this split.

`guarded_inverse_error=(reported_residual_inf+2e-13)/(1-q)` and
`guarded_field_error=sqrt(2)*guarded_inverse_error+2e-13` copy the original Python
diagnostics. `guarded_sign` copies its strict interval-like sign test. These
fixed guards are ordinary binary64 diagnostics, not outward-rounded guarantees.
Residual components/norm, nominal field, and inverse coordinates are independent
comparison outputs. `field_lower/upper` are never populated with those guards.

`e1_timed_nodes` brackets the same evaluator with native QueryPerformanceCounter,
excluding ctypes marshalling and output allocation. `e1_noop` measures call
overhead separately. Output data are zero-copy Python buffers on the tested
adapter; any future host/device transfer must be measured separately.

CUDA must first implement this dense numerical interface with the same failure
semantics and matched tests. Qualification must remain unavailable until the
actual device arithmetic has a separately validated enclosure implementation.
