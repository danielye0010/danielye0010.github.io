#include "e1.h"
#if defined(_WIN32)
extern "C" __declspec(dllimport) int __stdcall QueryPerformanceCounter(long long*);
extern "C" __declspec(dllimport) int __stdcall QueryPerformanceFrequency(long long*);
E1_API int e1_timed_nodes(const E1Model* m,const E1Options* o,const E1Plane* p,
    const E1Window* w,e1_u32 n,const e1_u64* ids,e1_u64 count,const e1_u8* forced,
    E1Output* out,double* seconds) {
    if(!seconds)return 1;
    long long begin,end,freq;
    if(!QueryPerformanceFrequency(&freq)||!QueryPerformanceCounter(&begin)||freq<=0)return 1;
    int result=e1_evaluate_nodes(m,o,p,w,n,ids,count,forced,out);
    if(!QueryPerformanceCounter(&end))return 1;
    *seconds=double(end-begin)/double(freq);return result;
}
#else
#include <chrono>
E1_API int e1_timed_nodes(const E1Model* m,const E1Options* o,const E1Plane* p,
    const E1Window* w,e1_u32 n,const e1_u64* ids,e1_u64 count,const e1_u8* forced,
    E1Output* out,double* seconds) {
    if(!seconds)return 1;auto a=std::chrono::steady_clock::now();
    int result=e1_evaluate_nodes(m,o,p,w,n,ids,count,forced,out);
    *seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-a).count();return result;
}
#endif
E1_API void e1_noop(){}
