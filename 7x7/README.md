# 7x7

A 7 m × 7 m, two-storey house with a roof deck under a pitched roof. The roof is five parts: three polycarbonate slopes (north, west, east) that meet in one peak over the north half, a spandek lean-to over the south-east with the door to the stair, and a small metal lean-to over the bathroom and toilet. It has light walls, and a rainwater tank at the foot of the stair, fed by a gutter
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
the others are solid. On the ground storey there is no slab under the open stair area (x -0.5–3, y 0–4.5): `slab_garage` covers x 3–7 and `slab_watch` x -0.5–3, y 4.5–7.

### Slab materials

Each slab can set a `material`, which becomes its own slab type and a surface colour in the render. Slabs without one (the steel-grate slabs) stay uncoloured.

| Slab | Material | Colour | Status | Notes |
|---|---|---|---|---|
| `slab_garage` | Lean concrete with wiremesh M5, 80 mm | grey | Decided | Thickness is 80 mm (`floor_80`), down from the 200 mm packed-dirt fill. |
| `slab_watch` | Lean concrete with wiremesh M5, 80 mm, with tiles on top | terracotta | Decided | Same concrete as `slab_garage` plus a 20 mm tile and adhesive layer (assumed), 100 mm in all. Replaces the raised tile on pedestals. |
| `slab_room` | TBD | amber | Open | Diamond steel plate is a candidate, but a carpet on it would hold spilled water and promote rust. Other options: grate with a tile or vinyl overlay, or a sealed deck. |
| `slab_toilet`, `slab_bath` | Waterproofed steel deck | teal | Decided | One material for both. Chosen over concrete, which at 100 mm is about 240 kg/m² and heavy on the toilet cantilever. Needs a sealed membrane and upstands at the walls. |
| `slab_cover`, `slab_room_roof` | Diamond steel plate | blue-grey | Decided | Solid, for privacy. |

`slab_roof` (steel grate, 100 mm, top at z = 6) is the floor under the roof. It follows the first-storey outline and
leaves the stair void open (x 0–3, y 1–3.5, and x 0–2.4, y 0–1). The strip x 2.4–3, y 0–1 outside the roof's x = 3 wall is covered by `roof_bath`.

## Stairs

The U-shaped steel stair sits in the void at the west end, x 0–3, y 1–3.5. `stair_1` rises from the ground to the
first floor and `stair_2` repeats it from the first floor to the roof deck. Each has two flights of 1.5 m rise and
2 m run around a landing at z + 1.4.

The first 7 treads of `stair_1`'s first flight are packed solid (`solid: 7` on the flight): blocks from the ground up to each tread, stopping at x = 1.25, 0.05 m short of the septic tank's east face (see Septic tank). The eighth tread stays a steel plate.

## Structure

- Columns: H 150×150 at the grid points listed under `columns`, on both storeys, rotated 90° (`rotation`) so the flanges face x: the main beams frame into the flange faces and the secondaries into the web.
- Main beams (WF 200×100) run along x at y = 0, 2, 4.5, 6.5, split at the x = 3 column (3 m spans).
- Secondary beams (WF 150×75) run along y at x = 0 to 6. Spans are split wherever they cross a main beam.
- Roof beams: the same layout under `slab_roof`, at z = 6, with lighter sections: main WF 125×60, secondary WF 100×50. The sections are placeholders until the roof loads are checked.

## Roof

The roof is eleven parts, each its own `IfcRoof` with one sloped panel over 3 or 4 corners `[x, y, z]`, where z is the rise above that roof's eaves. There is no parapet: the eaves are at the roof slab (z = 6.0), and the peak is 2.17 m above it (z = 8.17). The roof rests on the knee walls (see below) and overhangs them on the low sides. The corners are written as built: the roof edges reach 0.05 m past the grid line (x = -0.55, y = 7.05, x = 7.05), flush with the outer face of the first-floor AAC walls. Roof walls are light: steel sandwich panel (`SteelSandwich_50`) for infill, and steel-framed polycarbonate (`PolycarbonateFramed_16`) under the peak and along the x = 3 edge, so daylight reaches the deck.

The north half has four slopes. The peak at (3, 3.5), 2.17 m above the eaves, sits on the high edge of `roof_south_east` (x = 3). The north slope is split at x = 3 so the west half can stop at y = 4.5; the strip west of x = 3 and south of y = 4.5 is taken by the low roofs below:
- `roof_north_east` (insulated spandek on a rafter and purlin frame, see Roof rework): corners (7.05, 7.05), (3, 7.05) and the peak. About 31°.
- `roof_north_west` (insulated spandek, framed): corners (-0.55, 7.05), (3, 7.05) and (3, 4.5), 1.55873 m up. The rise is set so both north slopes have the same height along y = 6.5 (0.3362 m), so their posts there have the same height.
- `roof_west` (insulated spandek, framed): the west slope, corners (-0.55, 7.05), (-0.55, 4.5) and (3, 4.5). It stops at y = 4.5 instead of reaching the cantilever edge at y = 3.5.
- `roof_east` (insulated spandek, see Roof rework): the east slope, corners (7.05, 3.5), (7.05, 7.05) and the peak. About 28°, continuing the slope of `roof_south_east`.

The strip over the cantilevered room, y 3.5 to 4.5:
- `roof_slant` (polycarbonate): a shed roof, corners (-0.55, 3.5), (3, 3.5), (3, 4.5) and (0.45, 4.5), rising 0.43908 m to the north. That rise is exactly the height of `roof_west` at (0.45, 4.5), so the corner is closed.
- `roof_west_3` (polycarbonate): the triangle (-0.55, 3.5), (-0.55, 4.5), (0.45, 4.5) that fills the corner, at the same slope as `roof_west` along x = 0.

The south:
- `roof_south_east` (insulated and transparent spandek, see Roof rework): a lean-to over x 3 to 7.05, y 0 to 3.5, high on the west (2.17 m, the same elevation as the peak, which sits at its north-west corner) and sloping down to the east. About 28°. Its high edge is a 2.17 m polycarbonate wall along x = 3 with a door opening at y 1-2 where the stair lands (2.1 m high, so only 0.07 m of lintel above it; the door leaf is not modelled).
- `roof_stairs_1` and `roof_stairs_2` (polycarbonate): two bare shed roofs over the stair, west of x = 2.9, with no walls. `roof_stairs_2` (y 1 to 2) rises from 1.5 m at x = 0 to 2.17 m at x = 2.9; `roof_stairs_1` (y 2 to 3) is level along x at 1.5 m, falling to 1.4 m at y = 3.
- `roof_bath` (polycarbonate): the lean-to over the bathroom and toilet, y -0.65 to 0, rising to the north to 0.56259 m, the height of `roof_south_east` at (6, 0), so the two close at the corner.
- `roof_corner` (polycarbonate): the triangle (7.05, -0.65), (6.05, 0), (7.05, 0) that fills the south-east corner next to `roof_bath`.

Walls (none at the eaves; `edge_walls` and the hips below):
- A wall is opt-in: only a sloped edge named in `edge_walls` gets one, up to the roof surface, in the roof's `wall` type unless the entry overrides it. A roof with no `edge_walls` (the stair roofs) has none. Where another roof meets the edge there is no wall below that roof's surface, so only the gap above the lower roof is closed. A sloped edge that is not axis-aligned must be shared with another roof (the hip lines).
- The wall under the south edge of `roof_west` is polycarbonate (`edge_walls` `"1"`). `roof_east` and `roof_south_east` are one continuous slope along y = 3.5, so no wall stands between them.
- `roof_south_east` also gets a wall along its south edge, above `roof_bath` (edges 0 and 2).
- Corner heights shared by neighbouring roofs must agree to about 1e-9, or the generator makes a sliver wall (and can fail). `roof_slant` and `roof_west_3` therefore use 0.43907887324, not a rounded value.

The gutters are laid out in the Rainwater section.

### Knee walls

The roof has no parapet. Where it comes down to the low edges it rests on knee walls set back from the eaves, built from light posts and a rail instead of a solid wall (`knee_walls` in `spec.json`; the parapet code stays in `gen.py`, unused here). Each run is a line, mostly on the first-storey column grid:

| Run | Line | Between | Under | Posts |
|---|---|---|---|---|
| `north_west` | y = 6.5 | x 0.216-3 | `roof_north_west` (rafters) | no rail: one post under each rafter, at x 1, 2, 3, and under the hip rafter at x 0.216 |
| `north_east` | y = 6.5 | x 3-6 | `roof_north_east` (rafters) | no rail: one post under each rafter, at x 3, 4, 5, 6 (the post at x 3 is shared with `north_west`) |
| `west` | x = 0 | y 4.5-6 | `roof_west` (rafters) | no rail: one post under each rafter, at y 4.5, 5.25, 6 |
| `east_se` | x = 6 | y 0-3.5 | `roof_south_east` (rafters) | no rail: one post under each rafter, at y 0.1, 1, 2, 2.75, 3.5 |
| `east` | x = 6 | y 3.5-6.13 | `roof_east` (rafters) | no rail: one post under each rafter that reaches x = 6, at y 4.377, 5.253, and under the hip rafter at y 6.13 (the post at y 3.5 is shared with `east_se`) |
| `slant` | y = 4.5 | x 0.45-3 | `roof_slant` | column (3, 4.5); on the beam at (0.45, 4.5) |

- A post stands on every first-storey column along the run, from the column top (z = 6.0). Its height is derived from the roof: the roof surface above it less the rail depth. The rail carries the roof ribbing and stops at the face of the rail it meets at a corner. Rails are level, so the roof must be level along a run; the generator fails otherwise.
- A post can also stand on a roof beam instead of a column (`on_beam`, a list of `[x, y]`). These are at the hips, where the two slopes meet: (0.45, 4.5) the diagonal corner of `roof_slant`, and (0.216, 6.5), the hip between `roof_north_west` and `roof_west`, which carries the hip post of `north_west` (placed by `rafter_posts`, not `on_beam`). The beams are `beam_roof_y_6_s2` (also under the hip post of `east`), `beam_roof_x_6_5_m0` and `beam_roof_x_4_5_m0`, whose tops are at z = 6.0.
- There is no `bath` knee wall any more. Instead `supports` has `south_ridge`: two posts at (3, 0) and (3, 3.5) with a rail across their tops, along x = 3 at 2.17 m above the roof slab. It carries the high edge of `roof_south_east`. The posts stand on the roof slab level (z = 6.0) and are 0.075 m shorter than the rail top, like the knee-wall posts.
- Rail heights above the roof slab: `slant` 0.439 m. The posts are 0.075 m shorter. The runs with rafter posts have no rail; their posts stop at the rafter underside: 0.149 m for `north_west` and `north_east` (0.160 m for the hip post), 0.067 m for `west`.
- The posts of `west` at y = 5.25 and 6 are not on a column. Whether the roof beam along x = 0 carries them has not been checked in the model.
- Posts and rail are `RHS_75x75x3`, a light hollow section, not H or WF. The size is a placeholder until the roof loads are known.
- The set-back from the roof edge is the grid distance plus the 0.05 m overhang. Posts on beams are not detailed (no base plate or connection).
- Not generated yet: the diagonal hip members themselves. The hips are supported only at the points above.

## Rainwater

`tank_rain` is a 1.5 m tall rainwater tank in the north-west corner of the open ground-floor area, inside the brick walls
(x -0.4 to 1, y 3.2–4.45, kept 0.2 m clear of the septic tank to its south). It is modelled as a solid box, so the interior is not drawn. Its top is level with the stair landing's top (z = 1.5).
Below the first-floor room slab it is closed over; its southern 0.3 m (y 3.2–3.5) is under the open void.

The gutters form a network that drains to one downpipe, so the lowest point of a gutter need not be at its end:

- `pipe_collect` (a `GUTTER`, 100 mm): collects the run-off from the north-west. It runs from (-0.53, 7) south along the west edge to y = 3.48, then east to x = 3. It is lowest in the middle, at (0, 3.48, 5.85), and drains towards the downpipe from both ends.
- `pipe_stairs` (a gutter, 100 mm): collects from `roof_stairs_1` and `roof_stairs_2`, from (3, 3) west to (0, 3) and from (0, 1) north to (0, 3), draining to the downpipe at (0, 3, 7.3).
- `pipe_feed`: the 200 mm downpipe from (0, 3, 7.3), past the low point of `pipe_collect`, to the tank at z = 1.5. Normal rain goes this way. The diameters of the downpipe and overflow are provisional.
- `pipe_overflow`: a 200 mm pipe at z = 1.3 from the tank's south face, along x = -0.1 and out to y = -0.3.

The pipes and the gutter are solid round pipes, and the gutter stands in for an open one (its type is `GUTTER`).

## Septic tank

`septic_tank` (`septic_tanks` in `spec.json`) is a buried reinforced-concrete tank in the open ground-floor area, west of the stair. Its outer footprint is x −0.2 to 1.2, y 0.3 to 3.0 (2.7 × 1.4 m), with the long side along y.

| Part | Size |
|---|---|
| Chambers, south to north | 1.0 / 0.5 / 0.5 m clear (2:1:1); inner 2.0 × 1.0 × 1.5 m |
| Outer walls / partitions | 0.2 m / 0.15 m |
| Base slab | 0.2 m, top at z −0.6 |
| Cover slab | 0.15 m, z 0.9 to 1.05 |

- The outer length is 0.2 + 1.0 + 0.15 + 0.5 + 0.15 + 0.5 + 0.2 = 2.7 m; the generator fails if `outer` and these parts disagree. The inner dimensions come first, the walls and reinforcement are added around them.
- Position: the north face at y = 3.0 is exactly 1.5 m from the (0, 4.5) column, which is what fixes it; the (3, 2) and (3, 0) columns are 1.80 and 1.82 m away. `tank_rain` starts at y 3.2 to clear it.
- Depth: the inner floor is 0.6 m below ground and the cover top 1.05 m above it, leaving about 0.35 m under the stair landing (z 1.4).
- It is one `IfcTank` with no shape of its own; the walls and slabs aggregate into it. Their types carry a `Custom_SepticTank` property set: K-250 concrete (f'c 21 MPa), 50 mm inner and 30 mm outer cover, coal tar epoxy or bitumen coating in 3 coats, PPC / high-sulfate-resistance cement, double-layer deformed bar D10 at 150 mm at most, status Candidate. `Custom_SepticLayout` on the tank records the derived depths.
- The solid flight of `stair_1` stands against the east wall, which then acts as a retaining wall: it has to be checked for fill pressure with the tank empty and for liquid pressure with it full.

Not yet modelled, with the intent:
- Cover slope: about 2 % (28 mm across the width), falling away from the house so water does not pool. The cover is flat; unequal wall heights are the simple way to model it.
- Control hole, at least 40 cm across, in the south chamber (y 0.5–1.5), for instance y 0.55–0.95, so it lies south of the landing (which starts at y = 1) and needs no hinged panel. Use a solid gas-tight lid on a collar, not a grate, which would vent gas and odour.
- Landing grate: serrated steel, bearing bars at least 3×25 mm, pitch 30×100 mm (or tighter, 20×50), hot-dip galvanized, removable saddle clips.
- Vent pipe for the methane, straight up along the column that carries the stair.
- Toilet drains (prototype, `pipe_toilet_1` and `pipe_toilet_2`, 100 mm): the seats stand at (4.5, -0.3) and (3.5, -0.3), z 3.0. Each drops straight down with no s-trap. The bath drain falls from 2.6 to 2.5 along y = -0.3 and joins the toilet drain at (3.5, -0.3, 2.5). That runs north to y = 1.3, almost level (2.45) so it clears the 2.1 m garage door, then west at y = 1.3 with a steep fall of 1.65 m over 2.6 m (about 32°) to the south chamber, ending at (0.9, 1.3, 0.8): 0.1 m inside the east wall's inner face, with its crown just under the cover. Maximising the fall is deliberate; a slope that steep may leave solids behind and may need easing. Still open: the trap, vent and the openings through the walls.
- Openings in the partitions between chambers.

## Open points

Septic tank
- The landing (x 0–1, y 1–3) lies wholly over the tank. The tank walls should not carry it: they are liquid-retaining members, would tie the stair's settlement to the tank's, and are attacked by sulfide from inside. It needs independent steel supports on their own footings: the west edge bearing on the ground brick wall at x = −0.5 (if that wall is load-bearing), and the east edge on the solid flight, which means extending the landing to about x 1.3. The `stair_2` landing, at z 4.4 directly above, needs a route to the ground too. A structural engineer has to check all of it.
- The eighth tread of `stair_1`'s first flight is a plate cantilevering over the tank's wall and cover. The last tread top (z 1.2) and the landing top (z 1.5) are further apart than the riser limit; this predates the tank but matters once the landing height is settled against the tank top.
- The fill stops 0.05 m short of the tank wall; shifting the flight start 0.05 m west closes it.

Structure
- Roof level has only the knee-wall posts and rails. The x = 3 wall needs a steel ring beam on top, tied down to the columns, and the
  roof needs rafters and purlins. The knee walls need more supports (see Knee walls) and a check of the section.
- With the roof 0.5 m lower, the door at the stair top has only 0.07 m of lintel above its 2.1 m opening; the wall needs a header or the door a lower height.
- Wind uplift is the main risk for a light roof this high up and open on the void side. The tie-down from panel to purlin to rafter to ring
  beam to column has to be designed and checked by a structural engineer, using the SNI wind loads for the site.
- The edges facing the void have no wall or guard rail.

Openings
- The door leaf at the stair top is not modelled, only the opening. The posts and header around it come from the steel frame.
- The pipes through the brick walls (`pipe_feed`, `pipe_overflow`) and the toilet drain through the septic tank's east wall have no openings cut in them.

Water
- Gutters exist only over the north-west and the stair roofs. The main roof's north and east eaves have none, and `roof_bath`
  still sheds water west into the void, onto the stair.
- The tank needs a lid or screen at its southern end (y 3.2–3.5), which is open to the void.
- With the roof and walls closed, the grate floor under them stays dry apart from wind-driven rain through the stair door (sill and door seals).

## `spec.json` reference

- `slabs`: `id`, `storey`, `name`, `type` (`floor_80`, `floor_100` or `floor_200`), `polygon`, optional `material` (`lean_concrete`, `lean_concrete_tiled`, `diamond_plate`, `steel_deck` or `tbd`), optional `steel_grate`, optional `z`.
- `rooms`: walls built around an outline. Walls shared between rooms are merged into one run.
  - `rect`: `[x0, y0, x1, y1]`, or `polygon`: an axis-aligned outline given as a point list.
  - `wall`: `brick` or `aac` (`sandwich` and `polycarbonate` also exist, used on the roof).
  - `doors`: `{side, from, to}` with `side` one of `north`, `south`, `east`, `west`, and `from`/`to` the span along that
    edge. For a `polygon`, `side` is the direction the edge faces and the door goes on the edge that contains its span.
    Default height is 2.1 m, with a lintel above.
  - `open`: `{side, from, to}`; that stretch of the edge gets no wall. Needed on both rooms that share the edge.
- `roofs`: one entry per roof, each its own `IfcRoof` with one sloped panel: `id`, `storey`, `corners` (3 or 4 points `[x, y, z]`, z = rise above the eaves; a fourth point must lie in the plane of the first three), optional `panel` (`metal`, `polycarbonate`, `spandek_insulated` or `spandek_transparent`), `cladding` (`[{panel, width}]`, strips across y from the south edge, widths adding up to the span), `frame` (`rafter` and `purlin`, each `{width, depth, thickness}`; rafter also `lines` (coordinate across the slope of the first rafter, the last and any fixed rafter between; ascending) and `max_pitch`, purlin `max_spacing` and `inset`; optional `join_y` (a line shared with the next roof's frame, where purlins run on and merge) and `hip` (`{edge, laid_by}`: a diagonal rafter under that edge; `laid_by` is a roof id that has already laid it); the roof must fall along x only or y only, either way), `wall` (`brick`, `aac`, `sandwich` or `polycarbonate`; the default type of the roof's walls), `wall_height` (raises the eaves), `parapet` (edge numbers that get a wall of `wall_height`), `edge_walls` (per edge number, opt-in: `{wall, doors}` overrides the type or adds `{from, to}` openings, `true` for the roof's own wall type; an edge not listed has no wall).
- `knee_walls`: `storey`, `columns` (the storey whose columns carry the posts), `section` (`width`, `depth`, `thickness` of the hollow section) and `supports` and `runs`: `{id, axis, at, from, to, roofs, on_beam, tall_posts}`, a line `axis` = `x` or `y` at coordinate `at`, between `from` and `to`, under the listed roofs. `rafter_posts` is a roof id: no rail, a post under each of that roof's rafters on the line (axis y for a roof that falls along x, axis x for one that falls along y). `on_beam` is an optional list of `[x, y]` points on the line where a post stands on a beam; `tall_posts` an optional list of `[x, y, height]` that overrides a post's height. The generator fails if the roof is not level along a run. `supports` is a list of `{id, axis: "y", at, from, to, height}`: a post at each end and a rail across the tops at `height` above the storey floor.
- `walls`: loose wall runs, `{storey, from, to, wall}`.
- `tanks`: `id`, `storey`, `name`, `rect`, `height`, optional `z`.
- `septic_tanks`: `id`, `storey`, `name`, `outer` (`[x0, y0, x1, y1]` to the outer faces), `wall`, `partition`, `base`, `cover` (thicknesses), `chambers` (clear lengths along y, south to north), `floor_z` (top of the base slab), `inner_height`, optional `description`. The outer length must equal the walls, chambers and partitions added up.
- `pipes`: `id`, `storey`, `name`, `diameter`, `path` (a list of `[x, y, z]` points; each straight stretch becomes a pipe segment).
- `beams`: one block or a list of blocks (one per storey): `storey`, `main` and `secondary` (`{axis, at, spans}`), optional `sections` (`main` / `secondary`: `WF_200x100`, `WF_150x75`, `WF_125x60` or `WF_100x50`).
- `columns`: groups of `{storey, at, rotation}`; `rotation` 90 turns the H section so its flanges face x.
- `stairs`: see `spec.json`. A flight may set `solid`: the number of treads, counted from its start, packed solid from the flight's start level up.

Room `name` is a label only; it doesn't reach the generated file.

## Roof rework

Pilot on `roof_south_east`: spandek cladding on a rafter and purlin frame. `roof_east`, `roof_north_east`, `roof_north_west` and `roof_west` follow it, for now all insulated spandek with no transparent strips (no `cladding`, so one panel). The remaining roofs (`roof_slant`, `roof_west_3`, the stair and bath roofs) are still polycarbonate.

**Cladding** (`cladding` on the roof): strips side by side across y, each running the full slope (about 4.6 m, so a single sheet of 5 m or more, cut to length). Every sheet is 1 m effective width, so the 0.5 m strips are half-sheets.

| y (m) | Strip | Sheet |
|---|---|---|
| 0 – 0.5 | insulated | Spandek insulated 0.35 mm |
| 0.5 – 1.5 | transparent | Spandek PET 1.2 mm, 100 cm effective |
| 1.5 – 2.0 | insulated | as above |
| 2.0 – 3.0 | transparent | as above |
| 3.0 – 3.5 | insulated | as above |

The 0.75 m variant (0.5 – 0.75 – 1 – 0.75 – 0.5) was dropped: it would cut two transparent sheets and waste 0.25 m of each. Each panel is modelled 30 mm thick, the wave height, and rests on the purlins.

**Frame** (`frame` on the roof), stacked from the top: panel, purlin, rafter, knee-wall rail.

| Member | Section | Layout |
|---|---|---|
| Rafter | RHS 50×100×2.3 | Down the slope (along x on `roof_south_east` and `roof_east`; along y on the north roofs; the roof may fall either way), from x = 3.05 to the eave at x = 7.05. `lines` fixes the start, the end and any rafter that must stay put (the edges of the stair door); each gap between two lines is split into equal spaces no wider than `max_pitch` (1 m), the way a stair's treads are. `lines` are coordinates across the slope. `roof_south_east`: lines 0.1, 1, 2, 3.5, so rafters at y = 0.1, 1, 2, 2.75 and 3.5. |
| Purlin | RHS 40×60×2.3 | Across the slope (along y), starting 0.05 from the south edge. Seven lines, evenly from x = 3.05 to 7.0, 0.76 m apart along the slope (limit 0.875 m). |

- **`roof_east` and `roof_south_east` share the y = 3.5 line.** The rafter on it (`roof_east_rafter_0`) belongs to both: the second roof sees it is already laid and skips it. Both roofs have `join_y: 3.5`, so a purlin runs on to that line without the 0.05 m stop, and the two halves are merged into one member across it (the merged purlin keeps the id of the south half, `roof_south_east_purlin_N`).
- **`roof_east` is a triangle.** Its `lines` are 3.5 (the shared rafter) and 6.13, where the hip crosses x = 6, so rafters at y = 3.5, 4.377, 5.253 and 6.13 (0.877 m apart). Each starts 0.05 m inside the hip and runs to the eave; the last is 1.13 m long. The `hip` (`edge` 2, from the peak to the corner (7.05, 7.05)) gets a diagonal rafter, `roof_east_rafter_hip`, 5.73 m long, the same section as the other rafters and its top level with theirs. The purlins end on it instead of stopping 0.05 m short, so they rest on it. It also gets a post at x = 6 (on the hip beam), under its underside.
- **The north and west roofs** are triangles framed the same way, with the rafters under the slope's fall line.
  - `roof_north_east`: rafters along y at x = 3, 4, 5, 6 (`lines` 3, 6), the first along the x = 3 edge from y = 3.5 to the eave. Purlins run along x and stop on the hip. The hip rafter belongs to `roof_east` (`hip.laid_by`).
  - `roof_north_west`: rafters at x = 1, 2, 3 (`lines` 1, 3). It lays the hip rafter (3 to the corner at (-0.55, 7.05)), 4.58 m long.
  - `roof_west`: falls towards -x, so its rafters run from x = 3 down to the eave. `lines` 4.5, 6, so rafters at y = 4.5, 5.25 and 6, the first along the y = 4.5 edge. Its hip is `roof_north_west`'s (`laid_by`).
  - A hip's `laid_by` names the roof that has already laid the diagonal; the second roof's purlins still stop on it.
- Rafters are inclined and square to the slope; purlins are level, so their top touches the panel plane to within a few mm. Sections are placeholders until the roof loads are checked.
- The rafters rest on the `east_se` knee-wall posts at x = 6 and overhang them by 1.05 m (plan) to the eave.
- **Knee wall.** `east_se` has no rail, only a post under each rafter at x = 6 (`rafter_posts` on the run), five 75×75 posts (at y = 0.1, 1, 2, 2.75, 3.5) up to the rafter's underside at z = 6.381 (0.381 m above the roof slab; 0.182 m below the old rail top). They stand on the roof beam along x = 6 and on the column at (6, 2); the one at y = 0.1 stands beside the taller `bath` post at (6, 0). `east` now carries only `roof_east`, from (6, 4.5) to the hip.

**Open**
- The high ends of the north and west rafters (at the x = 3 edge, or y = 4.5 for `roof_west`) have no support yet either; they need the same ring beam. The posts at y = 6.5 are under the low ends only.
- The high ends of the rafters (x = 3.05) have no support yet: they need the ring beam on the x = 3 wall. The 2.17 m post at the (3, 0) column (the `bath` run's `tall_posts`) is the natural place to start it.
- `roof_east`: the high ends of its rafters and of the hip rafter (x = 3.05) are unsupported, like those of `roof_south_east`. Its rafters at y = 4.377 and 5.253 and the hip rafter rest on posts at x = 6; the last rafter (y = 6.13) starts at the hip just east of x = 6, so it has no post of its own and is held by the hip rafter and the purlins.
- The 1.05 m eave overhang, the stair-door opening (y 1–2, with the rafters at y = 1 and 2 on its edges), and the fixings (clips, screws, sealing of laps) are not designed.
- Spandek spans and fixing patterns are from the sheet data below, not checked against the supplier's span table.
- The hip rafters are all laid with the depth of the roof that owns them; the purlin ends that rest on a hip of the neighbouring roof can be a few mm off its top. Not checked in a viewer.
- Next: the remaining polycarbonate roofs, once these are reviewed.

Sheet data (also in `GLOSSARY.md`):
- Maxlite spandek transparan: effective width 77 cm or 1 m, 0.80 mm, lengths 1–6 m, Rp120,000–290,000 (Shopee).
- Spandek bening PET 1.2 mm: width 107 cm, effective 100 cm, wave pitch 15 cm, wave width 10 cm, wave height 3 cm, from 3 m long, Rp92,500 (Shopee).
- Spandek insulasi 0.35 mm: width 1 m, lengths 3–6 m, 2 mm insulation (bubble foil), Rp110,000 (Tokopedia).

## stairs support

### Mendefinisikan koneksi fisik antara Balok/Pelat Lantai dengan Tangga
```
ifcfile.createIfcRelConnectsElements(
    GlobalId=ifc_utils.create_guid(),
    OwnerHistory=owner_history,
    Name="Tumpuan Tangga",
    Description="Hubungan tumpuan struktural antara pelat lantai dan tangga",
    ConnectionGeometry=None, # Bisa diisi dengan IfcConnectionCurveGeometry jika detail
    RelatingElement=slab_atau_beam_penopang,
    RelatedElement=stair_flight_anda
)
```

• IfcStructuralPointSupport: Digunakan jika tumpuan tangga bertumpu pada titik tertentu (misalnya ujung kolom atau anchor bolt spesifik).
• IfcStructuralCurveSupport: Digunakan jika tangga bertumpu sepanjang garis balok penopang atau bordes (landing).

Anda dapat menambahkan logika relasi tumpuan di dalam fungsi kontainer tangga (build_stair) atau setelah objek IfcStairFlight terbentuk. 
```
def build_stair(scene, node, placement):
    """Container only: its flights and landings aggregate into it."""
    model = scene.model
    stair_container = _product(scene, node, placement)
    
    # KODE TAMBAHAN UNTUK MENDEFINISIKAN TUMPUAN (SUPPORTS)
    # Memeriksa apakah node data input mendefinisikan ID dari slab penopangnya
    if "SupportedBy" in node:
        for support_id in node["SupportedBy"]:
            # Mengambil referensi entity slab/penopang dari scene data Anda
            if support_id in scene.entities:
                supporting_element = scene.entities[support_id]
                
                # Membuat relasi tumpuan struktural/koneksi fisik di IFC
                model.create_entity(
                    "IfcRelConnectsElements",
                    GlobalId=guid_for(f"{node['id']}_support_{support_id}"),
                    Name="Stair Structural Support Connection",
                    Description="Mendefinisikan tumpuan tangga pada struktur utama bangunan",
                    RelatingElement=supporting_element,  # Elemen yang menopang (Slab/Beam)
                    RelatedElement=stair_container      # Elemen yang ditopang (Tangga)
                )
                
    return stair_container
```

### Contoh representasi node input tangga di file data Anda
```
stair_node = {
    "id": "stair_01",
    "type": "IfcStair",
    "Name": "Tangga Utama Blok A",
    "PredefinedType": "STRAIGHT_RUN_STAIR",
    "SupportedBy": ["slab_lantai_1", "slab_lantai_2"] # ID pelat beton bawah & atas
}
```
