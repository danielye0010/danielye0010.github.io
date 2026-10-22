#include "e1.h"
static_assert(sizeof(e1_u32)==4 && sizeof(e1_u64)==8 && sizeof(double)==8, "ABI sizes");
#if defined(E1_FREESTANDING)
// COFF floating-point marker; no CRT startup, heap, TLS or global constructors.
extern "C" { int _fltused=0; }
#endif
#if !defined(__clang__) && !defined(__GNUC__)
#include <math.h>
#endif
namespace {
double absd(double x) { return x<0 ? -x : x; }
double maxd(double a,double b) { return a>b ? a : b; }
double mind(double a,double b) { return a<b ? a : b; }
double clamp(double x) { return mind(1.,maxd(0.,x)); }
double sqrtd(double x) {
#if defined(__clang__) || defined(__GNUC__)
    return __builtin_sqrt(x);
#else
    return sqrt(x);
#endif
}
double inf() { union {e1_u64 bits; double value;} a; a.bits=0x7ff0000000000000ULL; return a.value; }
double nan() { union {e1_u64 bits; double value;} a; a.bits=0x7ff8000000000000ULL; return a.value; }
bool finite(double x) { return x==x && absd(x)<=1.7976931348623157e308; }
struct V { double a[3]; double& operator[](int i){return a[i];} double operator[](int i)const{return a[i];} };
double norm(V a) { return maxd(absd(a[0]),maxd(absd(a[1]),absd(a[2]))); }
bool finite3(V a) { return finite(a[0])&&finite(a[1])&&finite(a[2]); }
V sub(V a,V b) { V c; for(int j=0;j<3;++j)c[j]=a[j]-b[j]; return c; }
const double A[9]={1.+1./16,1./8,1./32,1./32,1.-1./32,1./16,-1./64,1./32,1.+1./32};
const double B[3]={1./32,-1./64,1./64};
double q(e1_u32 id) { return id==0?0.:(id==1?7./32:(id==2?15./32:15./16)); }
void tent(double x,double& f,double& d) {
    const double slopes[4]={3.,1.,-3.,-1.}, values[4]={0.,.75,1.,.25};
    double z=clamp(x); int k=int(z*4); if(k>3)k=3;
    f=values[k]+(z-k/4.)*slopes[k];
    d=(x>=0&&x<=1)?slopes[k]:0.; // right cell at internal knots, inclusive at 0/1
}
V forward(e1_u32 id,V x) {
    if(id==0)return x;
    V out;
    if(id==1) {
        for(int j=0;j<3;++j) {
            double s=0.; for(int k=0;k<3;++k)s+=clamp(x[k])*(A[j*3+k]-(j==k?1.:0.));
            out[j]=(x[j]+s)+B[j];
        }
        return out;
    }
    double a,b,c,dummy; tent(x[0],a,dummy);tent(x[1],b,dummy);tent(x[2],c,dummy);
    double amp=id==2?1.:2.;
    out[0]=x[0]+amp*(b*c/16+a*b/64);
    out[1]=x[1]+amp*(3*a*c/64-b*c/64);
    out[2]=x[2]+amp*(a*b/32+a*b*c/64);
    return out;
}
void jacobian(e1_u32 id,V x,double* J) {
    for(int r=0;r<3;++r)for(int c=0;c<3;++c)J[r*3+c]=(r==c?1.:0.);
    if(id==0)return;
    if(id==1) {
        for(int r=0;r<3;++r)for(int c=0;c<3;++c)
            J[r*3+c]+=(A[r*3+c]-(r==c?1.:0.))*((x[c]>=0&&x[c]<=1)?1.:0.);
        return;
    }
    double a,b,c,p,s,r;tent(x[0],a,p);tent(x[1],b,s);tent(x[2],c,r);
    double amp=id==2?1.:2.;
    J[0]+=amp*p*b/64;J[1]+=amp*s*(c/16+a/64);J[2]+=amp*r*b/16;
    J[3]+=amp*3*p*c/64;J[4]-=amp*s*c/64;J[5]+=amp*r*(3*a-b)/64;
    J[6]+=amp*p*b*(1./32+c/64);J[7]+=amp*s*a*(1./32+c/64);J[8]+=amp*r*a*b/64;
}
bool solve3(const double* matrix,V rhs,V& out) {
    double a[3][4];
    for(int j=0;j<3;++j){for(int k=0;k<3;++k)a[j][k]=matrix[j*3+k];a[j][3]=rhs[j];}
    for(int k=0;k<3;++k) {
        int pivot=k;for(int j=k+1;j<3;++j)if(absd(a[j][k])>absd(a[pivot][k]))pivot=j;
        if(!finite(a[pivot][k])||a[pivot][k]==0)return false;
        if(pivot!=k)for(int c=k;c<4;++c){double t=a[k][c];a[k][c]=a[pivot][c];a[pivot][c]=t;}
        for(int j=k+1;j<3;++j){double m=a[j][k]/a[k][k];for(int c=k+1;c<4;++c)a[j][c]-=m*a[k][c];}
    }
    for(int k=2;k>=0;--k){double s=a[k][3];for(int j=k+1;j<3;++j)s-=a[k][j]*out[j];out[k]=s/a[k][k];}
    return finite3(out);
}
V initial(e1_u32 id,V y) {
    if(id==0)return y;
    if(id==1){V rhs,out;for(int j=0;j<3;++j)rhs[j]=y[j]-B[j];solve3(A,rhs,out);return out;}
    V fy=forward(id,y),x;for(int j=0;j<3;++j)x[j]=y[j]-(fy[j]-y[j]);return x;
}
double field(const E1Model& m,V x) {
    double value=m.lo[0]-x[0];
    for(int j=0;j<3;++j)value=maxd(value,maxd(m.lo[j]-x[j],x[j]-m.hi[j]));
    for(e1_u32 j=0;j<m.hole_count;++j){double dx=x[0]-m.holes[j*3],dy=x[1]-m.holes[j*3+1];
        value=maxd(value,m.holes[j*3+2]-sqrtd(dx*dx+dy*dy));}
    return value;
}
bool valid_model(const E1Model& m) {
    if(m.abi_version!=1||m.reserved||m.hole_count>1024||(m.hole_count&&!m.holes))return false;
    for(int j=0;j<3;++j)if(!finite(m.lo[j])||!finite(m.hi[j])||m.lo[j]>=m.hi[j]||m.lo[j]<0||m.hi[j]>1)return false;
    for(e1_u32 j=0;j<m.hole_count;++j){double x=m.holes[j*3],y=m.holes[j*3+1],r=m.holes[j*3+2];
        if(!finite(x)||!finite(y)||!finite(r)||r<=0||x-r<=m.lo[0]||x+r>=m.hi[0]||y-r<=m.lo[1]||y+r>=m.hi[1])return false;
        for(e1_u32 k=0;k<j;++k){double dx=x-m.holes[k*3],dy=y-m.holes[k*3+1],rr=r+m.holes[k*3+2];if(dx*dx+dy*dy<=rr*rr)return false;}}
    return true;
}
bool valid_output(const E1Output& o) {
    return o.value&&o.field_lower&&o.field_upper&&o.source_x&&o.source_y&&o.source_z&&o.inverse_error_inf&&
        o.residual_x&&o.residual_y&&o.residual_z&&o.residual_inf&&o.guarded_inverse_error&&o.guarded_field_error&&
        o.qualification&&o.numeric_status&&o.failure_reason&&o.guarded_sign&&o.iterations&&o.fixedpoint_fallbacks;
}
void reset(E1Output& o,e1_u64 i) {
    o.value[i]=nan();o.field_lower[i]=-inf();o.field_upper[i]=inf();o.inverse_error_inf[i]=inf();
    o.source_x[i]=nan();o.source_y[i]=nan();o.source_z[i]=nan();
    o.residual_x[i]=nan();o.residual_y[i]=nan();o.residual_z[i]=nan();o.residual_inf[i]=inf();
    o.guarded_inverse_error[i]=inf();o.guarded_field_error[i]=inf();
    o.qualification[i]=0;o.numeric_status[i]=E1_INVALID;o.failure_reason[i]=E1_INVALID_REQUEST;
    o.guarded_sign[i]=0;o.iterations[i]=0;o.fixedpoint_fallbacks[i]=0;
}
void evaluate(const E1Model& m,const E1Options& opt,V y,e1_u64 i,bool forced,E1Output& o) {
    reset(o,i);
    if(m.model_id>3){o.numeric_status[i]=E1_UNSUPPORTED;o.failure_reason[i]=E1_UNSUPPORTED_MAP;return;}
    if(!finite3(y)){o.numeric_status[i]=E1_NONFINITE;o.failure_reason[i]=E1_NONFINITE_INPUT;return;}
    if(forced){o.numeric_status[i]=E1_INJECTED;o.failure_reason[i]=E1_FAILURE_CONTROL;return;}
    V x=initial(m.model_id,y),r=sub(forward(m.model_id,x),y);
    bool singular=false;
    for(e1_u32 it=0;it<opt.max_iterations && norm(r)>1e-14;++it) {
        ++o.iterations[i];double J[9];jacobian(m.model_id,x,J);V step;
        if(!solve3(J,r,step)){singular=true;break;}
        double old=norm(r),scale=1.;bool accepted=false;
        for(e1_u32 ls=0;ls<opt.line_search_steps;++ls){V trial;for(int j=0;j<3;++j)trial[j]=x[j]-scale*step[j];
            V rr=sub(forward(m.model_id,trial),y);double rn=norm(rr);
            if(finite3(trial)&&finite3(rr)&&(rn<old||rn<=1e-14)){x=trial;r=rr;accepted=true;break;}scale/=2.;}
        if(!accepted){x=sub(x,r);r=sub(forward(m.model_id,x),y);++o.fixedpoint_fallbacks[i];}
        if(!finite3(x)||!finite3(r))break;
    }
    o.source_x[i]=x[0];o.source_y[i]=x[1];o.source_z[i]=x[2];
    o.residual_x[i]=r[0];o.residual_y[i]=r[1];o.residual_z[i]=r[2];o.residual_inf[i]=norm(r);
    if(singular){o.numeric_status[i]=E1_SINGULAR;o.failure_reason[i]=E1_LINEAR_FAILURE;return;}
    if(!finite3(x)||!finite3(r)){o.numeric_status[i]=E1_NONFINITE;o.failure_reason[i]=E1_NONFINITE_INPUT;return;}
    if(norm(r)>3e-13){o.numeric_status[i]=E1_NONCONVERGED;o.failure_reason[i]=E1_SOLVER_FAILURE;return;}
    double inv=(norm(r)+2e-13)/(1-q(m.model_id));
    // Match original Model.bound: sqrt(2) also when there are no holes.
    double fb=sqrtd(2.)*inv+2e-13;
    o.guarded_inverse_error[i]=inv;o.guarded_field_error[i]=fb;
    if(fb>opt.field_tolerance){o.numeric_status[i]=E1_FIELD_TOLERANCE;o.failure_reason[i]=E1_SOLVER_FAILURE;return;}
    double value=field(m,x);
    if(!finite(value)){o.numeric_status[i]=E1_NONFINITE;o.failure_reason[i]=E1_NONFINITE_INPUT;return;}
    o.value[i]=value;o.numeric_status[i]=E1_OK;o.failure_reason[i]=E1_UNSUPPORTED_ARITHMETIC;
    o.guarded_sign[i]=(value+fb<0)?-1:((value-fb>0)?1:0);
}
bool options_ok(const E1Options& o){return o.abi_version==1&&!o.reserved&&o.max_iterations<=30&&o.line_search_steps<=8&&finite(o.field_tolerance)&&o.field_tolerance>0&&o.field_tolerance<=1e-10;}
}
E1_API e1_u32 e1_abi_version(){return 1;}
E1_API void e1_default_options(E1Options* o){if(!o)return;o->abi_version=1;o->max_iterations=30;o->line_search_steps=8;o->reserved=0;o->field_tolerance=1e-10;}
E1_API void e1_default_model(e1_u32 id,double radius,E1Model* m,double* h){
    if(!m||!h)return;m->abi_version=1;m->model_id=id;m->hole_count=4;m->reserved=0;
    for(int j=0;j<3;++j){m->lo[j]=1./16;m->hi[j]=15./16;}
    const double data[12]={5./16,1./2,7./256,3./8,1./2,7./256,29./32,11./16,3./128,5./8,9./32,0.};
    for(int j=0;j<12;++j)h[j]=data[j];h[11]=radius;m->holes=h;
}
E1_API int e1_evaluate_xyz(const E1Model* m,const E1Options* opt,e1_u64 count,const double* x,const double* y,const double* z,const e1_u8* forced,E1Output* o){
    if(count==0)return 0;
    if(!m||!opt||!o||!valid_output(*o)||!x||!y||!z)return 1;
    if(!valid_model(*m)||!options_ok(*opt)){for(e1_u64 i=0;i<count;++i)reset(*o,i);return 1;}
    for(e1_u64 i=0;i<count;++i){V p={{x[i],y[i],z[i]}};evaluate(*m,*opt,p,i,forced&&forced[i],*o);}return 0;
}
E1_API int e1_evaluate_nodes(const E1Model* m,const E1Options* opt,const E1Plane* p,const E1Window* w,e1_u32 n,const e1_u64* ids,e1_u64 count,const e1_u8* forced,E1Output* o){
    if(count==0)return 0;
    if(!m||!opt||!p||!w||!o||!valid_output(*o))return 1;
    bool valid=n&&!(n&(n-1))&&n<=1048576&&valid_model(*m)&&options_ok(*opt);
    for(int j=0;j<3;++j)valid=valid&&finite(p->origin[j])&&finite(p->u[j])&&finite(p->v[j]);
    double uu=0,vv=0,uv=0;for(int j=0;j<3;++j){uu+=p->u[j]*p->u[j];vv+=p->v[j]*p->v[j];uv+=p->u[j]*p->v[j];}
    valid=valid&&absd(uu-1)<=1e-10&&absd(vv-1)<=1e-10&&absd(uv)<=1e-10;
    for(int k=0;k<2;++k)valid=valid&&finite(w->lo[k])&&finite(w->hi[k])&&w->lo[k]<w->hi[k];
    if(!valid){for(e1_u64 i=0;i<count;++i)reset(*o,i);return 1;}
    e1_u64 total=(e1_u64(n)+1)*(e1_u64(n)+1);
    for(e1_u64 i=0;i<count;++i){e1_u64 id=ids?ids[i]:i;if(id>=total){reset(*o,i);continue;}
        double u=w->lo[0]+(w->hi[0]-w->lo[0])*(double(id%(n+1))/n);
        double v=w->lo[1]+(w->hi[1]-w->lo[1])*(double(id/(n+1))/n);
        V y;for(int k=0;k<3;++k)y[k]=(p->origin[k]+u*p->u[k])+v*p->v[k];
        evaluate(*m,*opt,y,i,forced&&forced[i],*o);
    }return 0;
}
E1_API int e1_forward_batch(e1_u32 id,e1_u64 count,const double* x,const double* y,const double* z,double* fx,double* fy,double* fz,double* J){
    if(!count)return 0;if(id>3||!x||!y||!z||!fx||!fy||!fz||!J)return 1;
    for(e1_u64 i=0;i<count;++i){V p={{x[i],y[i],z[i]}};if(!finite3(p))return 1;V f=forward(id,p);fx[i]=f[0];fy[i]=f[1];fz[i]=f[2];jacobian(id,p,J+9*i);}return 0;
}
