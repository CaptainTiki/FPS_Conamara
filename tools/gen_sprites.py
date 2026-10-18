"""Procedural pixel sprite sheets for flat 'anomaly' enemies.

Drifter: a floating violet shard with one glowing eye and trailing tendrils.
Sheet: 8 frames of 64x64 in a row ->
  0,1 idle (bob / tendril sway)   2 attack (eye flare)   3 pain
  4..7 death (shard splits and scatters)
Outputs art/sprites/drifter_albedo.png (RGBA) + drifter_emission.png (RGB).
Run: python3 tools/gen_sprites.py
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "sprites")
S = 64
N = 8

VIOLET = ["#0d0812", "#1c0f27", "#2e1840", "#45245c", "#5e3379", "#7b4797", "#9a62b3"]
GLOW = ["#5c0f4a", "#a3177d", "#e0309f", "#ff7ad0", "#ffd1f0"]
OUTLINE = (8, 4, 12, 255)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


VIOLET = [hexc(c) for c in VIOLET]
GLOW = [hexc(c) for c in GLOW]


def shard_points(cx, cy, scale=1.0, squash=1.0):
    # jagged kite / crystal silhouette, slightly asymmetric
    pts = [(0, -22), (7, -14), (13, -12), (10, -4), (15, 4), (8, 9), (4, 20), (0, 15),
           (-5, 21), (-8, 10), (-15, 5), (-11, -3), (-14, -11), (-7, -13)]
    return [(cx + x * scale / squash, cy + y * scale * squash) for x, y in pts]


def draw_body(img, emi, cx, cy, eye=1.0, flash=False, squash=1.0, cut=None, offset=(0, 0)):
    """Draw the shard into img (RGBA) and emi (RGB). `cut` = (side, angle) keeps half."""
    w = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    e = Image.new("RGB", (S, S), (0, 0, 0))
    d = ImageDraw.Draw(w)
    de = ImageDraw.Draw(e)
    pts = shard_points(cx, cy, 1.0, squash)
    d.polygon(pts, fill=VIOLET[3] + (255,), outline=OUTLINE)
    # facet shading: lit upper-left, dark lower-right
    d.polygon([pts[0], pts[13], pts[12], pts[11], (cx - 2, cy + 2)], fill=VIOLET[4] + (255,))
    d.polygon([pts[0], pts[1], (cx + 1, cy - 4)], fill=VIOLET[5] + (255,))
    d.polygon([pts[4], pts[5], pts[6], pts[7], (cx + 3, cy + 3)], fill=VIOLET[2] + (255,))
    d.polygon([pts[8], pts[9], pts[10], (cx - 2, cy + 6)], fill=VIOLET[2] + (255,))
    # glowing fracture lines
    cracks = [[(cx - 9, cy - 8), (cx - 4, cy - 3), (cx - 6, cy + 4)],
              [(cx + 6, cy - 10), (cx + 4, cy - 6), (cx + 9, cy + 1)],
              [(cx - 2, cy + 8), (cx + 1, cy + 14)]]
    for c in cracks:
        d.line(c, fill=GLOW[2] + (255,), width=1)
        de.line(c, fill=GLOW[2], width=1)
    # eye
    if eye > 0:
        r = 5 * eye
        box = [cx - r - 1, cy - 6 - r * 0.7, cx + r + 1, cy - 6 + r * 0.7]
        d.ellipse(box, fill=GLOW[3] + (255,), outline=OUTLINE)
        de.ellipse(box, fill=GLOW[3])
        inner = [cx - r * 0.5, cy - 6 - r * 0.4, cx + r * 0.5, cy - 6 + r * 0.4]
        d.ellipse(inner, fill=GLOW[4] + (255,))
        de.ellipse(inner, fill=GLOW[4])
        d.rectangle([cx - 1, cy - 7, cx, cy - 5], fill=OUTLINE)
        de.rectangle([cx - 1, cy - 7, cx, cy - 5], fill=(0, 0, 0))
    if cut is not None:
        side, k = cut
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        # diagonal split line through centre
        if side < 0:
            md.polygon([(0, 0), (cx + k, 0), (cx - k, S), (0, S)], fill=255)
        else:
            md.polygon([(cx + k, 0), (S, 0), (S, S), (cx - k, S)], fill=255)
        w.putalpha(Image.fromarray(np.minimum(np.array(w.split()[3]), np.array(mask))))
        e = Image.fromarray((np.array(e) * (np.array(mask)[..., None] / 255)).astype(np.uint8))
    if flash:
        a = np.array(w)
        m = a[..., 3] > 0
        a[m, :3] = (a[m, :3] * 0.3 + np.array([255, 235, 250]) * 0.7).astype(np.uint8)
        w = Image.fromarray(a)
    img.alpha_composite(w, dest=offset)
    emi.paste(e, offset, mask=Image.fromarray((np.array(e).sum(-1) > 0).astype(np.uint8) * 255))


def tendrils(img, emi, cx, cy, phase):
    d = ImageDraw.Draw(img)
    de = ImageDraw.Draw(emi)
    for i, x0 in enumerate((-5, 0, 5)):
        pts = []
        for k in range(7):
            y = cy + 16 + k * 3
            x = cx + x0 + math.sin(phase + k * 0.9 + i * 1.7) * (1 + k * 0.5)
            pts.append((x, y))
        d.line(pts, fill=VIOLET[4] + (255,), width=1)
        tip = pts[-1]
        d.point(tip, fill=GLOW[3] + (255,))
        de.point(tip, fill=GLOW[3])


def frame(i):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    emi = Image.new("RGB", (S, S), (0, 0, 0))
    cx, cy = 32, 26
    if i in (0, 1):
        bob = 0 if i == 0 else 1
        tendrils(img, emi, cx, cy + bob, i * 1.6)
        draw_body(img, emi, cx, cy + bob)
    elif i == 2:   # attack: eye blown wide, body stretched
        tendrils(img, emi, cx, cy, 0.8)
        draw_body(img, emi, cx, cy, eye=1.6, squash=1.08)
    elif i == 3:   # pain: squashed + flash
        tendrils(img, emi, cx, cy + 2, 2.5)
        draw_body(img, emi, cx, cy + 2, eye=0.6, flash=True, squash=0.88)
    else:          # death: split halves drift apart, fade, shed shards
        t = (i - 4) / 3.0
        sep = int(2 + t * 10)
        drop = int(t * 10)
        draw_body(img, emi, cx, cy, eye=max(0, 1 - t * 1.5), cut=(-1, 3), offset=(-sep, drop))
        draw_body(img, emi, cx, cy, eye=0, cut=(1, 3), offset=(sep, drop + 2))
        g = np.random.default_rng(i)
        d = ImageDraw.Draw(img)
        de = ImageDraw.Draw(emi)
        for _ in range(int(6 + t * 14)):
            a = g.random() * math.tau
            r = 6 + t * 26 * g.random()
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8 + t * 6
            c = GLOW[g.integers(1, 4)]
            d.rectangle([x, y, x + 1, y + 1], fill=c + (255,))
            de.rectangle([x, y, x + 1, y + 1], fill=c)
        if i == 7:   # last frame mostly gone
            a = np.array(img)
            a[..., 3] = (a[..., 3] * (g.random((S, S)) > 0.55)).astype(np.uint8)
            img = Image.fromarray(a)
            em = np.array(emi) * (np.array(img)[..., 3:] > 0)
            emi = Image.fromarray(em.astype(np.uint8))
    return img, emi


os.makedirs(OUT, exist_ok=True)
sheet = Image.new("RGBA", (S * N, S), (0, 0, 0, 0))
esheet = Image.new("RGB", (S * N, S), (0, 0, 0))
for i in range(N):
    f, e = frame(i)
    sheet.alpha_composite(f, dest=(i * S, 0))
    esheet.paste(e, (i * S, 0))
sheet.save(os.path.join(OUT, "drifter_albedo.png"))
esheet.save(os.path.join(OUT, "drifter_emission.png"))
prev = Image.new("RGBA", (S * N, S), (40, 44, 52, 255))
prev.alpha_composite(sheet)
prev.resize((S * N * 3, S * 3), Image.NEAREST).save(os.path.join(ROOT, "shots", "drifter_sheet.png"))
print("drifter sheet saved")


# ======================================================================= SKITTER

AMBER = [hexc(c) for c in ["#4a1d06", "#8a3a0a", "#d06a12", "#ffa53a", "#ffe0a8"]]


def skitter_body(img, emi, cx, cy, phase, eye=1.0, flash=False, lunge=0.0, cut=None, off=(0, 0)):
    w = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    e = Image.new("RGB", (S, S), (0, 0, 0))
    d = ImageDraw.Draw(w)
    de = ImageDraw.Draw(e)
    # legs: three per side, jointed, scuttling
    for side in (-1, 1):
        for k in range(3):
            a = phase + k * 2.1 + (0 if side < 0 else 1.05)
            hip = (cx + side * (6 + k * 3), cy + 2)
            knee = (cx + side * (14 + k * 4), cy - 6 + math.sin(a) * 3)
            foot = (cx + side * (18 + k * 4) + math.cos(a) * 2, cy + 12)
            d.line([hip, knee, foot], fill=VIOLET[1] + (255,), width=2)
            d.line([hip, knee, foot], fill=VIOLET[4] + (255,), width=1)
    # flat angular carapace, pitched forward when lunging
    tilt = int(lunge * 4)
    pts = [(cx - 15, cy + 2), (cx - 10, cy - 7 - tilt), (cx - 2, cy - 11 - tilt), (cx + 6, cy - 10 - tilt),
           (cx + 14, cy - 5), (cx + 16, cy + 3), (cx + 6, cy + 7), (cx - 8, cy + 7)]
    d.polygon(pts, fill=VIOLET[3] + (255,), outline=OUTLINE)
    d.polygon([pts[1], pts[2], pts[3], (cx + 2, cy - 3)], fill=VIOLET[5] + (255,))
    d.polygon([pts[5], pts[6], pts[7], (cx, cy + 2)], fill=VIOLET[2] + (255,))
    for c in ([(cx - 11, cy), (cx - 5, cy - 4)], [(cx + 8, cy - 6), (cx + 12, cy + 1)]):
        d.line(c, fill=AMBER[2] + (255,)); de.line(c, fill=AMBER[2])
    # eye cluster
    if eye > 0:
        for (ex, ey, r) in [(-4, -2, 2.2), (1, -4, 2.8), (6, -1, 2.0)]:
            r = r * eye
            box = [cx + ex - r, cy + ey - r, cx + ex + r, cy + ey + r]
            d.ellipse(box, fill=AMBER[3] + (255,), outline=OUTLINE)
            de.ellipse(box, fill=AMBER[3])
            d.point((cx + ex, cy + ey), fill=AMBER[4] + (255,)); de.point((cx + ex, cy + ey), fill=AMBER[4])
    if cut is not None:
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        if cut < 0:
            md.rectangle([0, 0, cx, S], fill=255)
        else:
            md.rectangle([cx, 0, S, S], fill=255)
        w.putalpha(Image.fromarray(np.minimum(np.array(w.split()[3]), np.array(mask))))
        e = Image.fromarray((np.array(e) * (np.array(mask)[..., None] / 255)).astype(np.uint8))
    if flash:
        a = np.array(w)
        m = a[..., 3] > 0
        a[m, :3] = (a[m, :3] * 0.3 + np.array([255, 240, 225]) * 0.7).astype(np.uint8)
        w = Image.fromarray(a)
    img.alpha_composite(w, dest=off)
    emi.paste(e, off, mask=Image.fromarray((np.array(e).sum(-1) > 0).astype(np.uint8) * 255))


def skitter_frame(i):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    emi = Image.new("RGB", (S, S), (0, 0, 0))
    cx, cy = 32, 44
    if i in (0, 1):
        skitter_body(img, emi, cx, cy - i, i * 2.4)
    elif i == 2:
        skitter_body(img, emi, cx, cy - 3, 1.0, eye=1.4, lunge=1.0)
    elif i == 3:
        skitter_body(img, emi, cx, cy + 1, 0.5, eye=0.6, flash=True)
    else:
        t = (i - 4) / 3.0
        sep = int(1 + t * 9)
        skitter_body(img, emi, cx, cy, 0.3, eye=max(0, 1 - t * 2), cut=-1, off=(-sep, int(t * 3)))
        skitter_body(img, emi, cx, cy, 0.3, eye=0, cut=1, off=(sep, int(t * 4)))
        g = np.random.default_rng(40 + i)
        d = ImageDraw.Draw(img); de = ImageDraw.Draw(emi)
        for _ in range(int(5 + t * 12)):
            a = g.random() * math.tau
            r = 4 + t * 22 * g.random()
            x, y = cx + math.cos(a) * r, cy - 4 + math.sin(a) * r * 0.5
            c = AMBER[g.integers(1, 4)]
            d.rectangle([x, y, x + 1, y + 1], fill=c + (255,)); de.rectangle([x, y, x + 1, y + 1], fill=c)
        if i == 7:
            a = np.array(img)
            a[..., 3] = (a[..., 3] * (g.random((S, S)) > 0.55)).astype(np.uint8)
            img = Image.fromarray(a)
            emi = Image.fromarray((np.array(emi) * (np.array(img)[..., 3:] > 0)).astype(np.uint8))
    return img, emi


sheet = Image.new("RGBA", (S * N, S), (0, 0, 0, 0))
esheet = Image.new("RGB", (S * N, S), (0, 0, 0))
for i in range(N):
    f, e = skitter_frame(i)
    sheet.alpha_composite(f, dest=(i * S, 0))
    esheet.paste(e, (i * S, 0))
sheet.save(os.path.join(OUT, "skitter_albedo.png"))
esheet.save(os.path.join(OUT, "skitter_emission.png"))
prev = Image.new("RGBA", (S * N, S), (40, 44, 52, 255))
prev.alpha_composite(sheet)
prev.resize((S * N * 3, S * 3), Image.NEAREST).save(os.path.join(ROOT, "shots", "skitter_sheet.png"))
print("skitter sheet saved")

