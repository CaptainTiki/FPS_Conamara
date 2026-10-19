# Status — where we are (keep this current; it's the handoff between sessions)

Updated 2026-10-19 (pm).

## Done
- TrenchBroom/FuncGodot pipeline (`tools/rebuild_tb.sh`), Godot 4.7.1, Jolt. Cloud sessions build + screenshot headless.
- Textures: LibreQuake sets imported (BSD-3, `docs/licenses/`), PBR maps generated, `quake` theme active.
- Dressing rules in `tools/export_map.py`: floors, borders, ceilings, skirting/panel/cornice bands, diagonal
  corner walls + risers, 8-step stairs with clip ramp, beams, pendant lamps, door frames sized to the Door
  scene, corridor ribs, overhead + wall pipes, pilasters, wall boxes/vents, octagonal pillars, crates,
  enemies/pickups/exit seeding, screenshot markers.
- `levels/test01` (seed 11, 56x56) — the level we solidify rules on. NOT yet adopted (regenerating overwrites).
  Regenerated 2026-10-19 after the first 13 pins: 2-wide corridors + doors, clean door placement,
  per-section corridor ramps + cliff healing, panel recess/posts, dark ribs, pipe ends, half-step
  ledges, pit ladders (`prop_ladder`), fully-lit lamps, corridor lamp coverage. Rules in `levels.md`.
- Q note pins -> `levels/notes/<level>.jsonl`. Answered batches move to `levels/notes/archive/`.
  Pin `cell` now uses the level's real row count (was hardcoded 72).

## Next
- John replays test01 (pull first; delete any local `levels/notes/test01.jsonl` so stale pins don't load) and pins the next batch.
- Hub pit riser is a flat 2 m face: wants a band / grating / something.
- Replace random raised platforms with purposeful features (dais + console, machinery pit with pipes, drain).
- More depth: ceiling pipe runs along beams, cable trays, door alcoves with a light, wall lights, floor drains,
  dropped half-ceiling at room edges, a few broken things (open panel, flickering light).
- `ice` theme (terra set tinted blue-white, brown fracture lines) and `alien` theme (metal+flesh hue-shifted
  violet, wet roughness, glowing runes; veins through metal, never walls of meat).
- Adopt test01 once John has hand-touched it in TrenchBroom; then Admin.

## How we work
- John plays, drops Q pins, commits `levels/notes/`. Claude reads them, turns each into a rule change, a
  TrenchBroom edit, or a "that's hand-edit territory", rebuilds, screenshots, pushes.
- Commit style: a few short descriptors, no body; push straight to main.
- Level rules live in `docs/levels.md`; premise in `docs/premise.md`.
