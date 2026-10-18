# Levels — intended, not final

Eleven levels in three parts. Each level is self-contained: hub-and-loops *inside* it, done when
you leave. No backtracking across levels. Revisits happen within a level (same room, different
state), never by sending the player back through an earlier level.

## Rules that apply to every level

- **Lots of small rooms, all interconnected.** The Doom-map shape: 15–25 rooms, loops, doors that
  matter. That is the sauce. No arenas, no "big open room", no long sightlines. A big room is a
  maze with a high ceiling (planter rows, partitions, pillars), not a field.
- **A room's purpose is to be a good fight.** Most rooms are "another room to fight in". A couple
  of props make it read as somewhere; that's set dressing, not design. Don't make rooms try to be
  a cafeteria.
- **Stack gates.** A blocked door is never bypassed by the very next room; the answer is several
  rooms away. Keycards are fine as one link in a chain.
- Generated layout is the clay (`tools/mapgen.py` → `tools/export_map.py`). Once a level is
  adopted it is hand-owned in TrenchBroom and never regenerated. Recurring hand fixes become rules.
- Props, enemies, pickups and the exit are point entities placed in TrenchBroom (the exporter
  seeds a first pass).

## Themes (texture sets, see `tools/export_map.py` THEMES)

| Theme | Set | Used by |
|---|---|---|
| `quake` (station tech) | `lq/tech` | Station levels, Tunnel start |
| `ice` (to do) | `lq/terra` snow/rock, tinted blue-white; brown fracture lines | Relay, Tunnel middle |
| `alien` (to do) | `lq/metal` + `lq/flesh`, hue-shifted violet, wet roughness, glowing runes; veins through metal, never walls of meat | Tunnel end, Through |

## The levels

### Station
1. **test01** *(not a game level — the level we solidify the rules on first)*
2. **Admin** — arrival. Badge, locker, security office, onboarding tour. Ends with the first alarm. Tech, lights on then off.
3. **The Dome** — hydroponics. Daylight lamps, the only green on the moon, water. Big but maze-like: planter rows and partitions.
4. **Habitation** — hab ring, cabins (bed, locker, partition to walk round), mess, medbay. First breakers, first skitters.
5. **Maintenance** — ducts, shafts, pipes, generators. Darkest level. Filler-style, stretches play time.
6. **Relay** — out on the ice, 0.13 g, Jupiter overhead. Restore the relay; Earth answers: fourteen months. Ice theme only.
7. **Labs** — science wing, specimen storage (what they are, before where they're from), the first serious keycard chain.

### Down
8. **The Tunnel** — one level, the whole descent. Starts as finished corridor, lining stops, bare ice and rock with work lights, then the rock stops being rock. Human → rock → alien in one walk. Elevator, landings, ladders.
9. **Portal Room** — the chamber at the bottom with the thing in it. Control room is slag. Survivors: it closes from the other side. Nobody has been through.

### Through
10. **Threshold** — first steps on the other side. Our light, their walls.
11. **Their Station** — whatever this place is to them. Their doors, their power; nothing of ours works.
12. **The Mechanism** — close it, then the run back with the clock running. Whether you make it is the last thing the player decides.

## What belongs where

- Tech props (consoles, crates, breakers, lockers, pickups in crates): Station and the Tunnel start only.
- Ice/rock: Relay, Tunnel middle. Nowhere else.
- Water: from the Dome down.
- Ducts: from Maintenance on. Keycards: from Labs on.
- Alien material: Tunnel end and Through. Never topside.
- Low gravity: outside the station only (Relay).

## Play-time benchmark

~15 min per level with exploration + combat. Measured by bot-vs-human ratios over repeated
playtests (`-- --playtest`), not estimated. Rooms that take time to check and loot stretch time;
long sightlines shrink it.
