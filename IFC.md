# ifcjson: IFC nodes reference (IFC4 / ISO 16739-1)

An `.ifcjson` document is a flat list of nodes under `data`. Each node is one IFC entity, and the generator turns the list into an IFC4 model.

**Legend:** **M** = mandatory, **O** = optional. For IFC attributes, M/O is the cardinality in the IFC4 schema. For keys that are not IFC attributes (marked *JSON*), M/O is what the generator requires.

## 1. Conventions

| Key | M/O | Meaning |
|---|---|---|
| `id` | **M** (*JSON*) | Local key, unique in the document. Other nodes refer to it. The generator derives a stable `GlobalId` from it, so regenerating keeps each element's identity. |
| `type` | **M** (*JSON*) | IFC entity name, e.g. `IfcWall`. |
| `Name` | O | Human label. Omit it when it would only repeat the `id` or the type. |
| `Description` | O | Free text. |
| `PredefinedType` | O (**M** on `*Type` nodes) | Sub-classification enum. An occurrence takes it from its type, so only the type states it. |
| `Location` | O (default `[0,0,0]`) | `IfcAxis2Placement3D.Location` (x, y, z in metres). |
| `RefDirection` | O (default `[1,0,0]`) | `IfcAxis2Placement3D.RefDirection`, the local X axis. This is the rotation: `[0,1,0]` = 90°, `[0,-1,0]` = -90°. |

Relationship keys (all hold `id` references). A parent, type or property set must appear **earlier** in the document than the node that refers to it.

| Key | IFC relationship | M/O |
|---|---|---|
| `Decomposes` | `IfcRelAggregates` (the parent): project → site → building → storey; stair → flight / landing | **M** for site, building, storey, flight and landing; otherwise not used |
| `ContainedIn` | `IfcRelContainedInSpatialStructure` (a storey) | **M** for every element that is not the part of an aggregate |
| `IsTypedBy` | `IfcRelDefinesByType` | O in IFC (**M** for beams, columns, walls, slabs and stair flights, whose geometry comes from the type) |
| `HasPropertySets` | `IfcRelDefinesByProperties` on an occurrence, `IfcTypeObject.HasPropertySets` on a type | O |

An element is either `ContainedIn` a storey or `Decomposes` into a parent, never both. Aggregated parts follow their parent's placement.

**Where geometry lives**
- Shared by all occurrences, so on the **type**: beam and column profile, wall and slab layer thickness and material.
- Varies per occurrence, so on the **node**: placement, `Length` / `Height`, slab outline.

---

## 2. Spatial structure

| `type` | IFC attributes used | JSON keys |
|---|---|---|
| `IfcProject` | `Name` O | `id` **M**, `Name` O |
| `IfcSite` | `Name` O | `id` **M**, `Name` O, `Decomposes` **M** (project) |
| `IfcBuilding` | `Name` O | `id` **M**, `Name` O, `Decomposes` **M** (site) |
| `IfcBuildingStorey` | `Name` O, `Elevation` O | `id` **M**, `Name` O, `Elevation` O (metres above the building datum), `Decomposes` **M** (building) |

Units and geometric contexts are supplied by the IFC template (metres, degrees).

---

## 3. Property sets

`IfcPropertySet`

| Key | M/O | Meaning |
|---|---|---|
| `id` | **M** | |
| `Name` | O | `Pset_*` is reserved for sets defined by the standard (e.g. `Pset_WallCommon`). Project-specific sets use another prefix (this document uses `Custom_`). |
| `Description` | O | |
| `HasProperties` | **M** | Object of `name: value`. Each entry is an `IfcPropertySingleValue` (`Name` **M**, `NominalValue` O). JSON booleans, numbers and strings become `IfcBoolean`, `IfcReal` and `IfcLabel`. |

Any set is carried into the IFC model as given (for instance `Custom_WallFrame`, which describes the steel frame behind a polycarbonate wall). The generator also **reads** these two sets, so the properties are required where an element uses them:
- `Custom_Roof` (on an `IfcRoof`): `PanelMaterial_Default` (`metal` or `polycarbonate`), the material of the roof's panel.
- `Custom_StairFlight` (on an `IfcStairFlightType`): `Width`, `TreadThickness`, `RiserHeightMin`, `RiserHeightMax` (metres).

---

## 4. Types

All types: `id` **M**, `Name` O, `Description` O, `PredefinedType` **M**, `HasPropertySets` O.

| `type` | `PredefinedType` values used | Extra keys |
|---|---|---|
| `IfcBeamType` | `BEAM` (also `JOIST`, `LINTEL`, `T_BEAM`, ...) | `Profile` **M**, `Material` **M** |
| `IfcColumnType` | `COLUMN` (also `PILASTER`) | `Profile` **M**, `Material` **M** |
| `IfcWallType` | `STANDARD`, `ELEMENTEDWALL` (framed wall with infill; also `PARTITIONING`, `SHEAR`, `PARAPET`, ...) | `MaterialLayers` **M** |
| `IfcSlabType` | `FLOOR`, `LANDING` (also `ROOF`, `BASESLAB`) | `MaterialLayers` **M** |
| `IfcStairFlightType` | `STRAIGHT` (also `WINDER`, `SPIRAL`, `CURVED`) | none |

`Profile` (becomes an `IfcMaterialProfileSet` on the type): `IfcIShapeProfileDef` or `IfcRectangleHollowProfileDef`.

| Key | M/O |
|---|---|
| `type` = `IfcIShapeProfileDef` | **M** |
| `OverallWidth`, `OverallDepth`, `WebThickness`, `FlangeThickness` | **M** (metres) |

| Key | M/O |
|---|---|
| `type` = `IfcRectangleHollowProfileDef` | **M** |
| `XDim` (width), `YDim` (depth), `WallThickness` | **M** (metres) |

`MaterialLayers` (becomes an `IfcMaterialLayerSet`): a list of layers, outermost first.

| Key | M/O |
|---|---|
| `LayerThickness` | **M** (metres). The element thickness is the sum over layers. |
| `Material` | O (`IfcMaterialLayer.Material` is optional). A name; `Steel_Black` gets a surface style, any other name is a plain `IfcMaterial`. |

---

## 5. Occurrences

All of these take `id`, `type`, `Name`, `Location`, `RefDirection`, `Decomposes` / `ContainedIn`, `IsTypedBy`, `HasPropertySets` as in section 1. Only the extra keys are listed.

| `type` | Extra keys | Notes |
|---|---|---|
| `IfcWall` | `Length` **M**, `Height` **M**, `Outline` O (*JSON*) | Thickness comes from the type's layers. `Location` is the start of the wall's centreline, running `Length` along local X. `Outline` is a closed polygon `[[u, z], ...]` in the wall's own plane (u along the wall, z up from `Location.z`) that replaces the rectangle, for gable ends and infill under sloped roofs. |
| `IfcSlab` | `OuterCurve` **M** | Closed polyline `[[x, y], ...]` (the first point is repeated automatically). Thickness comes from the type. `Location.z` is the slab underside. |
| `IfcBeam` | `Length` **M** | Section from the type. `Location` is the start of the underside centreline. |
| `IfcColumn` | `Length` **M** | Section from the type. `Location` is the centre of the base, extruded up. `RefDirection` `[0, 1, 0]` turns the section 90°. |
| `IfcRoof` | `OuterCurve` **M**, `HasPropertySets` **M** (`Custom_Roof`) | One sloped panel over 3 or 4 corners. `OuterCurve` is a list of `[x, y, z]` corners, where z is the rise above the eaves; a fourth corner must lie in the plane of the first three. `PredefinedType` `SHED_ROOF`. `Location.z` is the eave height. A roof that needs several slopes is several `IfcRoof`s sharing corners. |
| `IfcTank` | `OuterCurve` **M**, `Height` **M** (*JSON*) | `PredefinedType` `STORAGE`. A solid box extruded up from `Location.z`; the interior is not modelled. |
| `IfcPipeSegment` | `Direction` **M**, `Length` **M**, `Diameter` **M** (*JSON*) | `PredefinedType` `RIGIDSEGMENT` or `GUTTER` (a gutter is still drawn as a round pipe). A straight round pipe that starts at `Location` and runs `Length` along the unit vector `Direction`. |
| `IfcStair` | none | Container only (no geometry). `PredefinedType` e.g. `TWO_STRAIGHT_RUN_STAIR`. Its flights and landing slabs `Decomposes` into it. |
| `IfcStairFlight` | `Rise` **M**, `Run` **M** (*JSON*) | `Rise` is the total height gained, `Run` the horizontal length (metres). The generator derives the `IfcStairFlight` attributes `NumberOfRisers`, `NumberOfTreads`, `RiserHeight` and `TreadLength` from them: risers = `ceil(Rise / RiserHeightMax)` (fewest steps), `RiserHeight` = `Rise / risers`, treads = risers − 1, `TreadLength` = `Run / treads`. It fails if `RiserHeight` would fall below `RiserHeightMin`. `Width`, `TreadThickness`, `RiserHeightMin` and `RiserHeightMax` come from the type's `Custom_StairFlight`. `Location` is the centre of the flight's width at its lower start. The flight runs `NumberOfTreads × TreadLength` along `RefDirection`, and the width spreads equally to both sides. The top of the flight is at `Location.z + NumberOfRisers × RiserHeight`, which is where the next landing's top surface should be. |

`IfcSlab` landings use a type with `PredefinedType` `LANDING` and `Decomposes` the stair instead of being contained in a storey.
