# 7x7

A 7 m × 7 m, two-storey house with a roof deck under a pitched roof. The roof is five parts: three polycarbonate slopes (north, west, east) that meet in one peak over the north half, a polycarbonate lean-to over the south-east with the door to the stair, and a small metal lean-to over the bathroom and toilet. It has light walls, and a rainwater tank at the foot of the stair, fed by a gutter
with an overflow to the south. `spec.json` is the hand-edited source of truth;
`design.ifcjson` is generated from it and should not be edited directly.

```
python gen.py 7x7
```

Storey height is 3 m (`ground` at z = 0, `first` at z = 3, `roof` at z = 6). Coordinates are metres, x east and y north.

## Layout

| Storey | Space | Footprint | Walls | Notes |
|---|---|---|---|---|
| ground | `open` | rect (0, 0)–(3, 5) | brick | holds the U-shaped steel stair; no wall towards the garage between y 0 and 4.5 |
| ground | `room` | rect (0, 4.5)–(3, 7) | brick | door south, x 1–2 |
| ground | `garage` | rect (3, 0)–(7, 7) | brick | door south, x 3–6; no wall towards `open` between y 0 and 4.5 |
| first | `room` | rect (0, 3.5)–(3, 7) | AAC | door east, y 3.5–4.5 |
| first | `toilet` | rect (2.4, 0)–(4, 1) | AAC | door north, x 3–4 |
| first | `bathroom` | rect (4, 0)–(7, 2) | AAC | door north, x 4–5 |
| first | `hall` | polygon, same outline as `slab_hall` | AAC | door south, x 3–4 (the notch edge at y 3.5) |

Floors on the first storey are 100 mm slabs. `slab_first` and `slab_hall` are steel grate;
the others are solid.

`slab_roof` (steel grate, 100 mm, top at z = 6) is the floor under the roof. It follows the first-storey outline and
leaves the stair void open (x 0–3, y 1–3.5, and x 0–2.4, y 0–1). The strip x 2.4–3, y 0–1 outside the roof's x = 3 wall is covered by `roof_2`.

## Stairs

The U-shaped steel stair sits in the void at the west end, x 0–3, y 1–3.5. `stair_1` rises from the ground to the
first floor and `stair_2` repeats it from the first floor to the roof deck. Each has two flights of 1.5 m rise and
2 m run around a landing at z + 1.4.

## Structure

- Columns: H 150×150 at the grid points listed under `columns`, on both storeys, rotated 90° (`rotation`) so the flanges face x: the main beams frame into the flange faces and the secondaries into the web.
- Main beams (WF 200×100) run along x at y = 0, 2, 4.5, 6.5, split at the x = 3 column (3 m spans).
- Secondary beams (WF 150×75) run along y at x = 0 to 6. Spans are split wherever they cross a main beam.
- Roof beams: the same layout under `slab_roof`, at z = 6, with lighter sections: main WF 125×60, secondary WF 100×50. The sections are placeholders until the roof loads are checked.

## Roof

The roof is five parts, each its own `IfcRoof` with one sloped panel over 3 or 4 corners `[x, y, z]`, where z is the rise above that roof's eaves. There is no parapet: the eaves are at the roof slab (z = 6.0), and the peak is 2.17 m above it (z = 8.17). The roof rests on the knee walls (see below) and overhangs them on the low sides. The corners are written as built: the roof edges reach 0.05 m past the grid line (x = -0.55, y = 7.05, x = 7.05), flush with the outer face of the first-floor AAC walls. Roof walls are light: steel sandwich panel (`SteelSandwich_50`) for infill, and steel-framed polycarbonate (`PolycarbonateFramed_16`) under the peak and along the x = 3 edge, so daylight reaches the deck.

The north half is three triangles that meet in one point, the peak at (3, 3.5), 2.17 m above the eaves. The peak sits on the high edge of `roof_south_east` (x = 3), so all four roofs meet there:
- `roof_north` (polycarbonate): the north slope, corners (7.05, 7.05), (-0.55, 7.05) and the peak. About 32°.
- `roof_west` (polycarbonate): the west slope, corners (-0.55, 7.05), (-0.55, 3.5) and the peak. About 31°.
- `roof_east` (polycarbonate): the east slope, corners (7.05, 3.5), (7.05, 7.05) and the peak. About 28°, continuing the slope of `roof_south_east`.

The south:
- `roof_south_east` (polycarbonate): a lean-to over x 3 to 7.05, y 0 to 3.5, high on the west (2.17 m, the same elevation as the peak, which sits at its north-west corner) and sloping down to the east. About 28°. Its high edge is a 2.17 m polycarbonate wall along x = 3 with a door opening at y 1-2 where the stair lands (2.1 m high, so only 0.07 m of lintel above it; the door leaf is not modelled).
- `roof_2` (metal): the small lean-to over the bathroom and toilet, y -0.65 to 0, sloping down to the south. Height 0.17 m.

Walls (none at the eaves; `edge_walls` and the hips below):
- Every sloped edge that is raised above its eaves gets a wall up to the roof surface, in the roof's `wall` type unless `edge_walls` says otherwise. Where another roof meets the edge there is no wall below that roof's surface, so only the gap above the lower roof is closed. A sloped edge that is not axis-aligned must be shared with another roof (the hip lines between the three triangles).
- The wall under the south edge of `roof_west` is polycarbonate. `roof_east` and `roof_south_east` are one continuous slope along y = 3.5, so no wall stands between them.
- `roof_south_east` also gets a wall along its south edge, above `roof_2`.

Not yet checked: the gutter and overflow pipes (`pipe_collect`, `pipe_gutter_overflow`) were laid out against an older roof and have not been moved to this one. The roof is now 0.5 m lower than in the parapet version, so they need a fresh look.

### Knee walls

The roof has no parapet. Where it comes down to the low edges it rests on knee walls set back from the eaves, built from light posts and a rail instead of a solid wall (`knee_walls` in `spec.json`; the parapet code stays in `gen.py`, unused here). Each run is a line on the first-storey column grid:

| Run | Line | Between | Under | Set back from the eaves |
|---|---|---|---|---|
| `north` | y = 6.5 | x 0-6 | `roof_north` | 0.55 m |
| `west` | x = 0 | y 4.5-6.5 | `roof_west` | 0.55 m |
| `east` | x = 6 | y 0-4.5 | `roof_south_east`, `roof_east` | 1.05 m |

- The set-backs were asked as 0.5 m (north, west) and 1 m (east) from the low edge. The columns stand on the 7 m grid, so the walls sit on them and the distance to the roof edge, which overhangs the grid by 0.05 m, comes out 0.05 m more.
- A post stands on every first-storey column along the run, from the column top (z = 6.0). Its height is derived from the roof: the roof surface above it (0.336 m on `north` and `west`, 0.563 m on `east`) less the rail depth. A rail along the posts carries the roof ribbing and stops at the face of the rail it meets at a corner.
- Posts and rail are `RHS_75x75x3`, a light hollow section, not H or WF. The size is a placeholder until the roof loads are known.
- `west` and `north` meet at the corner column (0, 6.5), which lies on the hip between `roof_west` and `roof_north`, so both rails are at the same height there.
- Posts exist only where there are columns. `east` stops at y 4.5, 1.6 m short of the hip with `roof_north`; the roof over y 4.5-6.1 is cantilevered until a support is added there.

## Rainwater

`tank_rain` is a 1.5 m tall rainwater tank in the north-west corner of the open ground-floor area, inside the brick walls
(x 0.05–1, y 3–4.45). It is modelled as a solid box, so the interior is not drawn. Its top is level with the stair landing's top (z = 1.5).
Below the first-floor room slab it is closed over; its southern 0.5 m (y 3–3.5) is under the open void.

- `pipe_collect` (a `GUTTER`): a 100 mm channel that collects the water running off the cut edge at x = 3. It hangs on the west face of
  the x = 3 wall, just under the roof edge (z 8.2 at y = 0, falling slightly to 8.17 at y = 3.4), runs north to y = 3.4, then turns west and
  follows the sloped roof edge above the infill wall at y = 3.5, down to the corner at x = −0.1 (z 6.37).
- `pipe_feed`: the 100 mm downpipe from that corner at (x −0.1, y 3.4), down to z = 1.4, then through the brick wall into the tank. Normal
  rain goes this way.
- `pipe_gutter_overflow`: the excess in a very heavy rain. It leaves the south end of the gutter from an inlet raised above the gutter floor,
  steps out to x = 2.6, runs down the south face, and discharges to the south, street side, at z = 0.3, y = −0.5. It sits 0.3 m west of the
  H-beam column at (3, 0), so the column does not stand in its path.
- `pipe_overflow`: a 100 mm pipe at z = 1.2 from the tank's south face, running along x = 0.5 under the stair landing (whose underside
  is at 1.4) and out through the south wall to y = −0.3. The tank holds about 1.6 m³ below it.

The pipes and the gutter are solid round pipes, and the gutter stands in for an open one (its type is `GUTTER`).

## Open points

Structure
- Roof level has only the knee-wall posts and rails. The x = 3 wall needs a steel ring beam on top, tied down to the columns, and the
  roof needs rafters and purlins. The knee walls need more supports (see Knee walls) and a check of the section.
- With the roof 0.5 m lower, the door at the stair top has only 0.07 m of lintel above its 2.1 m opening; the wall needs a header or the door a lower height.
- Wind uplift is the main risk for a light roof this high up and open on the void side. The tie-down from panel to purlin to rafter to ring
  beam to column has to be designed and checked by a structural engineer, using the SNI wind loads for the site.
- The edges facing the void have no wall or guard rail.

Openings
- The door leaf at the stair top is not modelled, only the opening. The posts and header around it come from the steel frame.
- The pipes through the brick walls (`pipe_feed`, `pipe_overflow`) have no openings cut in them.

Water
- Gutters exist only on the x = 3 cut edge. The main roof's north and east eaves and its west eave north of y = 3.5 have none, and `roof_2`
  still sheds water west into the void, onto the stair.
- The gutter on x = 3 hangs directly over the columns at (3, 0) and (3, 2), so a leak would run down onto them. It needs flashing and a
  drip edge, and the column tops need protection.
- The tank needs a lid or screen at its southern end (y 3–3.5), which is open to the void.
- With the roof and walls closed, the grate floor under them stays dry apart from wind-driven rain through the stair door (sill and door seals).

## `spec.json` reference

- `slabs`: `id`, `storey`, `name`, `type` (`floor_100` or `floor_200`), `polygon`, optional `steel_grate`, optional `z`.
- `rooms`: walls built around an outline. Walls shared between rooms are merged into one run.
  - `rect`: `[x0, y0, x1, y1]`, or `polygon`: an axis-aligned outline given as a point list.
  - `wall`: `brick` or `aac` (`sandwich` and `polycarbonate` also exist, used on the roof).
  - `doors`: `{side, from, to}` with `side` one of `north`, `south`, `east`, `west`, and `from`/`to` the span along that
    edge. For a `polygon`, `side` is the direction the edge faces and the door goes on the edge that contains its span.
    Default height is 2.1 m, with a lintel above.
  - `open`: `{side, from, to}`; that stretch of the edge gets no wall. Needed on both rooms that share the edge.
- `roofs`: one entry per roof, each its own `IfcRoof` with one sloped panel: `id`, `storey`, `corners` (3 or 4 points `[x, y, z]`, z = rise above the eaves; a fourth point must lie in the plane of the first three), optional `panel` (`metal` or `polycarbonate`), `wall` (`brick`, `aac`, `sandwich` or `polycarbonate`; the default type of the roof's walls), `wall_height` (raises the eaves), `parapet` (edge numbers that get a wall of `wall_height`), `edge_walls` (per edge number: `{wall, doors}` overrides the type or adds `{from, to}` openings, `null` leaves the edge open).
- `knee_walls`: `storey`, `columns` (the storey whose columns carry the posts), `section` (`width`, `depth`, `thickness` of the hollow section) and `runs`: `{id, axis, at, from, to, roofs}`, a line `axis` = `x` or `y` at coordinate `at`, between `from` and `to`, under the listed roofs. The generator fails if the roof is not level along a run.
- `walls`: loose wall runs, `{storey, from, to, wall}`.
- `tanks`: `id`, `storey`, `name`, `rect`, `height`, optional `z`.
- `pipes`: `id`, `storey`, `name`, `diameter`, `path` (a list of `[x, y, z]` points; each straight stretch becomes a pipe segment).
- `beams`: one block or a list of blocks (one per storey): `storey`, `main` and `secondary` (`{axis, at, spans}`), optional `sections` (`main` / `secondary`: `WF_200x100`, `WF_150x75`, `WF_125x60` or `WF_100x50`).
- `columns`: groups of `{storey, at, rotation}`; `rotation` 90 turns the H section so its flanges face x.
- `stairs`: see `spec.json`.

Room `name` is a label only; it doesn't reach the generated file.
