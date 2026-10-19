# Project Conamara

Boomer shooter. Conamara Station, Europa: a research station that was quietly digging toward
something, on the day it switches it on. Godot 4.7 (Compatibility), TrenchBroom levels via
FuncGodot, 2D sprite enemies, retro textures + modern lighting.

- `docs/premise.md` — the setting and the story.
- `docs/levels.md` — the level plan and the rules every level follows.
- `docs/licenses/` — third-party art (LibreQuake textures, BSD-3). Ship these with the game.

## Level pipeline

    tools/rebuild_tb.sh test01            # levels/test01.map -> levels/test01.tscn -> shots/contact_test01.png
    tools/rebuild_tb.sh test02 42 56      # new layout from seed 42 (56x56 cells), then build + shoot
    THEME=kit tools/rebuild_tb.sh test01  # dressing theme: quake (default) | kit

Layout → `tools/mapgen.py` (rooms, loops, pits, catwalk, stairs, doors) → `levels/<name>.json`.
Dressing → `tools/export_map.py` → `levels/<name>.map`: one TrenchBroom layer per rule (floor,
border, ceiling, skirting, panel, cornice, beam, stairs, lamp, doorframe, rib, pipe, pilaster, wallbox,
pillar), brushes chunked into
8 m `func_detail` entities; entities for player start, lights, doors, enemies, pickups, exit,
screenshot markers. Scene → `tools/build_tb_level.gd` (FuncGodot) → `levels/<name>.tscn`, root
script `scripts/level.gd` (flow field for enemies from the level json, dev hooks).

Generated layouts are the clay. Once a level is adopted it's hand-owned in TrenchBroom
(`levels/trenchbroom/Conamara/` has the game config + FGD: copy into TrenchBroom's `games/`,
set the game path to this repo) and never regenerated.

Units: 32/m. Cell 64 (2 m). Floor step 32 (1 m). Ceiling level 56 (1.75 m). Door opening
1.5 m × 3.3 m per cell (door scene gets `slab_width`).

## Textures

`art/textures/tb/` — our own generated 64 px kit tiles (`tools/gen_tb_textures.py`).
`art/textures/lq/<set>/` — LibreQuake sets (tech, metal, terra, conc, liquidsky, flesh, props,
utility). `*_fbr` are fullbright layers → emission. Normal/roughness/emission maps are generated
by `tools/gen_tb_textures.py` next to each albedo; FuncGodot builds a nearest-filtered
StandardMaterial3D per texture from `art/textures/tb/_template.tres`.

## Playtest notes

In any level press **Q** to drop a note pin where you stand, type, Enter. Lines go to
`levels/notes/<level>.jsonl` (note, position, grid cell, view direction) and pins show in-world.
Commit the file; Claude reads it.

## Dev flags (run a level scene with `-- <flag>`)

`--capture` renders every `shot` marker to `shots/`. `--playtest` runs the bot. `--movetest`
walks the player and climbs a stair, printing positions. `--notetest` drops one pin and quits.
