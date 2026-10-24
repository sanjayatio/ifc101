# 7x7

A 7 m × 7 m, two-storey house. `spec.json` is the hand-edited source of truth;
`design.ifcjson` is generated from it and should not be edited directly.

```
python gen.py 7x7
```

Storey height is 3 m (`ground` at z = 0, `first` at z = 3). Coordinates are metres, x east and y north.

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

## Structure

- Columns: H 150×150 at the grid points listed under `columns`, on both storeys.
- Main beams (WF 200×100) run along y at x = 0, 3, 6.
- Secondary beams (WF 150×75) run along x. Spans are split wherever they cross a main beam.

## `spec.json` reference

- `slabs`: `id`, `storey`, `name`, `type` (`floor_100` or `floor_200`), `polygon`, optional `steel_grate`, optional `z`.
- `rooms`: walls built around an outline. Walls shared between rooms are merged into one run.
  - `rect`: `[x0, y0, x1, y1]`, or `polygon`: an axis-aligned outline given as a point list.
  - `wall`: `brick` or `aac`.
  - `doors`: `{side, from, to}` with `side` one of `north`, `south`, `east`, `west`, and `from`/`to` the span along that
    edge. For a `polygon`, `side` is the direction the edge faces and the door goes on the edge that contains its span.
    Default height is 2.1 m, with a lintel above.
  - `open`: `{side, from, to}`; that stretch of the edge gets no wall. Needed on both rooms that share the edge.
- `walls`: loose wall runs, `{storey, from, to, wall}`.
- `columns`, `stairs`, `beams`: see `spec.json`.

Room `name` is a label only; it doesn't reach the generated file.
