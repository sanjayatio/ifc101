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

- Columns: H 150×150 at the grid points listed under `columns`, on both storeys.
- Main beams (WF 200×100) run along y at x = 0, 3, 6.
- Secondary beams (WF 150×75) run along x. Spans are split wherever they cross a main beam.

## Roof

The roof is five parts, each its own `IfcRoof` with one sloped panel over 3 or 4 corners `[x, y, z]`, where z is the rise above that roof's eaves. The eaves sit on a 0.5 m wall, so they are at z = 6.5, and the total above the roof slab is `wall_height` + z. The corners are written as built: the roof edges that stand on the first-floor AAC walls reach 0.05 m past the grid line (x = -0.55, y = 7.05, x = 7.05), flush with the outer face of those walls. Roof walls are light: steel sandwich panel (`SteelSandwich_50`) for parapets and infill, and steel-framed polycarbonate (`PolycarbonateFramed_16`) under the peak and along the x = 3 edge, so daylight reaches the deck.

The north half is three triangles that meet in one point, the peak at (3, 3.5), 2.17 m above the eaves. The peak sits on the high edge of `roof_south_east` (x = 3), so all four roofs meet there:
- `roof_north` (polycarbonate): the north slope, corners (7.05, 7.05), (-0.55, 7.05) and the peak. About 32°.
- `roof_west` (polycarbonate): the west slope, corners (-0.55, 7.05), (-0.55, 3.5) and the peak. About 31°.
- `roof_east` (polycarbonate): the east slope, corners (7.05, 3.5), (7.05, 7.05) and the peak. About 28°, continuing the slope of `roof_south_east`.

The south:
- `roof_south_east` (polycarbonate): a lean-to over x 3 to 7.05, y 0 to 3.5, high on the west (2.17 m, the same elevation as the peak, which sits at its north-west corner) and sloping down to the east. About 28°. Its high edge is a 2.67 m polycarbonate wall along x = 3 with a door opening at y 1-2 where the stair lands (2.1 m high, lintel above; the door leaf is not modelled).
- `roof_2` (metal): the small lean-to over the bathroom and toilet, y -0.65 to 0, sloping down to the south. Height 0.17 m.

Walls (`wall_height` 0.5 m for the five parts above; `roof_2` has none):
- Parapets (`parapet`, a list of edge numbers; edge i runs from corner i to corner i + 1): only on edges that have a structure under them: north (y = 7.05), east (x = 7.05) and the room's west side (x = -0.55, y 3.5-7.05). Edges facing the void have no wall.
- Every other edge that is raised above its eaves gets a wall up to the roof surface, in the roof's `wall` type unless `edge_walls` says otherwise. Where another roof meets the edge there is no wall below that roof's surface, so only the gap above the lower roof is closed. A sloped edge that is not axis-aligned must be shared with another roof (the hip lines between the three triangles).
- The wall under the south edge of `roof_west` is polycarbonate. `roof_east` and `roof_south_east` are one continuous slope along y = 3.5, so no wall stands between them.
- `roof_south_east` also gets a wall along its south edge, above `roof_2`.

Not yet checked: the gutter and overflow pipes (`pipe_collect`, `pipe_gutter_overflow`) were laid out against the old roof and have not been moved to the new one.

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
- No columns or beams exist at the roof level yet. The x = 3 wall and the parapets need a steel ring beam on top, tied down to the columns,
  and the roof needs rafters and purlins.
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
- `walls`: loose wall runs, `{storey, from, to, wall}`.
- `tanks`: `id`, `storey`, `name`, `rect`, `height`, optional `z`.
- `pipes`: `id`, `storey`, `name`, `diameter`, `path` (a list of `[x, y, z]` points; each straight stretch becomes a pipe segment).
- `columns`, `stairs`, `beams`: see `spec.json`.

Room `name` is a label only; it doesn't reach the generated file.
