"""
Doom/Quake-flavoured top-down layout generator. The layout is the clay; tools/export_map.py
dresses it into a TrenchBroom .map (brushes + entities) for FuncGodot.

Outputs:
  level_automap.png  - Doom automap-style render (visual reference)
  level_data.png     - 1 px = 1 cell. R = floor level (0-7 -> 0..224),
                       G = ceiling level, B = type (0 void,1 floor,2 door,
                       3 locked door,4 stairs,5 lift,6 pit/low,7 catwalk)
  level.json         - cells + rooms + doors for Godot import

Usage: python3 tools/mapgen.py <seed> [w] [h] [outdir]   (default outdir levels)
"""
import json, math, random, sys
from PIL import Image, ImageDraw

VOID, FLOOR, DOOR, LOCKED, STAIRS, LIFT, PIT, CATWALK = range(8)

def chamfered(x0, y0, x1, y1, c):
    """Octagon via chamfered rectangle - the Doom/Quake room shape."""
    cells = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = min(x - x0, x1 - 1 - x)
            dy = min(y - y0, y1 - 1 - y)
            if dx + dy >= c:
                cells.add((x, y))
    return cells

def lshape(x0, y0, x1, y1, rng):
    cells = {(x, y) for y in range(y0, y1) for x in range(x0, x1)}
    w, h = x1 - x0, y1 - y0
    cw, ch = w // 2, h // 2
    corner = rng.choice([(x0, y0), (x1 - cw, y0), (x0, y1 - ch), (x1 - cw, y1 - ch)])
    for y in range(corner[1], corner[1] + ch):
        for x in range(corner[0], corner[0] + cw):
            cells.discard((x, y))
    return cells

class Gen:
    def __init__(self, seed, w=72, h=72):
        self.rng = random.Random(seed)
        self.w, self.h = w, h
        self.type = [[VOID] * w for _ in range(h)]
        self.floor = [[0] * w for _ in range(h)]
        self.ceil = [[0] * w for _ in range(h)]
        self.rooms = []
        self.doors = []

    # ---------- rooms ----------
    def free(self, cells, margin=2):
        for (x, y) in cells:
            for dy in range(-margin, margin + 1):
                for dx in range(-margin, margin + 1):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < self.w and 0 <= ny < self.h):
                        return False
                    if self.type[ny][nx] != VOID:
                        return False
        return True

    def stamp(self, cells, fl, cl, kind, name):
        for (x, y) in cells:
            self.type[y][x] = kind
            self.floor[y][x] = fl
            self.ceil[y][x] = cl
        cx = sum(x for x, _ in cells) / len(cells)
        cy = sum(y for _, y in cells) / len(cells)
        self.rooms.append(dict(name=name, cells=sorted(cells), floor=fl, ceil=cl,
                               center=(cx, cy)))

    def place_rooms(self):
        rng = self.rng
        # hub: big octagon in the middle with a pit and a catwalk ring
        hw = rng.randint(14, 18)
        x0, y0 = self.w // 2 - hw // 2, self.h // 2 - hw // 2
        hub = chamfered(x0, y0, x0 + hw, y0 + hw, hw // 3)
        self.stamp(hub, 2, 7, FLOOR, "hub")
        inner = chamfered(x0 + 4, y0 + 4, x0 + hw - 4, y0 + hw - 4, hw // 3 - 2)
        for (x, y) in inner:
            self.type[y][x] = PIT; self.floor[y][x] = 0
        # catwalk bridging the pit
        if rng.random() < 0.5:
            for x in range(x0 + 4, x0 + hw - 4):
                y = y0 + hw // 2
                if (x, y) in inner: self.type[y][x] = CATWALK; self.floor[y][x] = 2
        else:
            for y in range(y0 + 4, y0 + hw - 4):
                x = x0 + hw // 2
                if (x, y) in inner: self.type[y][x] = CATWALK; self.floor[y][x] = 2

        target = rng.randint(16, 22)
        tries = 0
        while len(self.rooms) < target and tries < 4000:
            tries += 1
            w = rng.randint(5, 15); h = rng.randint(5, 15)
            x = rng.randint(1, self.w - w - 1); y = rng.randint(1, self.h - h - 1)
            shape = rng.random()
            if shape < 0.45:
                cells = chamfered(x, y, x + w, y + h, rng.randint(1, min(w, h) // 3 + 1))
            elif shape < 0.7 and w > 6 and h > 6:
                cells = lshape(x, y, x + w, y + h, rng)
            else:
                cells = {(cx, cy) for cy in range(y, y + h) for cx in range(x, x + w)}
            if not self.free(cells):
                continue
            fl = rng.choice([0, 1, 1, 2, 2, 3, 4])
            cl = fl + rng.choice([2, 3, 3, 4, 5])
            self.stamp(cells, fl, cl, FLOOR, f"room{len(self.rooms)}")
            # pillars (Doom-style columns) in big rooms
            if len(cells) > 80 and rng.random() < 0.6:
                for px in range(x + 2, x + w - 2, 4):
                    for py in range(y + 2, y + h - 2, 4):
                        if (px, py) in cells and rng.random() < 0.7:
                            self.type[py][px] = VOID; cells.discard((px, py))
            # occasional internal pit / raised platform
            if len(cells) > 50 and rng.random() < 0.5:
                sub = chamfered(x + 2, y + 2, x + w - 2, y + h - 2, 2) & cells
                if rng.random() < 0.5:
                    for (sx, sy) in sub: self.type[sy][sx] = PIT; self.floor[sy][sx] = fl - 1
                else:
                    for (sx, sy) in sub: self.floor[sy][sx] = fl + 1

    # ---------- corridors ----------
    def carve_corridor(self, a, b, fl_a, fl_b):
        """L / Z corridor between room centres, with stairs where height changes."""
        rng = self.rng
        (ax, ay), (bx, by) = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
        path = []
        if rng.random() < 0.5:
            mx = rng.randint(min(ax, bx), max(ax, bx))
            path += [(x, ay) for x in range(min(ax, mx), max(ax, mx) + 1)]
            path += [(mx, y) for y in range(min(ay, by), max(ay, by) + 1)]
            path += [(x, by) for x in range(min(mx, bx), max(mx, bx) + 1)]
        else:
            my = rng.randint(min(ay, by), max(ay, by))
            path += [(ax, y) for y in range(min(ay, my), max(ay, my) + 1)]
            path += [(x, my) for x in range(min(ax, bx), max(ax, bx) + 1)]
            path += [(bx, y) for y in range(min(my, by), max(my, by) + 1)]
        # order path from a to b
        ordered, seen = [], set()
        for p in path:
            if p not in seen:
                seen.add(p); ordered.append(p)
        ordered.sort(key=lambda p: abs(p[0] - ax) + abs(p[1] - ay))

        width = rng.choice([1, 2, 2])
        new = []
        for (x, y) in ordered:
            for (nx, ny) in [(x + i, y + j) for i in range(width) for j in range(width)]:
                if 0 <= nx < self.w and 0 <= ny < self.h and self.type[ny][nx] == VOID:
                    new.append((nx, ny))
        if not new:
            return
        # height ramp along corridor
        n = len(new)
        steps = fl_b - fl_a
        for i, (x, y) in enumerate(new):
            t = i / max(1, n - 1)
            lvl = round(fl_a + steps * t)
            self.type[y][x] = FLOOR
            self.floor[y][x] = lvl
            self.ceil[y][x] = lvl + 3
        # mark stair cells where level changes
        prev = None
        for (x, y) in new:
            if prev is not None and self.floor[y][x] != prev:
                self.type[y][x] = STAIRS
            prev = self.floor[y][x]

    def connect(self):
        rng = self.rng
        rooms = self.rooms
        n = len(rooms)
        # MST on room centres
        in_tree = {0}
        edges = []
        while len(in_tree) < n:
            best = None
            for i in in_tree:
                for j in range(n):
                    if j in in_tree: continue
                    d = math.dist(rooms[i]["center"], rooms[j]["center"])
                    if best is None or d < best[0]: best = (d, i, j)
            edges.append((best[1], best[2])); in_tree.add(best[2])
        # loops: a few extra short edges (Doom maps loop back)
        extra = []
        for i in range(n):
            for j in range(i + 1, n):
                if (i, j) in edges or (j, i) in edges: continue
                extra.append((math.dist(rooms[i]["center"], rooms[j]["center"]), i, j))
        extra.sort()
        for _, i, j in extra[: max(2, n // 3)]:
            if rng.random() < 0.7: edges.append((i, j))
        for i, j in edges:
            a, b = rooms[i], rooms[j]
            self.carve_corridor(a["center"], b["center"], a["floor"], b["floor"])
        self.place_doors()

    def place_doors(self):
        """A door is the whole corridor cross-section where a corridor meets a room:
        every corridor cell with a room neighbour becomes DOOR, grouped into runs
        across the corridor; each run is one door (locked by chance)."""
        rng = self.rng
        room_cells = set()
        for r in self.rooms:
            room_cells.update(r["cells"])
        cand = set()
        for y in range(self.h):
            for x in range(self.w):
                if self.type[y][x] not in (FLOOR, STAIRS) or (x, y) in room_cells: continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in room_cells and self.type[ny][nx] == FLOOR:
                        # the corridor must continue away from the room on the other side
                        bx, by = x - dx, y - dy
                        if 0 <= bx < self.w and 0 <= by < self.h and self.type[by][bx] != VOID and (bx, by) not in room_cells:
                            cand.add((x, y, dx, dy))
        # group by (axis, line) into runs of adjacent cells
        seen = set()
        self.doors = []
        for (x, y, dx, dy) in sorted(cand):
            if (x, y) in seen: continue
            run = [(x, y)]
            if dx:   # corridor runs E-W, door spans N-S cells
                for s_ in (1, -1):
                    k = 1
                    while (x, y + s_ * k, dx, dy) in cand: run.append((x, y + s_ * k)); k += 1
            else:
                for s_ in (1, -1):
                    k = 1
                    while (x + s_ * k, y, dx, dy) in cand: run.append((x + s_ * k, y)); k += 1
            if len(run) > 2: continue           # too wide for a door: leave it an open mouth
            locked = rng.random() < 0.15
            for (cx, cy) in run:
                seen.add((cx, cy))
                self.type[cy][cx] = LOCKED if locked else DOOR
            run.sort()
            self.doors.append(dict(cells=run, axis="x" if dx else "y", locked=locked))

    # ---------- output ----------
    def render_automap(self, scale=10):
        img = Image.new("RGB", (self.w * scale, self.h * scale), (8, 8, 8))
        d = ImageDraw.Draw(img)
        floorcol = {0: (34, 30, 44), 1: (58, 50, 70), 2: (84, 74, 92), 3: (112, 100, 110), 4: (142, 128, 130), 5: (172, 156, 150)}
        typecol = {DOOR: (60, 180, 255), LOCKED: (255, 70, 60), STAIRS: (200, 170, 70),
                   LIFT: (255, 210, 40), PIT: (26, 22, 34), CATWALK: (120, 160, 150)}
        for y in range(self.h):
            for x in range(self.w):
                t = self.type[y][x]
                if t == VOID: continue
                c = typecol.get(t, floorcol.get(max(0, min(5, self.floor[y][x])), (150, 136, 140)))
                d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=c)
        # Doom automap lines: wall edges in red/yellow
        for y in range(self.h):
            for x in range(self.w):
                t = self.type[y][x]
                if t == VOID: continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    nt = self.type[ny][nx] if 0 <= nx < self.w and 0 <= ny < self.h else VOID
                    if nt == VOID:
                        col = (255, 60, 60)
                    elif self.floor[ny][nx] != self.floor[y][x]:
                        col = (230, 200, 90)
                    else:
                        continue
                    X, Y = x * scale, y * scale
                    if dx == 1: d.line([X + scale - 1, Y, X + scale - 1, Y + scale - 1], fill=col, width=2)
                    if dx == -1: d.line([X, Y, X, Y + scale - 1], fill=col, width=2)
                    if dy == 1: d.line([X, Y + scale - 1, X + scale - 1, Y + scale - 1], fill=col, width=2)
                    if dy == -1: d.line([X, Y, X + scale - 1, Y], fill=col, width=2)
        return img

    def render_data(self):
        img = Image.new("RGB", (self.w, self.h), (0, 0, 0))
        px = img.load()
        for y in range(self.h):
            for x in range(self.w):
                t = self.type[y][x]
                if t == VOID: continue
                px[x, y] = (max(0, self.floor[y][x] + 1) * 32, max(0, self.ceil[y][x] + 1) * 32, t * 32)
        return img

    def to_json(self):
        cells = []
        for y in range(self.h):
            for x in range(self.w):
                if self.type[y][x] != VOID:
                    cells.append(dict(x=x, y=y, t=self.type[y][x], f=self.floor[y][x], c=self.ceil[y][x]))
        return dict(width=self.w, height=self.h,
                    types=dict(zip(range(8), ["void", "floor", "door", "locked", "stairs", "lift", "pit", "catwalk"])),
                    rooms=[dict(name=r["name"], floor=r["floor"], ceil=r["ceil"], cells=r["cells"]) for r in self.rooms],
                    doors=self.doors, cells=cells)

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1337
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 72
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 72
    g = Gen(seed, w, h)
    g.place_rooms()
    g.connect()
    import os
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "levels", "tb")
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, f"seed{seed}")
    g.render_automap().save(base + "_automap.png")
    json.dump(g.to_json(), open(base + ".json", "w"))
    print(f"seed {seed}: {len(g.rooms)} rooms, {len(g.doors)} doors -> {base}.json")
