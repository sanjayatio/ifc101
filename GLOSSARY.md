# Glossary

Basic building terms as used in this repo's `design.ifcjson` / `spec.json` files.
Dimensions in metres unless noted.

## Structure

| Term | Meaning |
|---|---|
| **Column** | Vertical member carrying load down to the ground. Here: H 150×150 (`IfcColumn`). |
| **Beam** | Horizontal member carrying floor or wall load sideways to columns (`IfcBeam`). |
| **Main beam / girder** | The larger beam that other beams frame into. Here: WF 200×100, running along Y. |
| **Secondary beam / joist** | The smaller beam spanning between main beams, carrying the floor directly. Here: WF 150×75, running along X. |
| **H-beam** | Steel section whose flange width is about equal to its depth (150×150). Stocky, so it suits columns. |
| **WF (wide-flange) / I-beam** | Steel section deeper than it is wide (200×100, 150×75). Efficient in bending along its depth, so it suits beams. |
| **Flange** | The two wide plates at the top and bottom of an I or H section. They carry most of the bending. |
| **Web** | The thin plate joining the two flanges. It carries shear. |
| **Support** | Whatever a member rests on or attaches to. A beam is supported by columns or by a larger beam. |
| **Connection** | How a member attaches to its support. *Bearing:* it sits on top. *Side/butt:* it ends against the support's face, which is the current model (beams end on the column face, or on the web of a main beam). |
| **Span** | Clear distance between two supports. |
| **Cantilever** | A member or floor projecting past its last support, held at one end only. Here: the toilet, and the first-floor room. |
| **Load-bearing wall** | A wall that carries the floor or roof above it, not only its own weight. Ground-floor red brick is load-bearing. |
| **Non-load-bearing wall** | A partition or infill wall that only carries itself. First-floor AAC walls are non-load-bearing. |
| **Lintel** | The wall piece above a door or window opening. |
| **Slab** | Flat floor plate (`IfcSlab`). *Slab on grade* is cast directly on the ground. |
| **Storey / elevation** | A floor level, and its height above the ground floor datum (`IfcBuildingStorey`). |

## Roof

| Term | Meaning |
|---|---|
| **Roof deck** | The floor under the roof (`slab_roof`), reached by the stair. |
| **Pitch** | The roof slope, as an angle from horizontal. Here 28° to 32°, set by each roof's corners. |
| **Eave** | The lower edge of a roof slope, where water runs off. Here at z = 6.5, on top of the roof walls. |
| **Ridge / peak** | The top line where two slopes meet. Here the corner shared by `roof_north_east`, `roof_east` and `roof_south_east`, at (3, 3.5). |
| **Hip roof** | A roof that slopes down on all sides, so its ends are sloped too. |
| **Gable** | The vertical, triangular end wall under a roof's slopes. None in this design: the triangular gap under each slope is closed by an infill wall. |
| **Lean-to / shed roof** | A roof with a single slope, leaning against a taller wall. Here `roof_south_east` (high on the west, over the stair landing) `roof_bath` (over the toilet and bathroom strip) and `roof_slant` (over the cantilevered room). |
| **Hip end** | A sloped end of a roof, in place of a gable. Here the triangles `roof_north_east`, `roof_north_west`, `roof_west` and `roof_east`. |
| **Parapet** | A short wall at the roof edge that the eaves sit on. It raises the eaves, so adds headroom. Supported by the generator (`parapet`), not used in the 7x7 design. |
| **Knee wall** | A short support set back from the eaves that the roof slope rests on, with the roof overhanging past it. Here light posts, on the columns or on a roof beam at a hip, usually tied by a rail (`knee_walls`), not a solid wall. Under `roof_south_east` there is no rail: one post under each rafter. |
| **Infill wall** | A wall that closes the gap between a structure and a sloped roof edge. It carries only itself. |
| **Overhang** | Roof projecting past its last support. It has a long lever arm against wind suction, so the roof is cut at x = 3 to avoid one. |
| **Uplift** | Upward wind suction on a roof. An open or lightweight roof can be torn off, so every connection has to hold it down. |
| **Ring beam** | A continuous beam around the top of the walls that ties the roof to the columns. Not yet modelled. |
| **Rafter / purlin** | Rafters run up the slope and carry purlins, which run across it and carry the roof panels. Modelled on `roof_south_east` only (`frame`): rafters 1 m apart on the knee-wall rail, purlins at most 0.875 m apart on the rafters, then the panels. |
| **Gutter / downpipe** | They collect rain at the eave and lead it away. Not yet modelled. |
| **Header** | The member over a door opening, joining the posts on either side. |
| **Door post** | The steel post at each side of an opening. The door hangs from it. |
| **Steel frame** | The structure of a roof wall. A sheet of polycarbonate can't hold a door or wind loads, so the frame does it. |
| **Infill (panel)** | The sheet material between frame members. It is not structural. |

## Rainwater

| Term | Meaning |
|---|---|
| **Catchment tank** | A tank that collects water from the roof (`IfcTank`). Here a 1.5 m box in the north-west corner, level with the landing. |
| **Downpipe** | The vertical pipe that carries water from a gutter down to the tank. |
| **Overflow** | The outlet that lets surplus water out once the tank is full. Here a pipe at z = 1.2 m, so the tank holds about 1.6 m³ below it. |
| **Invert** | The inside bottom of a pipe. Water in the tank can rise to the overflow's invert before it leaves. |
| **Penetration** | A pipe passing through a wall. It needs an opening cut in the wall, which this model doesn't draw yet. |

## Stairs

| Term | Meaning |
|---|---|
| **Flight** | An uninterrupted run of steps between two levels (`IfcStairFlight`). |
| **Landing** | A flat platform between flights, where a U-shaped stair turns. |
| **U-shaped stair** | Two parallel flights joined by a landing, turning 180°. |
| **Rise** | Total vertical height a flight climbs. |
| **Run** | Total horizontal length of a flight. |
| **Riser** | The vertical face of one step. Its height must stay between 0.15 and 0.18 m here, and the generator picks the riser count to fit. |
| **Tread** | The horizontal surface of one step. A flight has one fewer tread than risers, because the top step is the floor. |
| **Going** | Horizontal depth of one tread. |
| **Stringer** | The inclined beam that carries the treads. |
| **Slope** | Rise ÷ run, usually quoted as an angle (about 33° is the reference design). |

## Materials

| Material | Status | Notes |
|---|---|---|
| **KalsiFloor** (fibre cement board) | Rejected | Brittle: it cracks or breaks suddenly instead of bending like a metal plate. |
| **Diamond steel plate** (checker plate) | Decided | Solid slab for the roof-level cover and room slabs, chosen for privacy. Raised pattern gives grip. It can rust if water is trapped on it, e.g. under carpet. |
| **Packed dirt** | Decided | Cheap ground slab for the garage. |
| **Raised tile** | Decided | Tile on pedestals for the `slab_watch` floor; the gap lets water drain below. |
| **Waterproofed steel deck** | Decided | Toilet and bath slabs. Steel plate with a sealed waterproof membrane; lighter than concrete, which matters on the toilet cantilever. |
| **Steel grate** | Decided | Floor base for upper storeys. Secondary overlay panels go on top. |
| **Red brick** | Decided | Ground-floor walls. They are load-bearing. Heavy, with a density of about 1,600–2,000 kg/m³. |
| **AAC** (aerated autoclaved concrete, "Hebel") | Candidate | Upper-storey walls. Light, with a density of about 550–750 kg/m³, so about 3× lighter than red brick. Not a natural fit for load-bearing walls, so it is used as infill only. |
| **Spandek** | Roof option; piloted on `roof_south_east` | Trapezoidal metal roof sheet. Blocks light and amplifies the sound of rainfall unless insulated. |
| **Spandek insulated** (0.35 mm, bubble foil) | Piloted | 1 m wide, lengths 3–6 m, steel 0.35 mm with 2 mm insulation. Rp110,000 per sheet (Tokopedia, sjbsteel). |
| **Spandek transparent, PET 1.2 mm** | Piloted | Clear sheet 107 cm wide, 100 cm effective; wave pitch 15 cm, wave width 10 cm, height 3 cm; from 3 m long. Rp92,500 (Shopee). |
| **Maxlite spandek transparan** | Alternative | 0.80 mm, effective width 77 cm or 1 m, lengths 1, 2, 2.5, 3, 4, 5, 6 m, fits the old Majadeck 770 profile. Rp120,000–290,000 (Shopee). |
| **Polycarbonate** | Preferred roof idea | Translucent, so sunlight passes through. Hollow multiwall panels reduce rain noise. It needs more framing than spandek, so it may not be lighter overall. Wind resistance at 5.5 m or more above ground is the open concern. Not structural: also used, in a steel frame, for the roof's gable and the x = 3 wall (about 2 kg/m², and it expands 2–3 mm per metre with temperature). |
| **Steel sandwich panel** | Candidate | Roof-level walls (parapets, infill). Steel sheets on both faces around an insulating core (PU or rockwool), about 10–15 kg/m² against 55–75 kg/m² for 100 mm AAC. Lighter, but its weight does no work against uplift, so it has to be bolted down. |
| **Light steel frame** | Candidate | Frames the roof walls and carries the door. Doubles as the ring beam. |
| **Fiberglass** | Roof option | Translucent corrugated or flat sheet. It lets light through, but no project decision or test result is recorded yet. |

## Orientation of steel sections in this model

A column's flanges are the two plates facing ±Y, and its web lies in the X=const plane along Y. Y-direction beams therefore meet a *flange face*, which is a strong, continuous plate. X-direction beams meet the *open side* between the flanges, so they would normally connect to the web with a shear tab.
