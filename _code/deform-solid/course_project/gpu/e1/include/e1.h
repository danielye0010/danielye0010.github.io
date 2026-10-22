#pragma once
// Fixed-width C ABI, caller-owned buffers, no allocations or Python dependency.
typedef unsigned int e1_u32;
typedef unsigned long long e1_u64;
typedef unsigned char e1_u8;
typedef signed char e1_i8;
#if defined(_WIN32)
#define E1_API extern "C" __declspec(dllexport)
#else
#define E1_API extern "C" __attribute__((visibility("default")))
#endif
enum E1ModelId { E1_IDENTITY=0, E1_AFFINE=1, E1_MILD=2, E1_STRONG=3 };
enum E1NumericStatus { E1_OK=1, E1_NONCONVERGED=2, E1_NONFINITE=3,
    E1_UNSUPPORTED=4, E1_INVALID=5, E1_FIELD_TOLERANCE=6, E1_SINGULAR=7, E1_INJECTED=8 };
enum E1Reason { E1_NO_REASON=0, E1_SOLVER_FAILURE=1, E1_NONFINITE_INPUT=2,
    E1_UNSUPPORTED_MAP=3, E1_UNSUPPORTED_BOUND=4, E1_UNSUPPORTED_ARITHMETIC=5,
    E1_INVALID_REQUEST=6, E1_LINEAR_FAILURE=7, E1_FAILURE_CONTROL=8 };
struct E1Model {
    e1_u32 abi_version, model_id, hole_count, reserved;
    double lo[3], hi[3];
    const double* holes; // consecutive (cx,cy,r), lifetime covers the call
};
struct E1Options {
    e1_u32 abi_version, max_iterations, line_search_steps, reserved;
    double field_tolerance; // default 1e-10; stop=1e-14 and acceptance=3e-13 fixed
};
struct E1Plane { double origin[3], u[3], v[3]; };
struct E1Window { double lo[2], hi[2]; };
struct E1Output {
    double *value, *field_lower, *field_upper, *source_x, *source_y, *source_z;
    double *inverse_error_inf; // +inf: no interval certificate implemented
    double *residual_x, *residual_y, *residual_z, *residual_inf;
    double *guarded_inverse_error, *guarded_field_error; // inherited diagnostics ONLY
    e1_u8 *qualification, *numeric_status, *failure_reason;
    e1_i8 *guarded_sign; // original Python guarded sign, NOT certified pruning
    e1_u32 *iterations, *fixedpoint_fallbacks;
};
E1_API e1_u32 e1_abi_version();
E1_API void e1_default_model(e1_u32 id, double last_radius, E1Model*, double* holes12);
E1_API void e1_default_options(E1Options*);
// Return 0 for structurally valid call (individual failures remain in row masks).
// Empty batches return 0 without dereferencing buffers. Errors return 1.
E1_API int e1_evaluate_xyz(const E1Model*, const E1Options*, e1_u64 count,
    const double* x, const double* y, const double* z, const e1_u8* force_failure, E1Output*);
E1_API int e1_evaluate_nodes(const E1Model*, const E1Options*, const E1Plane*,
    const E1Window*, e1_u32 n, const e1_u64* node_ids, e1_u64 count,
    const e1_u8* force_failure, E1Output*); // nullptr IDs = dense IDs 0..count-1
// Audit forward map/Jacobian without an inverse. jacobian is count*9 row-major.
E1_API int e1_forward_batch(e1_u32 model_id, e1_u64 count, const double* x,
    const double* y, const double* z, double* fx, double* fy, double* fz, double* jacobian);
E1_API int e1_timed_nodes(const E1Model*, const E1Options*, const E1Plane*,
    const E1Window*, e1_u32 n, const e1_u64* node_ids, e1_u64 count,
    const e1_u8* force_failure, E1Output*, double* native_seconds);
E1_API void e1_noop();
