"""Independent exact-rational enclosure/witness checker (no NumPy Q1/Newton).

Arithmetic endpoints are Fraction. Iterative enclosures are rounded OUTWARD
to a dyadic lattice by exact integer floor/ceiling to limit denominator growth.
The map is evaluated from its analytic piecewise-polynomial definition, not
from the production cell interpolation. This definition equals both grids.
"""
from fractions import Fraction as F
from itertools import product

SCALE = 2**48
KNOTS = tuple(map(F, (0, .25, .5, .75, 1)))
VALUES = tuple(map(F, (0, .75, 1, .25, 0)))
BODY_LO, BODY_HI = F(1, 16), F(15, 16)
HOLES = [(F(5,16), F(1,2), F(7,256)), (F(3,8), F(1,2), F(7,256)),
         (F(29,32), F(11,16), F(3,128)), (F(5,8), F(9,32), F(1,64))]
A = [[F(17,16), F(1,8), F(1,32)], [F(1,32), F(31,32), F(1,16)],
     [-F(1,64), F(1,32), F(33,32)]]
B = [F(1,32), -F(1,64), F(1,64)]


def lattice(interval):
    a, b = interval
    return (F((a*SCALE).numerator // (a*SCALE).denominator, SCALE),
            F(-((-b*SCALE).numerator // (-b*SCALE).denominator), SCALE))


def add(a, b):
    return a[0]+b[0], a[1]+b[1]


def mul(a, b):
    v = [x*y for x in a for y in b]
    return min(v), max(v)


def scale(a, factor):
    return mul(a, (factor, factor))


def tent(t):
    t = min(F(1), max(F(0), t))
    k = min(int(t*4), 3)
    return VALUES[k]+(t-KNOTS[k])*4*(VALUES[k+1]-VALUES[k])


def tent_interval(a):
    values = [tent(a[0]), tent(a[1])]
    values.extend(VALUES[k] for k in range(5) if a[0] <= KNOTS[k] <= a[1])
    return min(values), max(values)


def u_interval(kind, box):
    if kind == "identity":
        return [(F(0), F(0))]*3
    if kind == "affine":
        clipped = [(max(F(0), min(F(1), a)), max(F(0), min(F(1), b))) for a,b in box]
        out = []
        for i in range(3):
            v = B[i], B[i]
            for j in range(3):
                v = add(v, scale(clipped[j], A[i][j]-int(i==j)))
            out.append(lattice(v))
        return out
    if kind != "nonlinear":
        raise ValueError(kind)
    a,b,c = map(tent_interval, box)
    ab, ac, bc = mul(a,b), mul(a,c), mul(b,c)
    return [lattice(add(scale(bc,F(1,16)),scale(ab,F(1,64)))),
            lattice(add(scale(ac,F(3,64)),scale(bc,-F(1,64)))),
            lattice(add(scale(ab,F(1,32)),scale(mul(ab,c),F(1,64))))]


def forward(kind, x):
    """Exact point evaluation, deliberately without lattice rounding."""
    if kind == "identity":
        return tuple(x)
    if kind == "affine":
        z = [min(F(1), max(F(0), v)) for v in x]
        return tuple(x[i]+B[i]+sum((A[i][j]-int(i==j))*z[j] for j in range(3)) for i in range(3))
    a,b,c = map(tent, x)
    return x[0]+b*c/16+a*b/64, x[1]+3*a*c/64-b*c/64, x[2]+a*b/32+a*b*c/64


def rational_box(box):
    return tuple((F(float(a)),F(float(b))) for a,b in zip(box.lo,box.hi))


def solid_classify(box):
    if any(b < BODY_LO or a > BODY_HI for a,b in box):
        return "EMPTY"
    full = all(a > BODY_LO and b < BODY_HI for a,b in box)
    for cx,cy,r in HOLES:
        far2, near2 = F(0), F(0)
        for (a,b), center in zip(box[:2], (cx,cy)):
            far2 += max(abs(a-center),abs(b-center))**2
            near2 += max(a-center,center-b,F(0))**2
        if far2 < r*r:
            return "EMPTY"
        full &= near2 > r*r
    return "FULL" if full else "MIXED"


def verify_witness(kind, box, point):
    x = tuple(F(float(v)) for v in point)
    if solid_classify(tuple((v,v) for v in x)) != "FULL":
        return False
    y = forward(kind,x)
    return all(a < v < b for (a,b),v in zip(rational_box(box),y))


def inverse_enclosure(kind, query, iterations=18):
    # Root X exists globally by the independently checked q<1 gate.
    whole = [(F(0),F(1))]*3
    u = u_interval(kind,whole)
    current = tuple(lattice((a-v,b-w)) for (a,b),(w,v) in zip(query,u))
    for _ in range(iterations):
        u = u_interval(kind,current)
        candidate = [lattice((a-v,b-w)) for (a,b),(w,v) in zip(query,u)]
        new = tuple((max(a,c),min(b,d)) for (a,b),(c,d) in zip(current,candidate))
        if any(a>b for a,b in new):
            raise AssertionError("root enclosure became empty")
        if new == current:
            break
        current = new
    return current


def independent_point(kind, center):
    """Floating fixed-point seed ONLY; its final witness is checked exactly."""
    x = tuple(F(float(c)) for c in center)
    target = x
    for _ in range(48):
        y = forward(kind,x)
        # Exact outward interval bounds are not used to ACCEPT this point.
        x = tuple(F(round(float(a-b+c)*2**40),2**40) for a,b,c in zip(x,y,target))
    return x


def classify(kind, box, max_nodes=255, iterations=18):
    root = rational_box(box)
    stack = [(root,0)]
    nodes, unresolved, proofs = 0, False, []
    while stack and nodes < max_nodes:
        query, depth = stack.pop()
        nodes += 1
        inv = inverse_enclosure(kind,query,iterations)
        if solid_classify(inv) == "EMPTY":
            proofs.append({"query": [[str(v) for v in pair] for pair in query],
                           "preimage": [[str(v) for v in pair] for pair in inv]})
            continue
        center = [(a+b)/2 for a,b in query]
        x = independent_point(kind,center)
        if solid_classify(tuple((v,v) for v in x)) == "FULL":
            y = forward(kind,x)
            if all(a<v<b for (a,b),v in zip(root,y)):
                return {"status":"INTERSECTS", "nodes":nodes,
                        "witness_exact":[str(v) for v in x], "image_exact":[str(v) for v in y]}
        axis = max(range(3),key=lambda i:query[i][1]-query[i][0])
        a,b = query[axis]
        if depth >= 24 or b-a <= F(1,2**30):
            unresolved = True
        else:
            m = (a+b)/2
            l,r = list(query),list(query)
            l[axis],r[axis] = (a,m),(m,b)
            stack.extend([(tuple(r),depth+1),(tuple(l),depth+1)])
    if stack or unresolved:
        return {"status":"UNRESOLVED", "nodes":nodes,
                "remaining":len(stack), "reason":"exact oracle budget/contact limit"}
    return {"status":"DISJOINT", "nodes":nodes, "exclusion_cover":proofs}


def exact_assumptions(kind, n=4):
    """Independently reconstruct rational nodal edge derivative bounds."""
    G = [[F(0) for _ in range(3)] for _ in range(3)]
    for cell in product(range(n),repeat=3):
        for axis in range(3):
            other = [i for i in range(3) if i != axis]
            for bits in product((0,1),repeat=2):
                lo = [F(v,n) for v in cell]
                for i,b in zip(other,bits):
                    lo[i] += F(b,n)
                hi = lo.copy()
                hi[axis] += F(1,n)
                a,b = forward(kind,lo),forward(kind,hi)
                for i in range(3):
                    d = (b[i]-a[i])*n-int(i==axis)
                    G[i][axis] = max(G[i][axis],abs(d))
    q = max(map(sum,G))
    assert q < 1
    return {"G_exact":[[str(v) for v in row] for row in G], "q_exact":str(q),
            "alpha_exact":str(1/(1-q)), "all_cell_bilinear_edge_enclosure":True}
