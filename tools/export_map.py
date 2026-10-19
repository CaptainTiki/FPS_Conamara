"""levels/<name>.json (from mapgen.py) -> levels/<name>.map  (Valve 220, TrenchBroom)

The layout is cells; this file is the *dressing rules* that turn cells into brushes.
Every rule writes into its own TrenchBroom layer so a hand edit can select-by-layer:

  floor      solid columns up to floor height; tops floor / floor_metal / floor_grate
  border     floor_grate strip along every wall and riser (hides the tiling seam)
  ceiling    solid columns down to ceiling height
  skirting   kick band at the base of every wall
  panel      wall panels, varied per run by hash (wall / wall_vent)
  cornice    chamfer band under every ceiling edge
  beam       ceiling beams across rooms every 4th row
  stairs     4 real steps per stair cell
  lamp       light_strip fixture under every light
  doorframe  posts + lintel narrowing a door cell to the Door scene's slab (1.5 m x 3.25 m)

Entities: info_player_start, light (Godot property names, FuncGodot applies them to an
OmniLight3D), prop_door (-> scenes/props/door.tscn).

Units: 32 per metre. 1 cell = 64 (2 m). Floor step 32 (1 m). Ceiling level 56 (1.75 m).
Run: python3 tools/export_map.py levels/seed1337.json [quake|kit]
"""
import json, math, os, sys

U = 32                     # quake units per metre
CELL = 64
LVL = 32                   # floor level step
LVC = 56                   # ceiling level step (taller rooms than the floor grid implies)
VOID, FLOOR, DOOR, LOCKED, STAIRS, LIFT, PIT, CATWALK = range(8)

def ceil_u(f, c): return f * LVL + (c - f) * LVC

# ---------------------------------------------------------------- theme ----
# Role -> texture path under art/textures/. Swap the table to re-dress a level.
# "quake" = LibreQuake tech set (BSD-3, docs/licenses). "kit" = our own generated tiles.
THEMES = {
    "kit": {
        "floor": "tb/floor", "floor_metal": "tb/floor_metal", "floor_grate": "tb/floor_grate", "pit": "tb/gutter_glow",
        "kick": "tb/kick", "chamfer": "tb/chamfer", "ceiling": "tb/ceiling", "beam": "tb/beam",
        "lamp": "tb/light_strip", "trim": "tb/trim", "rod": "tb/trim", "door_frame": "tb/trim", "door": "tb/door",
        "rib": "tb/trim", "pipe": "tb/trim", "pilaster": "tb/trim", "vent": "tb/wall_vent", "boxes": ["tb/console", "tb/wall_vent"],
        "panels": [("tb/wall", .72), ("tb/wall_vent", 1.0)],
    },
    "quake": {
        "floor": "lq/tech/t_flor2a", "floor_metal": "lq/tech/t_flor1a", "floor_grate": "lq/tech/tek_grate", "pit": "lq/tech/tek_grate",
        "kick": "lq/tech/t_trim2a", "chamfer": "lq/tech/t_trim1c", "ceiling": "lq/tech/t_flat05", "beam": "lq/tech/t_trim1d",
        "lamp": "lq/tech/tlight11_fbr", "trim": "lq/tech/metalstrip_1", "rod": "lq/tech/tek_pipe2", "door_frame": "lq/tech/t_trim2d", "door": "lq/tech/tek_door1",
        "rib": "lq/tech/t_trim2d", "pipe": "lq/tech/tek_pipe2", "pilaster": "lq/tech/t_trim1c", "vent": "lq/tech/t_blok06h",
        "boxes": ["lq/tech/comp1_1", "lq/tech/comp1_2", "lq/tech/comp1_5", "lq/tech/comp1_8", "lq/tech/t_blok05", "lq/tech/t_blok04h"],
        "panels": [("lq/tech/t_wall1a", .30), ("lq/tech/t_wall3a", .50), ("lq/tech/t_blok03", .65),
                   ("lq/tech/t_blok09", .78), ("lq/tech/t_wall1b", .88), ("lq/tech/comp1_2", .94), ("lq/tech/t_blok06", 1.0)],
    },
}
THEME = THEMES["quake"]
def role_tex(role): return THEME.get(role, role)
def panel_tex(t):
    for name, upto in THEME["panels"]:
        if t < upto: return name
    return THEME["panels"][-1][0]

# ---------------------------------------------------------------- brushes ----
def box(x0, y0, z0, x1, y1, z1, top, side=None, bottom=None):
    """Axis-aligned brush with per-face textures. Valve 220 axes; outward normals."""
    side = side or top; bottom = bottom or top
    top, side, bottom = role_tex(top), role_tex(side), role_tex(bottom)
    faces = [
        (((x1, y0, z1), (x0, y0, z1), (x0, y1, z1)), top,    "[ 1 0 0 0 ] [ 0 -1 0 0 ]"),  # +z
        (((x0, y1, z0), (x0, y0, z0), (x1, y0, z0)), bottom, "[ 1 0 0 0 ] [ 0 -1 0 0 ]"),  # -z
        (((x1, y1, z0), (x1, y0, z0), (x1, y0, z1)), side,   "[ 0 1 0 0 ] [ 0 0 -1 0 ]"),  # +x
        (((x0, y0, z1), (x0, y0, z0), (x0, y1, z0)), side,   "[ 0 1 0 0 ] [ 0 0 -1 0 ]"),  # -x
        (((x0, y1, z1), (x0, y1, z0), (x1, y1, z0)), side,   "[ 1 0 0 0 ] [ 0 0 -1 0 ]"),  # +y
        (((x1, y0, z1), (x1, y0, z0), (x0, y0, z0)), side,   "[ 1 0 0 0 ] [ 0 0 -1 0 ]"),  # -y
    ]
    out = ["{"]
    for pts, tex, axes in faces:
        out.append(" ".join(f"( {a:g} {b:g} {c:g} )" for a, b, c in pts) + f" {tex} {axes} 0 1 1")
    out.append("}")
    return "\n".join(out)

def wedge(axis, lo, hi, z0, z1, tex="clip"):
    tex = role_tex(tex)
    """Ramp prism. axis 'x': lo/hi = (x, zmin, zmax) edges; axis 'y': lo/hi = (y, xmin, xmax).
    Low edge at height z0 rising to z1 at the high edge; solid down to z0."""
    if axis == "x":
        xl, xh, a0, a1 = lo[0], hi[0], lo[1], lo[2]
        P = lambda x, y, z: (x, y, z)
    else:
        xl, xh, a0, a1 = lo[0], hi[0], lo[1], lo[2]
        P = lambda x, y, z: (y, x, z)
    # bottom, two ends (a0, a1), vertical face at the high edge, and the slope
    ax = "[ 1 0 0 0 ] [ 0 -1 0 0 ]"
    faces = [
        ((P(xh, a0, z0), P(xl, a0, z0), P(xl, a1, z0)), ax),                       # bottom (-z)
        ((P(xl, a0, z0), P(xh, a0, z0), P(xh, a0, z1)), ax),                       # side a0
        ((P(xh, a1, z0), P(xl, a1, z0), P(xl, a1, z1)), ax),                       # side a1
        ((P(xh, a0, z0), P(xh, a1, z0), P(xh, a1, z1)), ax),                       # high end wall
        ((P(xl, a0, z0), P(xl, a1, z0), P(xh, a1, z1)), ax),                       # slope
    ]
    # fix winding by checking each normal against the centroid
    import numpy as _np
    pts_all = _np.array([p for f, _ in faces for p in f], dtype=float)
    cen = pts_all.mean(axis=0)
    out = ["{"]
    for pts, axes in faces:
        p = _np.array(pts, dtype=float)
        n = _np.cross(p[0] - p[1], p[2] - p[1])
        if _np.dot(n, p[1] - cen) < 0: pts = (pts[0], pts[2], pts[1])
        out.append(" ".join(f"( {a:g} {b:g} {c:g} )" for a, b, c in pts) + f" {tex} {axes} 0 1 1")
    out.append("}")
    return "\n".join(out)

def prism(poly, z0, z1, side_tex, cap_tex):
    """Vertical prism over a 2D polygon [(x, y), ...] (any winding). Each side face gets
    Valve texture axes along its edge so textures don't smear on diagonals."""
    import numpy as _np
    side_tex, cap_tex = role_tex(side_tex), role_tex(cap_tex)
    n = len(poly)
    faces = []
    cap = "[ 1 0 0 0 ] [ 0 -1 0 0 ]"
    faces.append((((poly[0][0], poly[0][1], z1), (poly[1][0], poly[1][1], z1), (poly[2][0], poly[2][1], z1)), cap_tex, cap))
    faces.append((((poly[0][0], poly[0][1], z0), (poly[1][0], poly[1][1], z0), (poly[2][0], poly[2][1], z0)), cap_tex, cap))
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L
        axes = f"[ {ux:.4f} {uy:.4f} 0 0 ] [ 0 0 -1 0 ]"
        faces.append((((ax, ay, z0), (bx, by, z0), (bx, by, z1)), side_tex, axes))
    cen = _np.array([(x, y, (z0 + z1) / 2) for x, y in poly], dtype=float).mean(axis=0)
    out = ["{"]
    for pts, tex, axes in faces:
        p = _np.array(pts, dtype=float)
        nrm = _np.cross(p[0] - p[1], p[2] - p[1])
        if _np.dot(nrm, p[1] - cen) < 0: pts = (pts[0], pts[2], pts[1])
        out.append(" ".join(f"( {a:g} {b:g} {c:g} )" for a, b, c in pts) + f" {tex} {axes} 0 1 1")
    out.append("}")
    return "\n".join(out)

def extrude(axis, a0, a1, poly, tex, cap=None):
    """Prism of a 2D polygon extruded along `axis` ('x' | 'y' | 'z') from a0 to a1.
    poly coordinates are the other two axes in order: x->(y,z)  y->(x,z)  z->(x,y)."""
    import numpy as _np
    tex = role_tex(tex); cap = role_tex(cap or tex)
    def P(a, uv):
        u, v = uv
        return {"x": (a, u, v), "y": (u, a, v), "z": (u, v, a)}[axis]
    n = len(poly); faces = []
    faces.append(((P(a1, poly[0]), P(a1, poly[1]), P(a1, poly[2])), cap))
    faces.append(((P(a0, poly[0]), P(a0, poly[1]), P(a0, poly[2])), cap))
    for i in range(n):
        faces.append(((P(a0, poly[i]), P(a0, poly[(i + 1) % n]), P(a1, poly[(i + 1) % n])), tex))
    pts_all = _np.array([p for f, _ in faces for p in f], dtype=float); cen = pts_all.mean(axis=0)
    out = ["{"]
    for pts, t in faces:
        p = _np.array(pts, dtype=float)
        nrm = _np.cross(p[0] - p[1], p[2] - p[1])
        if _np.dot(nrm, p[1] - cen) < 0: pts = (pts[0], pts[2], pts[1]); p = _np.array(pts, dtype=float)
        nrm = _np.cross(p[0] - p[1], p[2] - p[1]); nrm /= _np.linalg.norm(nrm)
        # texture axes in the face plane: u along the first edge, v = n x u
        u = p[0] - p[1]; u /= _np.linalg.norm(u); v = _np.cross(nrm, u)
        axes = f"[ {u[0]:.4f} {u[1]:.4f} {u[2]:.4f} 0 ] [ {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} 0 ]"
        out.append(" ".join(f"( {a:g} {b:g} {c:g} )" for a, b, c in pts) + f" {t} {axes} 0 1 1")
    out.append("}")
    return "\n".join(out)

def octagon(cx, cy, r):
    k = r * 0.4142
    return [(cx - k, cy - r), (cx + k, cy - r), (cx + r, cy - k), (cx + r, cy + k), (cx + k, cy + r), (cx - k, cy + r), (cx - r, cy + k), (cx - r, cy - k)]

def merge_rects(cells):
    cells = set(cells); rects = []
    while cells:
        x0, y0 = min(cells, key=lambda p: (p[1], p[0])); x1 = x0
        while (x1 + 1, y0) in cells: x1 += 1
        y1 = y0
        while all((x, y1 + 1) in cells for x in range(x0, x1 + 1)): y1 += 1
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): cells.discard((x, y))
        rects.append((x0, y0, x1 + 1, y1 + 1))
    return rects

def merge_runs(segs, max_len=99):
    segs = set(segs); runs = []
    while segs:
        k, i0 = min(segs); i1 = i0
        while (k, i1 + 1) in segs and i1 - i0 + 1 < max_len: i1 += 1
        for i in range(i0, i1 + 1): segs.discard((k, i))
        runs.append((k, i0, i1 + 1))
    return runs

def hash01(a, b):
    h = (a * 374761393 + b * 668265263) ^ 0x5bd1e995
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return ((h ^ (h >> 16)) & 0xffffffff) / 4294967296.0

# ---------------------------------------------------------------- build ----
def build(level):
    H = level["height"]
    cells = {(c["x"], c["y"]): c for c in level["cells"]}
    at = cells.get
    fmin = min(c["f"] for c in cells.values()) - 1
    cmax = max(ceil_u(c["f"], c["c"]) for c in cells.values()) + 2 * LVL
    base = fmin * LVL - 16
    top = cmax + 16
    def Y(y): return (H - y) * CELL          # flip rows so the map reads like the PNG
    layers = {k: [] for k in ["floor", "border", "ceiling", "skirting", "panel", "cornice", "beam", "stairs", "lamp", "doorframe", "rib", "pipe", "pilaster", "wallbox", "pillar"]}
    ents = []
    room_of = {}
    for i, r in enumerate(level["rooms"]):
        for p in r["cells"]: room_of[tuple(p)] = i

    def floor_u(c): return c["f"] * LVL
    def ceil_of(c): return ceil_u(c["f"], c["c"])

    # --- floors: solid columns from base to the floor, grouped by (height, top texture)
    def floor_tex(c):
        if c["t"] == PIT: return "pit"
        if c["t"] == CATWALK: return "floor_grate"
        if (c["x"], c["y"]) not in room_of: return "floor_metal"     # corridors
        return "floor"
    groups = {}
    for (x, y), c in cells.items():
        if c["t"] == STAIRS: continue                                 # stairs get their own column below
        groups.setdefault((c["f"], floor_tex(c)), set()).add((x, y))
    for (f, tex), cs in groups.items():
        for x0, y0, x1, y1 in merge_rects(cs):
            layers["floor"].append(box(x0 * CELL, Y(y1), base, x1 * CELL, Y(y0), f * LVL, tex, "kick"))

    # --- ceilings: solid columns from the ceiling up
    groups = {}
    for (x, y), c in cells.items():
        groups.setdefault(ceil_of(c), set()).add((x, y))
    for cz, cs in groups.items():
        for x0, y0, x1, y1 in merge_rects(cs):
            layers["ceiling"].append(box(x0 * CELL, Y(y1), cz, x1 * CELL, Y(y0), top, "chamfer", "chamfer", "ceiling"))

    # --- walls on void edges: skirting (16u) + panel + cornice (16u), full base->top so the map seals
    # edge keys: direction -> set of (k, i) runs; panel texture chosen per run by hash
    E, W_, S, N = set(), set(), set(), set()
    corners = {}      # room cell with exactly two adjacent void sides -> which (ew, ns)
    for (x, y), c in cells.items():
        ve, vw, vs, vn = (x + 1, y) not in cells, (x - 1, y) not in cells, (x, y + 1) not in cells, (x, y - 1) not in cells
        if (x, y) in room_of and c["t"] == FLOOR and (ve != vw) and (vs != vn):
            corners[(x, y)] = (1 if ve else -1, 1 if vs else -1)
            continue          # the diagonal prism replaces this cell's two outer walls
        if ve: E.add((x, y))
        if vw: W_.add((x, y))
        if vs: S.add((y, x))
        if vn: N.add((y, x))
    pillars = set()
    for (x, y) in list(room_of):
        for d in ((1, 0), (0, 1)):
            v = (x + d[0], y + d[1])
            if v in cells: continue
            if all((v[0] + dx, v[1] + dy) in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                pillars.add(v)
    for (vx, vy) in pillars:
        E.discard((vx - 1, vy)); W_.discard((vx + 1, vy)); S.discard((vy - 1, vx)); N.discard((vy + 1, vx))
        c = cells[(vx - 1, vy)]; fz, cz = floor_u(c), ceil_of(c)
        poly = octagon(vx * CELL + CELL / 2, Y(vy + 1) + CELL / 2, CELL / 2)
        layers["pillar"].append(prism(poly, base, fz + 16, "kick", "kick"))
        layers["pillar"].append(prism(poly, fz + 16, cz - 16, panel_tex(hash01(vx, vy)), "chamfer"))
        layers["pillar"].append(prism(poly, cz - 16, top, "chamfer", "chamfer"))
    for (x, y), (ew, ns) in corners.items():
        c = cells[(x, y)]; fz, cz = floor_u(c), ceil_of(c)
        X0, X1, Z0, Z1 = x * CELL, (x + 1) * CELL, Y(y + 1), Y(y)        # Z0 = south (screen down), Z1 = north
        # the solid half on the void side: three corners of the cell
        if (ew, ns) == (1, 1):    poly = [(X1, Z1), (X1, Z0), (X0, Z0)]     # E & S void: SE half, hypotenuse NE->SW
        if (ew, ns) == (1, -1):   poly = [(X1, Z0), (X1, Z1), (X0, Z1)]     # E & N void: NE half
        if (ew, ns) == (-1, 1):   poly = [(X0, Z1), (X0, Z0), (X1, Z0)]     # W & S void: SW half
        if (ew, ns) == (-1, -1):  poly = [(X0, Z0), (X0, Z1), (X1, Z1)]     # W & N void: NW half
        panel = panel_tex(hash01(x * 5 + 1, y * 3 + 2))
        layers["skirting"].append(prism(poly, base, fz + 16, "kick", "kick"))
        layers["panel"].append(prism(poly, fz + 16, cz - 16, panel, panel))
        layers["cornice"].append(prism(poly, cz - 16, top, "chamfer", "chamfer"))
    def wall_run(x0, y0, x1, y1, floor_z, ceil_z, key):
        """x0..x1 / y0..y1 in quake units (thin box). Splits into skirting / panel / cornice."""
        t = hash01(*key)
        panel = panel_tex(t)
        layers["skirting"].append(box(x0, y0, base, x1, y1, floor_z + 16, "kick"))
        layers["panel"].append(box(x0, y0, floor_z + 16, x1, y1, ceil_z - 16, panel))
        layers["cornice"].append(box(x0, y0, ceil_z - 16, x1, y1, top, "chamfer"))
    def edge_runs(segs, vertical):
        # runs of cells sharing floor and ceiling so the bands line up; max 3 cells so panels vary
        out = []
        for k, i0, i1 in merge_runs(segs, 1):
            out.append((k, i0, i1))
        # group consecutive single segments with equal floor/ceil into runs up to 3
        out.sort(); runs = []; cur = None
        for k, i0, i1 in out:
            c = at((i0, k)) if not vertical else at((k, i0))
            fz, cz = floor_u(c), ceil_of(c)
            if cur and cur[0] == k and cur[2] == i0 and cur[3] == fz and cur[4] == cz and cur[2] - cur[1] < 3:
                cur[2] = i1
            else:
                if cur: runs.append(cur)
                cur = [k, i0, i1, fz, cz]
        if cur: runs.append(cur)
        return runs
    for x, y0, y1, fz, cz in edge_runs(E, True):
        wall_run((x + 1) * CELL, Y(y1), (x + 1) * CELL + 16, Y(y0), fz, cz, (x + 1, y0))
    for x, y0, y1, fz, cz in edge_runs(W_, True):
        wall_run(x * CELL - 16, Y(y1), x * CELL, Y(y0), fz, cz, (x - 1, y0))
    for y, x0, x1, fz, cz in edge_runs(S, False):      # void row is y+1
        xs = x0 * CELL + (16 if at((x0 - 1, y + 1)) and (x0 - 1, y + 1) not in corners else 0)
        xe = x1 * CELL - (16 if at((x1, y + 1)) and (x1, y + 1) not in corners else 0)
        wall_run(xs, Y(y + 1) - 16, xe, Y(y + 1), fz, cz, (x0, y + 1))
    for y, x0, x1, fz, cz in edge_runs(N, False):      # void row is y-1
        xs = x0 * CELL + (16 if at((x0 - 1, y - 1)) and (x0 - 1, y - 1) not in corners else 0)
        xe = x1 * CELL - (16 if at((x1, y - 1)) and (x1, y - 1) not in corners else 0)
        wall_run(xs, Y(y), xe, Y(y) + 16, fz, cz, (x0, y - 1))

    # --- diagonal risers: a low cell with higher floor on two adjacent sides (a step in a pit's
    #     or a sunken area's outline) gets a prism filling its half on the high side, so the
    #     riser runs at 45 degrees like the walls do
    for (x, y), c in cells.items():
        if c["t"] in (STAIRS, LIFT): continue
        f = floor_u(c)
        def hi(dx, dy):
            o = at((x + dx, y + dy)); return o is not None and o["t"] not in (STAIRS,) and floor_u(o) > f
        e, w, s_, n = hi(1, 0), hi(-1, 0), hi(0, 1), hi(0, -1)
        if (e == w) or (s_ == n): continue
        ew, ns = (1 if e else -1), (1 if s_ else -1)
        if not hi(ew, ns): continue                      # diagonal must be high too (a real step, not a notch)
        oe, os_ = at((x + ew, y)), at((x, y + ns))
        h = min(floor_u(oe), floor_u(os_))
        X0, X1, Z0, Z1 = x * CELL, (x + 1) * CELL, Y(y + 1), Y(y)
        if (ew, ns) == (1, 1):    poly = [(X1, Z1), (X1, Z0), (X0, Z0)]
        if (ew, ns) == (1, -1):   poly = [(X1, Z0), (X1, Z1), (X0, Z1)]
        if (ew, ns) == (-1, 1):   poly = [(X0, Z1), (X0, Z0), (X1, Z0)]
        if (ew, ns) == (-1, -1):  poly = [(X0, Z0), (X0, Z1), (X1, Z1)]
        layers["floor"].append(prism(poly, f, h, "kick", floor_tex(oe)))

    # --- border grate strips along walls and risers (12u wide, 2u tall on the floor)
    for (x, y), c in cells.items():
        if c["t"] in (PIT, CATWALK, STAIRS): continue
        fz = floor_u(c); X, Z0, Z1 = x * CELL, Y(y + 1), Y(y)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            o = at((x + dx, y + dy))
            if o and floor_u(o) <= fz: continue
            if (x, y) in corners and not o: continue
            if dx == 1: layers["border"].append(box(X + CELL - 12, Z0, fz, X + CELL, Z1, fz + 2, "floor_grate"))
            if dx == -1: layers["border"].append(box(X, Z0, fz, X + 12, Z1, fz + 2, "floor_grate"))
            if dy == 1: layers["border"].append(box(X, Z0, fz, X + CELL, Z0 + 12, fz + 2, "floor_grate"))
            if dy == -1: layers["border"].append(box(X, Z1 - 12, fz, X + CELL, Z1, fz + 2, "floor_grate"))

    # --- depth pass. Everything here is decoration a hand edit can delete by layer.
    def corridor(p): return p in cells and p not in room_of and cells[p]["t"] in (FLOOR, DOOR, LOCKED, STAIRS)
    def wall_sides(x, y):
        """void neighbours of a room cell: list of (dx, dy)."""
        return [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y + dy) not in cells]
    # corridor ribs: every 4th cell across an E-W or N-S run, posts on both walls + lintel
    for (x, y), c in cells.items():
        if not corridor((x, y)) or c["t"] != FLOOR: continue
        fz, cz = floor_u(c), ceil_of(c)
        ew = corridor((x + 1, y)) and corridor((x - 1, y)); ns = corridor((x, y + 1)) and corridor((x, y - 1))
        if ew and not ns and x % 4 == 0 and not corridor((x, y - 1)):
            k = 0
            while corridor((x, y + k + 1)): k += 1
            Z0, Z1 = Y(y + k + 1), Y(y); X0 = x * CELL + 24
            layers["rib"].append(box(X0, Z0, cz - 20, X0 + 16, Z1, cz, "rib"))
            layers["rib"].append(box(X0, Z1 - 16, fz, X0 + 16, Z1, cz, "rib"))
            layers["rib"].append(box(X0, Z0, fz, X0 + 16, Z0 + 16, cz, "rib"))
        if ns and not ew and y % 4 == 0 and not corridor((x - 1, y)):
            k = 0
            while corridor((x + k + 1, y)): k += 1
            X0, X1 = x * CELL, (x + k + 1) * CELL; Z0 = Y(y + 1) + 24
            layers["rib"].append(box(X0, Z0, cz - 20, X1, Z0 + 16, cz, "rib"))
            layers["rib"].append(box(X0, Z0, fz, X0 + 16, Z0 + 16, cz, "rib"))
            layers["rib"].append(box(X1 - 16, Z0, fz, X1, Z0 + 16, cz, "rib"))
    # overhead pipe pairs along corridor runs, hugging one wall
    done = set()
    for (x, y), c in cells.items():
        if not corridor((x, y)) or (x, y) in done: continue
        if corridor((x + 1, y)) and not corridor((x, y - 1)):          # E-W run with a north wall
            x0 = x
            while corridor((x0 - 1, y)) and not corridor((x0 - 1, y - 1)): x0 -= 1
            x1 = x
            while corridor((x1 + 1, y)) and not corridor((x1 + 1, y - 1)): x1 += 1
            for xx in range(x0, x1 + 1): done.add((xx, y))
            if x1 - x0 < 2: continue
            cz = min(ceil_of(cells[(xx, y)]) for xx in range(x0, x1 + 1))
            zw = Y(y)                                                      # wall plane (north)
            for off in (14, 30):
                layers["pipe"].append(extrude("x", x0 * CELL + 8, (x1 + 1) * CELL - 8, octagon(zw - off, cz - 22, 6), "pipe"))
        elif corridor((x, y + 1)) and not corridor((x - 1, y)):         # N-S run with a west wall
            y0 = y
            while corridor((x, y0 - 1)) and not corridor((x - 1, y0 - 1)): y0 -= 1
            y1 = y
            while corridor((x, y1 + 1)) and not corridor((x - 1, y1 + 1)): y1 += 1
            for yy in range(y0, y1 + 1): done.add((x, yy))
            if y1 - y0 < 2: continue
            cz = min(ceil_of(cells[(x, yy)]) for yy in range(y0, y1 + 1))
            xw = x * CELL
            for off in (14, 30):
                layers["pipe"].append(extrude("y", Y(y1 + 1) + 8, Y(y0) - 8, octagon(xw + off, cz - 22, 6), "pipe"))
    # room walls: pilasters every 4 cells, vertical pipes, wall boxes, vents, crates
    for (x, y), c in cells.items():
        if (x, y) not in room_of or c["t"] != FLOOR or (x, y) in corners: continue
        sides = wall_sides(x, y)
        if not sides: continue
        fz, cz = floor_u(c), ceil_of(c)
        X0, X1, Z0, Z1 = x * CELL, (x + 1) * CELL, Y(y + 1), Y(y)
        h = hash01(x * 11 + 3, y * 17 + 5)
        for (dx, dy) in sides:
            # frame in wall-local terms: `along` is the wall direction, `into` the room
            def wall_box(depth, w, z0, z1, tex, centre=0.5):
                """a box against this wall: `w` wide along the wall, `depth` into the room, z0..z1 tall"""
                if dx == 1:   return box(X1 - depth, Z0 + (CELL - w) * centre, z0, X1, Z0 + (CELL - w) * centre + w, z1, tex)
                if dx == -1:  return box(X0, Z0 + (CELL - w) * centre, z0, X0 + depth, Z0 + (CELL - w) * centre + w, z1, tex)
                if dy == 1:   return box(X0 + (CELL - w) * centre, Z0, z0, X0 + (CELL - w) * centre + w, Z0 + depth, z1, tex)
                if dy == -1:  return box(X0 + (CELL - w) * centre, Z1 - depth, z0, X0 + (CELL - w) * centre + w, Z1, z1, tex)
            def wall_pipe(r, off):
                if dx == 1:   return prism(octagon(X1 - off, (Z0 + Z1) / 2, r), fz, cz, "pipe", "pipe")
                if dx == -1:  return prism(octagon(X0 + off, (Z0 + Z1) / 2, r), fz, cz, "pipe", "pipe")
                if dy == 1:   return prism(octagon((X0 + X1) / 2, Z0 + off, r), fz, cz, "pipe", "pipe")
                if dy == -1:  return prism(octagon((X0 + X1) / 2, Z1 - off, r), fz, cz, "pipe", "pipe")
            along = y if dx else x
            if along % 4 == 0:
                layers["pilaster"].append(wall_box(12, 32, fz, cz, "pilaster"))
                continue
            if h < .07:
                layers["pipe"].append(wall_pipe(7, 16))
                layers["pipe"].append(wall_box(22, 12, fz + 60, fz + 68, "rib"))     # bracket
            elif h < .16:
                tex = THEME["boxes"][int(hash01(y * 7, x * 3) * len(THEME["boxes"]))]
                layers["wallbox"].append(wall_box(6, 40, fz + 44, fz + 92, tex))
            elif h < .22:
                layers["wallbox"].append(wall_box(5, 48, cz - 44, cz - 20, "vent"))
            elif h < .27 and c["t"] == FLOOR:
                p = (x, y)
                cx_, cz_ = (X0 + X1) / 2 - dx * 14, (Z0 + Z1) / 2 + dy * 14
                ents.append(f'"classname" "{"prop_crate_stack" if h < .245 else "prop_crate"}"\n"origin" "{cx_:g} {cz_:g} {fz + 2:g}"\n"angle" "{int(hash01(x, y) * 4) * 90}"')
            break    # one feature per cell

    # --- beams every 4th row inside rooms where the ceiling is continuous
    for (x, y), c in cells.items():
        if y % 4 or c["t"] != FLOOR or (x, y) not in room_of: continue
        e, w = at((x + 1, y)), at((x - 1, y))
        if not (e or w) or (e and e["c"] != c["c"]) or (w and w["c"] != c["c"]): continue
        cz = ceil_of(c)
        if cz - floor_u(c) < 2.4 * U: continue
        zc = Y(y + 1) + CELL / 2
        layers["beam"].append(box(x * CELL, zc - 6, cz - 14, (x + 1) * CELL, zc + 6, cz, "beam"))

    # --- stairs: 8 steps (12.5 cm) from the lower neighbour's level up to this cell's level,
    #     plus an invisible clip ramp over them so the player walks up smoothly
    for (x, y), c in cells.items():
        if c["t"] != STAIRS: continue
        f1 = floor_u(c); lower = None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            o = at((x + dx, y + dy))
            if o and floor_u(o) < f1: lower = (dx, dy, floor_u(o)); break
        X, Z0, Z1 = x * CELL, Y(y + 1), Y(y)
        if not lower:
            layers["floor"].append(box(X, Z0, base, X + CELL, Z1, f1, "floor_metal", "kick")); continue
        dx, dy, f0 = lower; N_ = 8; rise = (f1 - f0) / N_; run = CELL / N_
        layers["floor"].append(box(X, Z0, base, X + CELL, Z1, f0, "floor_metal", "kick"))
        for i in range(N_):
            h = f0 + rise * (i + 1)
            if dx == 1:   layers["stairs"].append(box(X + CELL - run * (i + 1), Z0, f0, X + CELL - run * i, Z1, h, "floor_metal", "kick"))
            if dx == -1:  layers["stairs"].append(box(X + run * i, Z0, f0, X + run * (i + 1), Z1, h, "floor_metal", "kick"))
            if dy == 1:   layers["stairs"].append(box(X, Z0 + run * i, f0, X + CELL, Z0 + run * (i + 1), h, "floor_metal", "kick"))
            if dy == -1:  layers["stairs"].append(box(X, Z1 - run * (i + 1), f0, X + CELL, Z1 - run * i, h, "floor_metal", "kick"))
        # clip ramp through the step tops: starts one tread into the lower cell at floor level,
        # reaches the upper floor one tread before the cell ends (so no lip at either end)
        if dx == 1:    lo, hi = ((X + CELL + run, Z0, Z1), (X + run, Z0, Z1)); axis = "x"
        if dx == -1:   lo, hi = ((X - run, Z0, Z1), (X + CELL - run, Z0, Z1)); axis = "x"
        if dy == 1:    lo, hi = ((Z0 - run, X, X + CELL), (Z1 - run, X, X + CELL)); axis = "y"
        if dy == -1:   lo, hi = ((Z1 + run, X, X + CELL), (Z0 + run, X, X + CELL)); axis = "y"
        layers["stairs"].append(wedge(axis, lo, hi, f0, f1))

    # --- lights + lamp fixtures. Small rooms: one ceiling light. Big rooms: a 4-cell grid of
    #     pendants hung down to 4.5 m above the floor so the light reaches the deck.
    def light(cx, cz, z, energy, rng_, color="255 230 194", ceiling=None):
        ents.append(f'"classname" "light"\n"origin" "{cx:g} {cz:g} {z:g}"\n"light_color" "{color}"\n"light_energy" "{energy}"\n"omni_range" "{rng_}"')
        layers["lamp"].append(box(cx - 16, cz - 16, z + 12, cx + 16, cz + 16, z + 16, "lamp", "trim"))
        if ceiling is not None and ceiling > z + 16:
            layers["lamp"].append(box(cx - 2, cz - 2, z + 16, cx + 2, cz + 2, ceiling, "rod"))   # pendant rod
    for r in level["rooms"]:
        cs = [tuple(p) for p in r["cells"] if tuple(p) in cells]
        cz = ceil_u(r["floor"], r["ceil"]); fz = r["floor"] * LVL
        hang = min(cz - 20, fz + int(4.5 * U))
        if len(cs) <= 80:
            cx = sum(p[0] for p in cs) / len(cs) + .5; cy = sum(p[1] for p in cs) / len(cs) + .5
            light(cx * CELL, Y(cy), hang, 5.0, 14, "255 230 194", cz)
        else:
            for p in cs:
                if p[0] % 4 == 2 and p[1] % 4 == 2 and cells[p]["t"] != PIT:
                    light((p[0] + .5) * CELL, Y(p[1] + .5), hang, 4.5, 12, "255 230 194", cz)
    for (x, y), c in cells.items():          # pits: dim cyan light low down so the drop reads
        if c["t"] == PIT and x % 3 == 0 and y % 3 == 0:
            ents.append(f'"classname" "light"\n"origin" "{(x + .5) * CELL:g} {Y(y + .5):g} {floor_u(c) + 24:g}"\n"light_color" "90 200 255"\n"light_energy" "2.5"\n"omni_range" "7"')
    def corridor(p): return p in cells and p not in room_of and cells[p]["t"] in (FLOOR, DOOR, LOCKED, STAIRS)
    for (x, y), c in cells.items():
        if not corridor((x, y)) or c["t"] != FLOOR: continue
        ew = corridor((x + 1, y)) or corridor((x - 1, y)); ns = corridor((x, y + 1)) or corridor((x, y - 1))
        hit = (ew and x % 4 == 0 and not corridor((x, y - 1))) or (ns and not ew and y % 4 == 0 and not corridor((x - 1, y)))
        if hit: light((x + .5) * CELL, Y(y + .5), ceil_of(c) - 20, 3.0, 9, "140 230 255")

    # --- doors: one frame + one Door scene per run of door cells, spanning the corridor width.
    #     Opening = run width - 2 posts; the Door scene gets slab_width to match.
    for d in level["doors"]:
        run = [tuple(p) for p in d["cells"]]; c = cells[run[0]]
        fz, cz = floor_u(c), ceil_of(c)
        lint = fz + int(3.3 * U); post = int(.25 * U); n = len(run)
        xs = [p[0] for p in run]; ys = [p[1] for p in run]
        X0, X1 = min(xs) * CELL, (max(xs) + 1) * CELL; Z0, Z1 = Y(max(ys) + 1), Y(min(ys))
        if d["axis"] == "x":     # corridor runs E-W: slab lies across z, thin in x
            xm = X0 + CELL // 2
            layers["doorframe"].append(box(xm - 8, Z0, fz, xm + 8, Z0 + post, lint, "door_frame"))
            layers["doorframe"].append(box(xm - 8, Z1 - post, fz, xm + 8, Z1, lint, "door_frame"))
            layers["doorframe"].append(box(xm - 8, Z0, lint, xm + 8, Z1, cz, "door_frame"))
            ox, oz, angle = xm, (Z0 + Z1) / 2, 0
        else:                    # corridor runs N-S: slab lies across x, thin in z
            zm = Z0 + CELL // 2
            layers["doorframe"].append(box(X0, zm - 8, fz, X0 + post, zm + 8, lint, "door_frame"))
            layers["doorframe"].append(box(X1 - post, zm - 8, fz, X1, zm + 8, lint, "door_frame"))
            layers["doorframe"].append(box(X0, zm - 8, lint, X1, zm + 8, cz, "door_frame"))
            ox, oz, angle = (X0 + X1) / 2, zm, 90
        width_m = (n * CELL - 2 * post) / U
        ents.append(f'"classname" "prop_door"\n"origin" "{ox:g} {oz:g} {fz:g}"\n"angle" "{angle}"\n"lock" "{"jammed" if d["locked"] else "none"}"\n"slab_width" "{width_m:g}"\n"texture" "{THEME["door"]}"')

    # --- player start: the floor cell nearest room 1's centre, at that cell's own floor height
    r1 = level["rooms"][1]; cs = [tuple(p) for p in r1["cells"] if tuple(p) in cells and cells[tuple(p)]["t"] == FLOOR]
    mx = sum(p[0] for p in cs) / len(cs) + .5; my = sum(p[1] for p in cs) / len(cs) + .5
    sc = min(cs, key=lambda p: abs(p[0] + .5 - mx) + abs(p[1] + .5 - my))
    cx, cy = sc[0] + .5, sc[1] + .5
    hub = level["rooms"][0]; hcs = [tuple(p) for p in hub["cells"] if tuple(p) in cells]
    hx = sum(p[0] for p in hcs) / len(hcs) + .5; hy = sum(p[1] for p in hcs) / len(hcs) + .5
    ang = math.degrees(math.atan2(Y(hy) - Y(cy), (hx - cx) * CELL))
    ents.append(f'"classname" "info_player_start"\n"origin" "{cx * CELL:g} {Y(cy):g} {floor_u(cells[sc]) + 4:g}"\n"angle" "{ang:.0f}"')

    # --- enemies, pickups, exit: rooms are rooms to fight in. Skitters scale with room size,
    #     a Drifter in each big room, health/cells in rooms far from the start, exit farthest of all.
    def bfs_rooms(start_room):
        """room index -> hop distance over corridor cells (rough: BFS on the cell grid, mark rooms)."""
        from collections import deque
        dist = {}; q = deque(); seen = set()
        for p in level["rooms"][start_room]["cells"]:
            if tuple(p) in cells: q.append((tuple(p), 0)); seen.add(tuple(p))
        while q:
            p, dd = q.popleft()
            r = room_of.get(p)
            if r is not None and r not in dist: dist[r] = dd
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + dx, p[1] + dy)
                if n in cells and n not in seen and cells[n]["t"] != PIT:
                    seen.add(n); q.append((n, dd + 1))
        return dist
    hops = bfs_rooms(1)
    far = sorted(hops, key=lambda r: -hops[r])
    def spot(name, p, extra=""):
        c = cells[p]; ents.append(f'"classname" "{name}"\n"origin" "{(p[0] + .5) * CELL:g} {Y(p[1] + .5):g} {floor_u(c) + 8:g}"{extra}')
    for i, r in enumerate(level["rooms"]):
        if i == 1: continue
        rc = [tuple(p) for p in r["cells"] if tuple(p) in cells and cells[tuple(p)]["t"] == FLOOR]
        if not rc: continue
        rc.sort(key=lambda p: hash01(p[0] * 7 + i, p[1] * 13))
        n_sk = min(4, 1 + len(rc) // 40)
        for p in rc[:n_sk]: spot("monster_skitter", p)
        if len(rc) > 80: spot("monster_drifter", rc[n_sk])
        if hops.get(i, 0) > 12 and hash01(i, 99) < .5: spot("item_health", rc[-1])
        if hash01(i, 7) < .35: spot("item_cells", rc[-2])
    # corridor skitters: one every ~12 corridor cells, deterministic
    corr = sorted(p for p in cells if p not in room_of and cells[p]["t"] == FLOOR)
    for p in corr:
        if hash01(p[0] * 3, p[1] * 5) < 1 / 12: spot("monster_skitter", p)
    if far:
        ex = level["rooms"][far[0]]; ec = [tuple(p) for p in ex["cells"] if tuple(p) in cells and cells[tuple(p)]["t"] == FLOOR]
        mx = sum(p[0] for p in ec) / len(ec); my = sum(p[1] for p in ec) / len(ec)
        spot("trigger_exit", min(ec, key=lambda p: abs(p[0] + .5 - mx) + abs(p[1] + .5 - my)))

    # screenshot markers: stand at the edge of a room, look at its centre
    def shot(name, r):
        rc = [tuple(p) for p in r["cells"] if tuple(p) in cells and cells[tuple(p)]["t"] in (FLOOR, CATWALK)
              and all((p[0] + dx, p[1] + dy) in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]   # interior cells only
        if not rc: return
        mx = sum(p[0] for p in rc) / len(rc) + .5; my = sum(p[1] for p in rc) / len(rc) + .5
        sx, sy = max(rc, key=lambda p: abs(p[0] + .5 - mx) + abs(p[1] + .5 - my))      # farthest floor cell
        sx += .5; sy += .5
        ang = math.degrees(math.atan2(Y(my) - Y(sy), (mx - sx) * CELL))
        sf = cells[(int(sx), int(sy))]["f"]
        ents.append(f'"classname" "shot"\n"origin" "{sx * CELL:g} {Y(sy):g} {sf * LVL + int(1.6 * U):g}"\n"angle" "{ang:.0f}"\n"shot_name" "{name}"')
    shot("hub", hub)
    # a corridor shot: the longest straight corridor run, looking down it
    best = None
    for (x, y), c in cells.items():
        if not corridor((x, y)): continue
        k = 0
        while corridor((x + k + 1, y)): k += 1
        if best is None or k > best[0]: best = (k, x, y)
    if best and best[0] >= 3:
        k, x, y = best; c = cells[(x, y)]
        ents.append(f'"classname" "shot"\n"origin" "{(x + .5) * CELL:g} {Y(y + .5):g} {floor_u(c) + int(1.6 * U):g}"\n"angle" "0"\n"shot_name" "corridor"')
    for i in (1, 2, 5, 8):
        if i < len(level["rooms"]): shot(level["rooms"][i]["name"], level["rooms"][i])
    return layers, ents

CHUNK = 4 * CELL     # 8 m tiles: each becomes its own mesh so the renderer's per-mesh light cap is local

def _chunk_of(brush):
    """(cx, cy) of a brush from its first plane point (min corner-ish)."""
    import re
    pts = [tuple(float(v) for v in m) for m in re.findall(r"\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)", brush)]
    x = min(p[0] for p in pts); y = min(p[1] for p in pts)
    return (int(x // CHUNK), int(y // CHUNK))

def write_map(layers, ents, path, name):
    out = ["// Game: Conamara", "// Format: Valve", "{", '"classname" "worldspawn"', '"mapversion" "220"', f'"message" "{name}"', "}"]
    lid = 0
    for lname, brushes in layers.items():
        if not brushes: continue
        lid += 1
        out += ["{", '"classname" "func_group"', '"_tb_type" "_tb_layer"', f'"_tb_name" "{lname}"', f'"_tb_id" "{lid}"', "}"]
        chunks = {}
        for b in brushes: chunks.setdefault(_chunk_of(b), []).append(b)
        for (cx, cy), bs in sorted(chunks.items()):
            out += ["{", '"classname" "func_detail"', f'"_tb_layer" "{lid}"', f'"_chunk" "{lname}_{cx}_{cy}"']
            out += bs; out.append("}")
    for props in ents:
        out += ["{", props, "}"]
    open(path, "w").write("\n".join(out) + "\n")
    return sum(len(b) for b in layers.values())

if __name__ == "__main__":
    src = sys.argv[1]
    if len(sys.argv) > 2: THEME = THEMES[sys.argv[2]]
    level = json.load(open(src))
    name = os.path.splitext(os.path.basename(src))[0]
    layers, ents = build(level)
    dst = os.path.join(os.path.dirname(src), name + ".map")
    n = write_map(layers, ents, dst, name)
    print(f"{n} brushes in {sum(1 for v in layers.values() if v)} layers, {len(ents)} entities -> {dst}")
