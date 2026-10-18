"""Procedural tileable texture atlas for the Collider kit.

Every tile is 64x64 (2m of world = 32px/m), seamless, and quantised to a
fixed palette with ordered dithering so the whole game shares one look.
Outputs:
  art/textures/kit_albedo.png    colour atlas
  art/textures/kit_emission.png  emission atlas (black = no glow)
  art/textures/tiles.json        tile name -> atlas index
Run: python3 tools/gen_textures.py
"""
import json, os
import numpy as np
from PIL import Image

T = 64            # tile size
PAD = 8           # wrap padding around each tile (stops bleeding)
CELL = T + PAD * 2
COLS = 8
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "textures")
rng = np.random.default_rng(7)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


# ---- palette: ramps run dark -> light -------------------------------------
RAMPS = {
    "steel":    ["#131518", "#1b1e22", "#24282d", "#2e3339", "#3a4047", "#4a5058", "#5f666e", "#7d848c", "#a2a8ae"],
    "concrete": ["#242220", "#302d2a", "#3d3935", "#4b4641", "#5a544e", "#6b645c", "#7e766d", "#948b81"],
    "hazard":   ["#1e1a16", "#2b241c", "#8a6512", "#b8861a", "#dca52a", "#f2c84b"],
    "cyan":     ["#06141a", "#0b2a33", "#0f4a5c", "#167e96", "#22b3cf", "#6fe6fb", "#d6fbff"],
    "orange":   ["#2a1610", "#4a2213", "#7a3618", "#a8491d", "#d0632a", "#f08b45"],
    "red":      ["#1c0b0b", "#3d1212", "#6e1a1a", "#a32424", "#e04040", "#ff8a7a"],
    "olive":    ["#191c14", "#252a1c", "#343b26", "#465032", "#5b663f", "#727f4f"],
}
RAMPS = {k: np.stack([hexc(c) for c in v]) for k, v in RAMPS.items()}

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 - 0.47
DITHER = np.tile(BAYER, (T // 4, T // 4))

Y, X = np.mgrid[0:T, 0:T].astype(np.float32)


def quant(shade, ramp, dither=0.55):
    """shade 0..1 -> palette colours with ordered dither."""
    r = RAMPS[ramp]
    n = len(r)
    v = np.clip(shade, 0, 1) * (n - 1) + DITHER * dither
    idx = np.clip(np.round(v), 0, n - 1).astype(int)
    return r[idx]


def vnoise(cells, seed=None, octaves=1):
    """Periodic value noise (seamless over the tile)."""
    g = np.random.default_rng(seed if seed is not None else rng.integers(1 << 30))
    out = np.zeros((T, T), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        grid = g.random((c, c)).astype(np.float32)
        fx = X / T * c
        fy = Y / T * c
        x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int)
        tx = fx - x0; ty = fy - y0
        tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty)
        x1 = (x0 + 1) % c; y1 = (y0 + 1) % c
        x0 %= c; y0 %= c
        a = grid[y0, x0] * (1 - tx) + grid[y0, x1] * tx
        b = grid[y1, x0] * (1 - tx) + grid[y1, x1] * tx
        out += (a * (1 - ty) + b * ty) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def bevel(shade, x0, y0, x1, y1, hi=0.18, lo=0.22, w=1):
    """Raise a rectangle: lit top/left edge, shadowed bottom/right edge."""
    s = shade.copy()
    s[y0:y0 + w, x0:x1] += hi
    s[y0:y1, x0:x0 + w] += hi
    s[y1 - w:y1, x0:x1] -= lo
    s[y0:y1, x1 - w:x1] -= lo
    return s


def seam(shade, x0, y0, x1, y1, d=0.3):
    """Recessed groove outline around a rectangle (1px dark + 1px light)."""
    s = shade.copy()
    s[y0, x0:x1] -= d; s[y0:y1, x0] -= d
    s[min(y0 + 1, T - 1), x0:x1] -= d * 0.4
    s[y1 - 1, x0:x1] += d * 0.35; s[y0:y1, x1 - 1] += d * 0.35
    return s


def bolt(shade, x, y):
    s = shade
    s[y % T, x % T] += 0.35
    s[(y + 1) % T, (x + 1) % T] -= 0.3
    s[y % T, (x + 1) % T] += 0.1
    return s


def grime(shade, amount=0.15, bottom=True):
    n = vnoise(4, octaves=3)
    s = shade - (n - 0.5) * amount * 2
    if bottom:
        s -= np.clip((Y - 44) / 20.0, 0, 1) * amount * 1.2 * (0.5 + n)
    return s


tiles = {}       # name -> (rgb array, emission rgb array)
NOEMIT = np.zeros((T, T, 3), np.float32)


def add(name, rgb, emit=None):
    tiles[name] = (rgb, NOEMIT if emit is None else emit)


# ---------------------------------------------------------------- floors ----
def floor_concrete():
    # ship deck: four 1m plates, bevelled edges, corner fasteners, grip dots
    s = 0.5 + (vnoise(8, octaves=3) - 0.5) * 0.12
    for (x, y) in [(0, 0), (32, 0), (0, 32), (32, 32)]:
        s = bevel(s, x, y, x + 32, y + 32, 0.14, 0.24, 1)
        s[y + 31, x:x + 32] -= 0.12; s[y:y + 32, x + 31] -= 0.12
        for (bx, by) in [(x + 3, y + 3), (x + 27, y + 3), (x + 3, y + 27), (x + 27, y + 27)]:
            bolt(s, bx, by)
    grip = ((X % 4) == 2) & ((Y % 4) == 2) & ((X % 32) > 7) & ((X % 32) < 25) & ((Y % 32) > 7) & ((Y % 32) < 25)
    s[grip] -= 0.14
    s = grime(s, 0.05, bottom=False)
    return quant(s, "concrete")


def floor_metal():
    s = np.full((T, T), 0.42) + (vnoise(4, octaves=2) - 0.5) * 0.15
    # diamond tread: small raised dashes alternating direction
    for gy in range(0, T, 8):
        for gx in range(0, T, 8):
            ox = gx + (4 if (gy // 8) % 2 else 0)
            if ((gx // 8) + (gy // 8)) % 2:
                for k in range(3):
                    s[(gy + 2 + k) % T, (ox + 1 + k) % T] += 0.22
                    s[(gy + 3 + k) % T, (ox + 1 + k) % T] -= 0.15
            else:
                for k in range(3):
                    s[(gy + 4 - k) % T, (ox + 1 + k) % T] += 0.22
                    s[(gy + 5 - k) % T, (ox + 1 + k) % T] -= 0.15
    s = seam(s, 0, 0, T, T, 0.3)
    for p in [(3, 3), (60, 3), (3, 60), (60, 60), (31, 3), (31, 60)]:
        bolt(s, *p)
    return quant(grime(s, 0.08, False), "steel")


def floor_grate():
    s = np.full((T, T), 0.55)
    holes = ((X % 8) >= 2) & ((Y % 8) >= 2)
    s[holes] = 0.05
    s[((X % 8) == 1) & ~holes] -= 0.2
    s[((Y % 8) == 1) & ~holes] -= 0.2
    s = seam(s, 0, 0, T, T, 0.3)
    rgb = quant(s, "steel")
    # glow showing through the holes
    glow = vnoise(4, octaves=2)
    em = np.zeros((T, T, 3), np.float32)
    hole_col = quant(0.12 + glow * 0.3, "cyan")
    rgb[holes] = hole_col[holes]
    em[holes] = hole_col[holes] * 0.3
    return rgb, em


def ceiling():
    s = 0.42 + (vnoise(8, octaves=2) - 0.5) * 0.08
    s = bevel(s, 0, 0, T, T, 0.12, 0.25, 2)
    s = seam(s, 8, 8, 56, 56, 0.14)
    s[30:34, 8:56] -= 0.1                          # centre service seam
    for (x, y) in [(4, 4), (59, 4), (4, 59), (59, 59)]:
        bolt(s, x, y)
    return quant(s, "steel")


# ----------------------------------------------------------------- walls ----
def wall_lower():
    # lower hull panel: slotted kick vents, heavy bottom plate
    s = 0.40 + (vnoise(4, octaves=3) - 0.5) * 0.08
    s = bevel(s, 0, 0, T, 48, 0.12, 0.2, 1)
    s = seam(s, 6, 6, 58, 42, 0.12)
    for x in range(10, 56, 6):                     # vent slots
        s[30:38, x:x + 3] = 0.08
        s[38, x:x + 3] += 0.15
    s[48:, :] = 0.2 + vnoise(16)[48:, :] * 0.05
    s[48, :] += 0.2
    for x in (3, 60):
        bolt(s, x, 3); bolt(s, x, 44)
    s = grime(s, 0.08, True)
    return quant(s, "steel")


def wall_upper():
    # upper hull panel: tall inset, orange accent stripe that runs ship-wide
    s = 0.54 + (vnoise(4, octaves=3) - 0.5) * 0.08
    s = bevel(s, 0, 0, T, T, 0.08, 0.16, 1)
    s = seam(s, 5, 14, 59, 50, 0.10)
    s = bevel(s, 7, 16, 57, 48, 0.06, 0.08, 1)
    s[56:64, :] = 0.30
    s[56, :] += 0.25; s[63, :] -= 0.15             # rail
    for x in (2, 61):
        bolt(s, x, 7); bolt(s, x, 52)
    rgb = quant(grime(s, 0.04, False), "steel")
    stripe = (Y >= 59) & (Y < 62)
    rgb[stripe] = quant(np.full((T, T), 0.85), "orange", 0.3)[stripe]
    return rgb


def beam():
    s = np.full((T, T), 0.34) + (vnoise(4, octaves=2) - 0.5) * 0.08
    s[0:3, :] += 0.2; s[61:, :] -= 0.15        # flanges
    s[6, :] -= 0.15; s[57, :] += 0.1
    for x in range(4, T, 8):
        bolt(s, x, 3); bolt(s, x, 59)
    return quant(s, "steel")


def wall_concrete():
    # bulkhead: heavy vertical ribs
    s = 0.36 + (vnoise(4, octaves=3) - 0.5) * 0.08
    for x0 in (0, 32):
        s[:, x0:x0 + 8] += 0.14
        s[:, x0] += 0.15; s[:, x0 + 7] -= 0.25
        s[:, x0 + 8] -= 0.15
        for y in range(4, T, 16):
            bolt(s, x0 + 3, y)
    s[:, 16:24] -= 0.05; s[:, 48:56] -= 0.05
    s = grime(s, 0.08, True)
    return quant(s, "steel")


def hazard():
    band = ((X + Y) % 16) < 8
    s = np.where(band, 0.82, 0.08) + (vnoise(8, octaves=2) - 0.5) * 0.18
    s = grime(s, 0.12, False)
    rgb = quant(s, "hazard")
    return rgb


def trim():
    s = 0.5 + (vnoise(2, octaves=1) - 0.5) * 0.1
    streak = np.random.default_rng(3).random(T).astype(np.float32)
    s += (streak[None, :] * 0 + streak[:, None] - 0.5) * 0.12  # horizontal brush
    s[0, :] += 0.2; s[T - 1, :] -= 0.25
    return quant(s, "steel")


def recess_back():
    s = np.full((T, T), 0.22) + (vnoise(4, octaves=2) - 0.5) * 0.1
    for x in range(0, T, 8):
        s[:, x] += 0.14
        s[:, (x + 1) % T] += 0.05
        s[:, (x + 6) % T] -= 0.06
        s[:, (x + 7) % T] -= 0.1
    return quant(grime(s, 0.08, True), "steel")


def light_strip():
    s = np.full((T, T), 0.25) + (vnoise(4)) * 0.05
    s = bevel(s, 0, 20, T, 44, 0.2, 0.3)
    rgb = quant(s, "steel")
    em = np.zeros((T, T, 3), np.float32)
    lit = (Y >= 24) & (Y < 40)
    core = 0.7 + 0.3 * (1 - np.abs(Y - 31.5) / 8.0)
    glow = quant(core, "cyan", dither=0.6)
    rgb[lit] = glow[lit]
    em[lit] = glow[lit]
    # housing dividers every 16px
    div = lit & ((X % 16) == 0)
    rgb[div] = RAMPS["steel"][2]; em[div] = 0
    return rgb, em


def vent():
    s = np.full((T, T), 0.35)
    s = bevel(s, 0, 0, T, T, 0.18, 0.25, 2)
    for y in range(6, 58, 6):
        s[y:y + 3, 4:60] = 0.08
        s[y + 3, 4:60] += 0.18
    return quant(s, "steel")


def pipe():
    # u runs around the pipe circumference; shade like a cylinder
    c = np.cos((X / T - 0.35) * np.pi * 2) * 0.5 + 0.5
    s = 0.2 + c * 0.55
    band = (Y % 32) < 4
    rgb = quant(s, "steel")
    rgb[band] = quant(s * 0.9 + 0.1, "orange")[band]
    return rgb


def crate():
    s = 0.45 + (vnoise(4, octaves=2) - 0.5) * 0.15
    s = bevel(s, 0, 0, T, T, 0.2, 0.3, 3)
    for k in range(T - 12):
        a = 6 + k
        s[a, a] += 0.25; s[a, (a + 1) % T] -= 0.2
        s[a, T - 1 - a] += 0.25; s[a, (T - 2 - a) % T] -= 0.2
    rgb = quant(grime(s, 0.1, True), "olive")
    # stencil block
    rgb[8:14, 40:56] = RAMPS["hazard"][4]
    return rgb


def door():
    s = 0.42 + (vnoise(4, octaves=2) - 0.5) * 0.12
    s = bevel(s, 0, 0, 32, T, 0.15, 0.25, 2)
    s = bevel(s, 32, 0, T, T, 0.15, 0.25, 2)
    for x in (6, 26, 38, 58):
        bolt(s, x, 6); bolt(s, x, 57)
    rgb = quant(s, "steel")
    chev = (((np.abs(X - 31.5) + Y) % 16) < 8) & (Y >= 26) & (Y < 38)
    rgb[chev] = RAMPS["hazard"][4]
    em = np.zeros((T, T, 3), np.float32)
    # small status lamp
    rgb[4:8, 29:35] = RAMPS["cyan"][5]; em[4:8, 29:35] = RAMPS["cyan"][5]
    return rgb, em


def console():
    s = np.full((T, T), 0.22)
    s = bevel(s, 0, 0, T, T, 0.18, 0.25, 2)
    s = bevel(s, 6, 6, 58, 38, -0.1, -0.1, 2)
    rgb = quant(s, "steel")
    em = np.zeros((T, T, 3), np.float32)
    scr = np.zeros((T, T), bool); scr[8:36, 8:56] = True
    base = quant(np.full((T, T), 0.22), "cyan", 0)
    rgb[scr] = base[scr]; em[scr] = base[scr] * 0.6
    g = np.random.default_rng(11)
    for row in range(11, 34, 4):
        n = g.integers(10, 44)
        rgb[row, 11:11 + n] = RAMPS["cyan"][5]; em[row, 11:11 + n] = RAMPS["cyan"][5]
    # buttons
    for i, col in enumerate(["red", "hazard", "cyan", "orange"]):
        x = 10 + i * 12
        rgb[46:52, x:x + 6] = RAMPS[col][4]; em[46:52, x:x + 6] = RAMPS[col][4] * 0.8
    return rgb, em


def warning_lamp():
    s = 0.3 + (vnoise(4) - 0.5) * 0.1
    s = bevel(s, 0, 0, T, T, 0.15, 0.25, 2)
    rgb = quant(s, "steel")
    em = np.zeros((T, T, 3), np.float32)
    d = np.sqrt((X - 31.5) ** 2 + (Y - 31.5) ** 2)
    lamp = d < 14
    col = quant(1 - d / 16, "red", 0.7)
    rgb[lamp] = col[lamp]; em[lamp] = col[lamp]
    ring = (d >= 14) & (d < 17)
    rgb[ring] = RAMPS["steel"][6]
    return rgb, em


def floor_line():
    rgb = floor_concrete()
    paint = quant(0.75 + (vnoise(8) - 0.5) * 0.3, "hazard")
    m = (Y >= 2) & (Y < 8)
    rgb[m] = paint[m]
    return rgb


def wall_cables():
    s = 0.40 + (vnoise(4, octaves=3) - 0.5) * 0.12
    rgb = quant(s, "steel")
    for i, (yc, ramp) in enumerate([(22, "steel"), (30, "orange"), (38, "steel"), (45, "cyan")]):
        for yy in range(yc - 3, yc + 3):
            t = 1 - abs(yy - yc + 0.5) / 3.5
            row = quant(np.full((1, T), 0.15 + t * 0.5), ramp if ramp != "cyan" else "cyan", 0)[0]
            rgb[yy, :] = row
    # brackets
    for x in range(8, T, 32):
        rgb[16:52, x:x + 3] = RAMPS["steel"][5]
        rgb[16:52, x + 3] = RAMPS["steel"][1]
    return rgb


def rust_plate():
    s = 0.45 + (vnoise(4, octaves=4) - 0.5) * 0.3
    s = bevel(s, 0, 0, T, T, 0.12, 0.2, 1)
    rgb = quant(s, "steel")
    r = vnoise(8, octaves=3)
    m = r > 0.62
    rgb[m] = quant(s * 0.8, "orange")[m]
    return rgb



def chamfer():
    # angled wall/ceiling panel; u runs along the wall, v up the slope.
    # thin cyan strip near the ceiling edge = ship-wide ambient lighting
    s = 0.46 + (vnoise(4, octaves=2) - 0.5) * 0.08
    for x0 in (0, 32):
        s = bevel(s, x0, 0, x0 + 32, T, 0.1, 0.2, 1)
    s[6:8, :] -= 0.12     # shadow line near the ceiling edge
    return quant(s, "steel")


def kick():
    s = 0.24 + (vnoise(4) - 0.5) * 0.06
    s = bevel(s, 0, 0, T, T, 0.12, 0.2, 1)
    for x in (4, 59):
        bolt(s, x, 40)
    return quant(s, "steel")


def window():
    g = np.random.default_rng(21)
    neb = vnoise(4, octaves=4)
    s = 0.05 + neb * 0.25
    rgb = quant(s, "cyan", 0.4) * 0.55 + quant(vnoise(2, octaves=3) * 0.5, "red", 0.4) * 0.25
    em = rgb.copy() * 0.6
    for _ in range(70):
        x, y = g.integers(0, T, 2)
        b = g.random()
        c = np.array([200, 220, 255]) * (0.5 + b * 0.5)
        rgb[y, x] = c; em[y, x] = c
        if b > 0.9:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rgb[(y + dy) % T, (x + dx) % T] = c * 0.5; em[(y + dy) % T, (x + dx) % T] = c * 0.5
    return rgb, em



def gutter():
    # dark service grating that runs along the foot of every wall
    s = np.full((T, T), 0.30) + (vnoise(4, octaves=2) - 0.5) * 0.06
    slots = ((X % 6) >= 2) & ((Y % 16) >= 2) & ((Y % 16) < 14)
    s[slots] = 0.02
    s[((X % 6) == 1) & slots.any(axis=0)[None, :].repeat(T, 0)] += 0.0
    s[(Y % 16) == 1] += 0.12
    s[(Y % 16) == 14] -= 0.1
    return quant(s, "steel")



def gutter_glow():
    rgb = gutter()
    em = np.zeros((T, T, 3), np.float32)
    slots = ((X % 6) >= 2) & ((Y % 16) >= 4) & ((Y % 16) < 12) & ((Y // 16) % 2 == 0)
    col = quant(np.full((T, T), 0.55), "cyan", 0)
    rgb[slots] = col[slots]; em[slots] = col[slots] * 0.5
    return rgb, em


# ---- register (order = atlas index; keep stable once levels exist) --------
add("floor_concrete", floor_concrete())
add("floor_metal", floor_metal())
add("floor_grate", *floor_grate())
add("ceiling", ceiling())
add("wall_lower", wall_lower())
add("wall_upper", wall_upper())
add("wall_concrete", wall_concrete())
add("hazard", hazard())
add("trim", trim())
add("recess_back", recess_back())
add("light_strip", *light_strip())
add("vent", vent())
add("pipe", pipe())
add("crate", crate())
add("door", *door())
add("console", *console())
add("warning_lamp", *warning_lamp())
add("floor_line", floor_line())
add("wall_cables", wall_cables())
add("rust_plate", rust_plate())
add("beam", beam())
add("chamfer", chamfer())
add("kick", kick())
add("gutter", gutter())
add("gutter_glow", *gutter_glow())
add("window", *window())

rows = (len(tiles) + COLS - 1) // COLS
rows = max(rows, 4)
W, H = COLS * CELL, rows * CELL
albedo = np.zeros((H, W, 3), np.uint8)
emis = np.zeros((H, W, 3), np.uint8)
index = {}
for i, (name, (rgb, em)) in enumerate(tiles.items()):
    cx, cy = (i % COLS) * CELL, (i // COLS) * CELL
    # wrap-pad so filtering / mips never pull in a neighbour tile
    padded = np.pad(rgb, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="wrap")
    padded_e = np.pad(em, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="wrap")
    albedo[cy:cy + CELL, cx:cx + CELL] = np.clip(padded, 0, 255).astype(np.uint8)
    emis[cy:cy + CELL, cx:cx + CELL] = np.clip(padded_e, 0, 255).astype(np.uint8)
    index[name] = i

os.makedirs(OUT, exist_ok=True)
Image.fromarray(albedo).save(os.path.join(OUT, "kit_albedo.png"))
Image.fromarray(emis).save(os.path.join(OUT, "kit_emission.png"))
meta = {"tile": T, "pad": PAD, "cell": CELL, "cols": COLS, "width": W, "height": H, "tiles": index}
with open(os.path.join(OUT, "tiles.json"), "w") as f:
    json.dump(meta, f, indent=1)

# preview sheet (unpadded, 3x, labelled) for review
prev = Image.new("RGB", (COLS * (T * 3 + 4), rows * (T * 3 + 4)), (10, 10, 10))
for i, (name, (rgb, em)) in enumerate(tiles.items()):
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((T * 3, T * 3), Image.NEAREST)
    prev.paste(im, ((i % COLS) * (T * 3 + 4), (i // COLS) * (T * 3 + 4)))
prev.save(os.path.join(ROOT, "shots", "tiles_preview.png"))
print("tiles:", len(tiles), "atlas", W, "x", H)
