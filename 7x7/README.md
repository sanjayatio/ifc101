# 7x7

A 7 m × 7 m, two-storey house with a roof deck under a pitched roof. `spec.json` is the hand-edited source of truth;
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
leaves the stair void open (x 0–3, y 1–3.5, and x 0–2.4, y 0–1).

## Stairs

The U-shaped steel stair sits in the void at the west end, x 0–3, y 1–3.5. `stair_1` rises from the ground to the
first floor and `stair_2` repeats it from the first floor to the roof deck. Each has two flights of 1.5 m rise and
2 m run around a landing at z + 1.4.

## Structure

- Columns: H 150×150 at the grid points listed under `columns`, on both storeys.
- Main beams (WF 200×100) run along y at x = 0, 3, 6.
- Secondary beams (WF 150×75) run along x. Spans are split wherever they cross a main beam.

## Roof

`roof_1` is a 30° polycarbonate roof over the 7 × 7 footprint. Its eaves sit on a 0.5 m AAC wall, so they are at z = 6.5.

- Peak: a ridge along x = 3.5, from the south edge to y = 3.5, where the north hip starts.
- North, east: the hip and the east slope run to the full footprint.
- South: a vertical gable (`roof_1_gable_south`), built only from x = 2.4, where `slab_roof` starts under it.
- West: from the south edge to y = 3.5 the slope stops 2 m west of the ridge (x = 1.5), so it overhangs the stair void and
  covers the top of the stair. `roof_1_infill_west` closes the sloped gap above the room's south wall, x 0–1.5 at y = 3.5.
- Walls (`parapet`): 0.5 m, only on edges that have a structure under them: north (y = 7), east (x = 7) and the room's
  west side (x = 0, y 3.5–7). Edges facing the void have no wall.

Why this shape: the void has nothing under it to carry a wall or roof, so the roof cannot stay a full square. The west
slope is cut short instead, which keeps the peak where it was and still covers the top of the stair.
Headroom there is about 2.2 m (the roof at x = 3 is 2.23 m above the slab).

Open points:
- The overhang between x 1.5 and 3 has no support yet (rafters from the x = 3 line, or posts at the stair).
- No columns or beams exist at the roof level yet.
- The gable is open between x 1.5 and 2.4, and the cut edge at x = 1.5 is open.
- The edges facing the void have no wall or guard rail.

## `spec.json` reference

- `slabs`: `id`, `storey`, `name`, `type` (`floor_100` or `floor_200`), `polygon`, optional `steel_grate`, optional `z`.
- `rooms`: walls built around an outline. Walls shared between rooms are merged into one run.
  - `rect`: `[x0, y0, x1, y1]`, or `polygon`: an axis-aligned outline given as a point list.
  - `wall`: `brick` or `aac`.
  - `doors`: `{side, from, to}` with `side` one of `north`, `south`, `east`, `west`, and `from`/`to` the span along that
    edge. For a `polygon`, `side` is the direction the edge faces and the door goes on the edge that contains its span.
    Default height is 2.1 m, with a lintel above.
  - `open`: `{side, from, to}`; that stretch of the edge gets no wall. Needed on both rooms that share the edge.
- `roofs`: `id`, `storey`, `rect`, optional `pitch` (degrees, default 30), `panel` (`metal` or `polycarbonate`), `wall` (`brick` or `aac`), `wall_height` (raises the eaves), `gable` (`south`), `gable_from` (x where the gable wall starts), `west_run`, `parapet` (list of `[[x, y], [x, y]]` wall runs).
- `walls`: loose wall runs, `{storey, from, to, wall}`.
- `columns`, `stairs`, `beams`: see `spec.json`.

Room `name` is a label only; it doesn't reach the generated file.
