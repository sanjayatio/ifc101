import argparse, json, math
from pathlib import Path

SPEC_NAME, OUTPUT_NAME = "spec.json", "design.ifcjson"
HEAD_KEYS = ("id", "type", "IsTypedBy", "ContainedIn", "Decomposes", "HasPropertySets", "PredefinedType")
ONE_LINE = {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcPropertySet"}

BEAM_SECTIONS = {"WF_200x100": ("beam_type_wf_200x100", "WF_200x100", 0.1, 0.2, 0.0055, 0.008),
                 "WF_150x75": ("beam_type_wf_150x75", "WF_150x75", 0.075, 0.15, 0.005, 0.007),
                 "WF_125x60": ("beam_type_wf_125x60", "WF_125x60", 0.06, 0.125, 0.006, 0.008),
                 "WF_100x50": ("beam_type_wf_100x50", "WF_100x50", 0.05, 0.1, 0.005, 0.007)}
DEFAULT_SECTIONS = {"main": "WF_200x100", "secondary": "WF_150x75"}
WALL_TYPES = {"brick": "wall_type_brick_100", "aac": "wall_type_aac_100", "sandwich": "wall_type_steel_sandwich_50",
              "polycarbonate": "wall_type_polycarbonate_framed"}
WALL_THICKNESS = {"brick": 0.1, "aac": 0.1, "sandwich": 0.05, "polycarbonate": 0.016}  # the sum of each type's layers
SLAB_TYPES = {"floor_100": "slab_type_floor_100", "floor_200": "slab_type_floor_200"}
# Slab finish key (`material` in spec.json) -> (IfcMaterial name, colour is set in ifc_components.STYLED_MATERIALS)
SLAB_MATERIALS = {"packed_dirt": "Packed Dirt", "raised_tile": "Raised Tile", "diamond_plate": "Diamond Steel Plate",
                  "steel_deck": "Waterproofed Steel Deck", "tbd": "TBD (diamond plate or other)"}
COLUMN_TYPE, COLUMN_SIZE = "column_type_hbeam_150x150", 0.15
KNEE_POST_TYPE, KNEE_RAIL_TYPE = "column_type_knee_post", "beam_type_knee_rail"
DOOR_HEIGHT = 2.1
SEPTIC_CONCRETE = "Reinforced Concrete K-250"


def r(v):
    return round(v, 5)


def slug(v):
    return str(v).replace(".", "_").replace("-", "m")


class Design:
    def __init__(self, spec):
        self.spec, self.nodes = spec, []
        self.height = spec["storey_height"]
        self.storeys = {name: {"id": f"storey_{name}", "elevation": r(i * self.height)} for i, name in enumerate(spec["storeys"])}

    def add(self, **node):
        self.nodes.append({k: v for k, v in node.items() if v is not None})

    def elevation(self, storey):
        return self.storeys[storey]["elevation"]

    def storey_id(self, storey):
        return self.storeys[storey]["id"]

    # ---- shared header: spatial tree, property sets, types ------------------------------
    def header(self):
        add = self.add
        add(id="project", type="IfcProject", Name=self.spec.get("name", "BIM_Exploration_Project"))
        add(id="site", type="IfcSite", Name="Project Site", Decomposes="project")
        add(id="building", type="IfcBuilding", Name="Main Building", Decomposes="site")
        for name, s in self.storeys.items():
            add(id=s["id"], type="IfcBuildingStorey", Name=f"{name.capitalize()} Floor", Elevation=s["elevation"], Decomposes="building")

        add(id="pset_wall_ground_common", type="IfcPropertySet", Name="Pset_WallCommon", HasProperties={"LoadBearing": True})
        add(id="pset_wall_ground_decision", type="IfcPropertySet", Name="Custom_Decision", HasProperties={"Status": "Decided"})
        add(id="pset_wall_first_common", type="IfcPropertySet", Name="Pset_WallCommon", HasProperties={"LoadBearing": False})
        add(id="pset_wall_first_decision", type="IfcPropertySet", Name="Custom_Decision", HasProperties={"Status": "Candidate"})
        add(id="pset_slab_steel", type="IfcPropertySet", Name="Custom_SlabDecision", Description="Steel grating layout for upper floors",
            HasProperties={"BaseStructure": "Steel Grate", "TopFinish": "Secondary overlay panels", "Status": "Decided",
                           "DiscardedMaterial": "KalsiFloor (brittle failure risk, rejected)"})
        add(id="pset_stair_flight", type="IfcPropertySet", Name="Custom_StairFlight",
            HasProperties={"Width": 1.0, "TreadThickness": 0.03, "RiserHeightMin": 0.15, "RiserHeightMax": 0.18})

        used = {BEAM_SECTIONS[name] for block in self.beam_blocks() for name in {**DEFAULT_SECTIONS, **block.get("sections", {})}.values()}
        for tid, name, width, depth, web, flange in sorted(used):
            add(id=tid, type="IfcBeamType", Name=name, PredefinedType="BEAM", Material="Steel_Black",
                Profile={"type": "IfcIShapeProfileDef", "OverallWidth": width, "OverallDepth": depth, "WebThickness": web, "FlangeThickness": flange})
        add(id=COLUMN_TYPE, type="IfcColumnType", Name="HBeam_150x150", PredefinedType="COLUMN", Material="Steel_Black",
            Profile={"type": "IfcIShapeProfileDef", "OverallWidth": 0.15, "OverallDepth": 0.15, "WebThickness": 0.007, "FlangeThickness": 0.01})
        knee = self.spec.get("knee_walls")
        if knee:
            s = knee["section"]
            profile = {"type": "IfcRectangleHollowProfileDef", "XDim": s["width"], "YDim": s["depth"], "WallThickness": s["thickness"]}
            name = "RHS_{}x{}x{}".format(*(round(s[k] * 1000) for k in ("width", "depth", "thickness")))
            description = "Light hollow section for the knee wall under the roof edge; carries the roof ribbing, not a primary frame"
            add(id=KNEE_POST_TYPE, type="IfcColumnType", Name=name, Description=description, PredefinedType="COLUMN", Material="Steel_Black", Profile=profile)
            add(id=KNEE_RAIL_TYPE, type="IfcBeamType", Name=name, Description=description, PredefinedType="BEAM", Material="Steel_Black", Profile=profile)
        for roof in self.spec.get("roofs", []):
            for kind, s in (roof.get("frame") or {}).items():
                profile = {"type": "IfcRectangleHollowProfileDef", "XDim": s["width"], "YDim": s["depth"], "WallThickness": s["thickness"]}
                name = "RHS_{}x{}x{:g}".format(round(s["width"] * 1000), round(s["depth"] * 1000), round(s["thickness"] * 1000, 1))
                add(id=f"beam_type_{kind}_{roof['id']}", type="IfcBeamType", Name=name, PredefinedType="BEAM", Material="Steel_Black", Profile=profile,
                    Description=f"{kind.capitalize()} of {roof['id']}: light hollow section, size is a placeholder until the roof loads are checked")
        add(id="wall_type_brick_100", type="IfcWallType", Name="RedBrick_100", PredefinedType="STANDARD",
            Description="Ground floor load-bearing red brick masonry", MaterialLayers=[{"Material": "Red Brick", "LayerThickness": 0.1}],
            HasPropertySets=["pset_wall_ground_common", "pset_wall_ground_decision"])
        add(id="wall_type_aac_100", type="IfcWallType", Name="AAC_100", PredefinedType="STANDARD",
            Description="Lightweight AAC blocks to reduce structural load on upper level",
            MaterialLayers=[{"Material": "Autoclaved Aerated Concrete (AAC)", "LayerThickness": 0.1}],
            HasPropertySets=["pset_wall_first_common", "pset_wall_first_decision"])
        add(id="pset_wall_polycarbonate_frame", type="IfcPropertySet", Name="Custom_WallFrame",
            Description="The steel frame carries the load; the polycarbonate sheet is infill only and cannot hold a door",
            HasProperties={"Frame": "Steel RHS 50x50", "PostSpacingMax": 1.0, "Infill": "Polycarbonate multiwall, 16 mm",
                           "OpeningFrame": "Steel posts either side of an opening, header above, bolted to the slab and columns",
                           "JointGap": "Sealed channels; polycarbonate moves 2-3 mm per metre with temperature"})
        add(id="wall_type_steel_sandwich_50", type="IfcWallType", Name="SteelSandwich_50", PredefinedType="STANDARD",
            Description="Insulated steel sandwich panel on a light steel frame; light walls at roof level",
            MaterialLayers=[{"Material": "Steel Sheet", "LayerThickness": 0.0005}, {"Material": "PU Insulation Core", "LayerThickness": 0.049},
                            {"Material": "Steel Sheet", "LayerThickness": 0.0005}])
        add(id="wall_type_polycarbonate_framed", type="IfcWallType", Name="PolycarbonateFramed_16", PredefinedType="ELEMENTEDWALL",
            Description="Steel-framed wall glazed with polycarbonate, so daylight reaches the roof deck",
            MaterialLayers=[{"Material": "Polycarbonate Multiwall", "LayerThickness": 0.016}], HasPropertySets=["pset_wall_polycarbonate_frame"])
        self.septic_types()
        self.slab_material_types()
        add(id="slab_type_floor_100", type="IfcSlabType", Name="Floor_100", PredefinedType="FLOOR", MaterialLayers=[{"LayerThickness": 0.1}])
        add(id="slab_type_floor_200", type="IfcSlabType", Name="Floor_200", PredefinedType="FLOOR", MaterialLayers=[{"LayerThickness": 0.2}])
        add(id="slab_type_landing_100", type="IfcSlabType", Name="Landing_100", PredefinedType="LANDING", MaterialLayers=[{"LayerThickness": 0.1}])
        add(id="stair_flight_type_steel", type="IfcStairFlightType", Name="SteelFlight", PredefinedType="STRAIGHT", HasPropertySets=["pset_stair_flight"])

    def slab_material_types(self):
        """One slab type per (thickness, material) pair used by a slab's `material`; slabs without one keep the plain floor types."""
        used = sorted({(s.get("type", "floor_100"), s["material"]) for s in self.spec.get("slabs", []) if "material" in s})
        for kind, material in used:
            self.add(id=self.slab_material_type(kind, material), type="IfcSlabType", Name=f"{kind.capitalize()}_{material}", PredefinedType="FLOOR",
                     MaterialLayers=[{"Material": SLAB_MATERIALS[material], "LayerThickness": 0.2 if kind == "floor_200" else 0.1}])

    @staticmethod
    def slab_material_type(kind, material):
        return f"slab_type_{kind}_{material}"

    def septic_types(self):
        """Concrete wall and slab types for every septic tank, one per thickness, sharing the corrosion-protection property set."""
        tanks = self.spec.get("septic_tanks", [])
        if not tanks:
            return
        self.add(id="pset_septic_concrete", type="IfcPropertySet", Name="Custom_SepticTank",
                 Description="Wet, sulfide-rich service: the walls must not seep and the steel must stay covered",
                 HasProperties={"ConcreteQuality": "K-250 (f'c 21 MPa)", "ConcreteCoverInner": "50 mm (anti-corrosion)", "ConcreteCoverOuter": "30 mm",
                                "InternalCoating": "Coal tar epoxy / bitumen, 3 coats", "CementType": "PPC / High Sulfate Resistance (Type HS)",
                                "Reinforcement": "Double layer deformed bar, D10 at 150 mm max", "Status": "Candidate"})
        layers = lambda t: [{"Material": SEPTIC_CONCRETE, "LayerThickness": t}]
        for mm in sorted({round(t[key] * 1000) for t in tanks for key in ("wall", "partition")}):
            self.add(id=self.septic_wall_type(mm), type="IfcWallType", Name=f"SepticConcrete_{mm}", PredefinedType="STANDARD",
                     MaterialLayers=layers(mm / 1000.0), HasPropertySets=["pset_septic_concrete"])
        for key, predefined in (("base", "BASESLAB"), ("cover", "ROOF")):
            for mm in sorted({round(t[key] * 1000) for t in tanks}):
                self.add(id=self.septic_slab_type(key, mm), type="IfcSlabType", Name=f"Septic{key.capitalize()}_{mm}", PredefinedType=predefined,
                         MaterialLayers=layers(mm / 1000.0), HasPropertySets=["pset_septic_concrete"])

    @staticmethod
    def septic_wall_type(mm):
        return f"wall_type_septic_{mm}"

    @staticmethod
    def septic_slab_type(key, mm):
        return f"slab_type_septic_{key}_{mm}"

    # ---- slabs ----------------------------------------------------------------------------
    def slabs(self):
        for s in self.spec.get("slabs", []):
            thickness = 0.2 if s.get("type", "floor_100") == "floor_200" else 0.1
            kind = s.get("type", "floor_100")
            type_id = self.slab_material_type(kind, s["material"]) if "material" in s else SLAB_TYPES[kind]
            node = dict(id=s["id"], type="IfcSlab", IsTypedBy=type_id, ContainedIn=self.storey_id(s["storey"]))
            if s.get("steel_grate"):
                node["HasPropertySets"] = ["pset_slab_steel"]
            node.update(Name=s.get("name", s["id"]), Location=[0.0, 0.0, s.get("z", r(self.elevation(s["storey"]) - thickness))],
                        OuterCurve=s["polygon"])
            self.nodes.append(node)

    # ---- walls: rooms and loose walls are reduced to segments, merged, then cut for doors ---
    def wall_segments(self):
        segs = []  # (storey, orient, fixed, a, b, material, openings)
        for room in self.spec.get("rooms", []):
            if "polygon" in room:  # axis-aligned outline; an edge's side is the way it faces, doors match by side and range
                pts = room["polygon"]
                ccw = sum(xa * yb - xb * ya for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1])) > 0
                for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]):
                    orient, fixed, a, b = ("x", ya, min(xa, xb), max(xa, xb)) if ya == yb else ("y", xa, min(ya, yb), max(ya, yb))
                    inward = (-(yb - ya), xb - xa) if ccw else (yb - ya, -(xb - xa))  # normal pointing into the room
                    side = ("south" if inward[1] > 0 else "north") if orient == "x" else ("west" if inward[0] > 0 else "east")
                    openings = [(d["from"], d["to"], d.get("height", DOOR_HEIGHT)) for d in room.get("doors", [])
                                if d["side"] == side and a <= d["from"] and d["to"] <= b]
                    segs.append((room["storey"], orient, fixed, a, b, room["wall"], openings))
                continue
            x0, y0, x1, y1 = room["rect"]
            edges = {"south": ("x", y0, x0, x1), "north": ("x", y1, x0, x1), "west": ("y", x0, y0, y1), "east": ("y", x1, y0, y1)}
            for side, (orient, fixed, a, b) in edges.items():
                openings = [(d["from"], d["to"], d.get("height", DOOR_HEIGHT)) for d in room.get("doors", []) if d["side"] == side]
                kept = [(a, b)]  # "open" stretches of this edge get no wall at all
                for g in sorted((g for g in room.get("open", []) if g["side"] == side), key=lambda g: g["from"]):
                    kept = [piece for k0, k1 in kept for piece in ((k0, min(k1, g["from"])), (max(k0, g["to"]), k1)) if piece[1] > piece[0] + 1e-9]
                for k0, k1 in kept:
                    segs.append((room["storey"], orient, fixed, k0, k1, room["wall"], [o for o in openings if k0 <= o[0] and o[1] <= k1]))
        for w in self.spec.get("walls", []):
            (xa, ya), (xb, yb) = w["from"], w["to"]
            orient, fixed, a, b = ("x", ya, min(xa, xb), max(xa, xb)) if ya == yb else ("y", xa, min(ya, yb), max(ya, yb))
            segs.append((w["storey"], orient, fixed, a, b, w["wall"], []))
        return segs

    def walls(self):
        groups = {}
        for storey, orient, fixed, a, b, material, openings in self.wall_segments():
            groups.setdefault((storey, orient, fixed, material), []).append((a, b, openings))
        for (storey, orient, fixed, material), items in groups.items():
            items.sort(key=lambda it: it[0])
            merged = []  # shared room edges overlap or touch: fuse them into one run
            for a, b, openings in items:
                if merged and a <= merged[-1][1] + 1e-9:
                    merged[-1][1] = max(merged[-1][1], b)
                    merged[-1][2].extend(openings)
                else:
                    merged.append([a, b, list(openings)])
            for a, b, openings in merged:
                self.wall_run(storey, orient, fixed, material, a, b, sorted(set(openings)))

    def wall_run(self, storey, orient, fixed, material, a, b, openings, height=None, owner=None):
        z, height, n = self.elevation(storey), height or self.height, 0
        cursor, pieces = a, []
        for o0, o1, oh in openings:
            pieces += [(cursor, o0, z, height)] if o0 > cursor + 1e-9 else []
            pieces.append((o0, o1, z + oh, height - oh))  # lintel above the opening
            cursor = o1
        pieces += [(cursor, b, z, height)] if b > cursor + 1e-9 else []
        for p0, p1, pz, ph in pieces:
            n += 1
            node = dict(id=f"wall_{owner or storey}_{orient}{slug(fixed)}_{n}", type="IfcWall", IsTypedBy=WALL_TYPES[material], ContainedIn=self.storey_id(storey))
            if orient == "x":
                node["Location"] = [r(p0), fixed, r(pz)]
            else:
                node["Location"] = [fixed, r(p0), r(pz)]
                node["RefDirection"] = [0.0, 1.0, 0.0]
            node.update(Length=r(p1 - p0), Height=r(ph))
            self.nodes.append(node)

    # ---- columns, stairs -------------------------------------------------------------------
    def columns(self):
        for group in self.spec.get("columns", []):
            storey = group["storey"]
            for x, y in group["at"]:  # `rotation` 90 turns the section so its flanges face x instead of y
                self.add(id=f"col_{storey}_{slug(x)}_{slug(y)}", type="IfcColumn", IsTypedBy=COLUMN_TYPE, ContainedIn=self.storey_id(storey),
                         Location=[float(x), float(y), self.elevation(storey)], RefDirection=[0.0, 1.0, 0.0] if group.get("rotation", 0) % 180 == 90 else None,
                         Length=self.height)

    def stairs(self):
        for stair in self.spec.get("stairs", []):
            sid, z0 = stair["id"], self.elevation(stair["storey"])
            self.add(id=sid, type="IfcStair", PredefinedType="TWO_STRAIGHT_RUN_STAIR", ContainedIn=self.storey_id(stair["storey"]))
            for i, f in enumerate(stair["flights"], 1):
                dx, dy = f["direction"]
                self.add(id=f"{sid}_flight_{i}", type="IfcStairFlight", PredefinedType="STRAIGHT", Decomposes=sid, IsTypedBy="stair_flight_type_steel",
                         Location=[f["start"][0], f["start"][1], r(z0 + f["start"][2])], RefDirection=[float(dx), float(dy), 0.0], Rise=f["rise"], Run=f["run"],
                         SolidTreads=f.get("solid"))
            for i, land in enumerate(stair.get("landings", []), 1):
                self.add(id=f"{sid}_landing_{i}", type="IfcSlab", IsTypedBy="slab_type_landing_100", Decomposes=sid,
                         Location=[0.0, 0.0, r(z0 + land["z"])], OuterCurve=land["polygon"])

    # ---- rainwater: a tank and the pipes that feed and drain it -----------------------------
    def tanks(self):
        for tank in self.spec.get("tanks", []):
            x0, y0, x1, y1 = tank["rect"]
            self.add(id=tank["id"], type="IfcTank", PredefinedType="STORAGE", ContainedIn=self.storey_id(tank["storey"]), Name=tank.get("name", tank["id"]),
                     Location=[0.0, 0.0, tank.get("z", self.elevation(tank["storey"]))], OuterCurve=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                     Height=tank["height"])

    def septic_tanks(self):
        """A buried tank in chambers along y, south to north. `outer` is [x0, y0, x1, y1] to the outer faces and must equal the sum of the
        outer walls, `chambers` (clear lengths) and the partitions between them. `floor_z` is the top of the base slab, `inner_height` the clear
        height above it; the cover slab sits on the walls. Everything aggregates into one IfcTank that has no shape of its own."""
        for tank in self.spec.get("septic_tanks", []):
            sid, storey = tank["id"], tank["storey"]
            x0, y0, x1, y1 = tank["outer"]
            wall, part, base, cover = tank["wall"], tank["partition"], tank["base"], tank["cover"]
            chambers, floor, height = tank["chambers"], tank["floor_z"], tank["inner_height"]
            length = 2 * wall + sum(chambers) + part * (len(chambers) - 1)
            assert abs((y1 - y0) - length) < 1e-6, f"{sid}: the outer length is {y1 - y0} m but walls, chambers and partitions add up to {length} m"
            ground, top = self.elevation(storey), r(floor + height)
            outline = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            self.add(id=f"pset_{sid}", type="IfcPropertySet", Name="Custom_SepticLayout",
                     HasProperties={"InnerWidth": r(x1 - x0 - 2 * wall), "InnerLength": r(sum(chambers)), "InnerHeight": height,
                                    "ChamberLengths": " / ".join(f"{c} m" for c in chambers),
                                    "InnerFloorBelowGround": r(ground - floor), "CoverTopAboveGround": r(top + cover - ground)})
            self.add(id=sid, type="IfcTank", PredefinedType="STORAGE", ContainedIn=self.storey_id(storey), Name=tank.get("name", sid),
                     Description=tank.get("description"), HasPropertySets=[f"pset_{sid}"])

            def wall_node(name, thickness, orient, fixed, a, b):
                node = dict(id=f"{sid}_{name}", type="IfcWall", IsTypedBy=self.septic_wall_type(round(thickness * 1000)), Decomposes=sid)
                node["Location"] = [r(a), r(fixed), floor] if orient == "x" else [r(fixed), r(a), floor]
                if orient == "y":
                    node["RefDirection"] = [0.0, 1.0, 0.0]
                self.nodes.append({**node, "Length": r(b - a), "Height": height})

            wall_node("wall_west", wall, "y", x0 + wall / 2.0, y0, y1)  # the long walls own the corners
            wall_node("wall_east", wall, "y", x1 - wall / 2.0, y0, y1)
            wall_node("wall_south", wall, "x", y0 + wall / 2.0, x0 + wall, x1 - wall)
            wall_node("wall_north", wall, "x", y1 - wall / 2.0, x0 + wall, x1 - wall)
            cursor = y0 + wall
            for i, clear in enumerate(chambers[:-1], 1):
                cursor += clear
                wall_node(f"partition_{i}", part, "x", cursor + part / 2.0, x0 + wall, x1 - wall)
                cursor += part
            for name, key, z in (("base", "base", floor - base), ("cover", "cover", top)):
                self.add(id=f"{sid}_{name}", type="IfcSlab", IsTypedBy=self.septic_slab_type(key, round(tank[key] * 1000)), Decomposes=sid,
                         Location=[0.0, 0.0, r(z)], OuterCurve=outline)

    def pipes(self):
        for pipe in self.spec.get("pipes", []):
            for i, (a, b) in enumerate(zip(pipe["path"], pipe["path"][1:]), 1):  # one segment per straight stretch
                length = math.dist(a, b)
                self.add(id=f"{pipe['id']}_{i}", type="IfcPipeSegment", PredefinedType=pipe.get("predefined", "RIGIDSEGMENT"), ContainedIn=self.storey_id(pipe["storey"]),
                         Name=pipe.get("name", pipe["id"]), Description=pipe.get("description"), Location=[float(c) for c in a], Direction=[r((q - p) / length) for p, q in zip(a, b)],
                         Length=r(length), Diameter=pipe.get("diameter", 0.1))

    # ---- roofs: each roof is one sloped panel over 3 or 4 corners [x, y, z]; z is the rise above its eaves ---
    def roofs(self):
        specs = self.spec.get("roofs", [])
        for roof in specs:
            corners = roof["corners"]
            assert len(corners) in (3, 4), f"{roof['id']}: a roof has 3 or 4 corners"
            storey, rise = roof["storey"], roof.get("wall_height", 0.0)
            pset = f"pset_{roof['id']}"
            self.add(id=pset, type="IfcPropertySet", Name="Custom_Roof", HasProperties={"PanelMaterial_Default": roof.get("panel", "polycarbonate")})
            self.add(id=roof["id"], type="IfcRoof", Name=roof["id"], PredefinedType="SHED_ROOF", ContainedIn=self.storey_id(storey),
                     Description=f"One sloped panel; the corner z is the rise above the eaves, which stand {rise} m above the roof slab, on the walls below",
                     HasPropertySets=[pset], Location=[0.0, 0.0, r(self.elevation(storey) + rise)],
                     OuterCurve=[[r(x), r(y), r(z)] for x, y, z in corners], Strips=self.strips(roof))
            self.roof_walls(roof, specs)
            self.roof_frame(roof)

    @staticmethod
    def strips(roof):
        """`cladding`: panels laid side by side across y from the roof's south edge, `[{panel, width}]`; returns [y0, y1, panel] each."""
        cladding = roof.get("cladding")
        if not cladding:
            return None
        y = lo = min(c[1] for c in roof["corners"])
        out = []
        for strip in cladding:
            out.append([r(y), r(y + strip["width"]), strip["panel"]])
            y += strip["width"]
        assert abs(y - max(c[1] for c in roof["corners"])) < 1e-9, f"{roof['id']}: the cladding widths add up to {r(y - lo)} m, not the roof's span"
        return out

    def frame_geometry(self, roof):
        """Slope of a roof that falls along x: (cos, slope) with slope = dz/dx. The plane must not fall along y."""
        xs, ys = [c[0] for c in roof["corners"]], [c[1] for c in roof["corners"]]
        xa, xb, ya, yb = min(xs), max(xs), min(ys), max(ys)
        assert abs(self.surface(roof, xa, yb) - self.surface(roof, xa, ya)) < 1e-9, f"{roof['id']}: the frame needs a roof that falls along x only"
        slope = (self.surface(roof, xb, ya) - self.surface(roof, xa, ya)) / (xb - xa)
        return 1.0 / math.sqrt(1.0 + slope * slope), slope

    def frame_drop(self, roof):
        """Vertical distance from the panel underside down to the underside of the rafter: purlin and rafter depth, measured square to the slope."""
        cos, _ = self.frame_geometry(roof)
        return (roof["frame"]["purlin"]["depth"] + roof["frame"]["rafter"]["depth"]) / cos

    @staticmethod
    def rafter_ys(roof):
        """y of each rafter: one `edge_inset` in from each side edge, and every `pitch` from the south edge between them."""
        ys, rafter = [c[1] for c in roof["corners"]], roof["frame"]["rafter"]
        ya, yb = min(ys), max(ys)
        inner = [ya + k * rafter["pitch"] for k in range(1, 100) if ya + k * rafter["pitch"] < yb - rafter["edge_inset"] - 1e-9]
        return [ya + rafter["edge_inset"]] + inner + [yb - rafter["edge_inset"]]

    def roof_frame(self, roof):
        """Rafters run down the slope under the purlins, which run across it under the panels: panel, purlin, rafter, knee-wall rail.
        Rafters sit at `pitch` along y (plus one `edge_inset` in from each side edge); purlins are spread evenly from `inset` in from
        the high edge to `inset` in from the low edge, no further apart than `max_spacing` along the slope."""
        frame = roof.get("frame")
        if not frame:
            return
        storey, z0 = roof["storey"], self.elevation(roof["storey"])
        cos, slope = self.frame_geometry(roof)
        sin = -slope * cos
        xs, ys = [c[0] for c in roof["corners"]], [c[1] for c in roof["corners"]]
        xa, xb, ya, yb = min(xs), max(xs), min(ys), max(ys)
        rafter, purlin = frame["rafter"], frame["purlin"]
        pd, rd = purlin["depth"], rafter["depth"]
        normal = (sin, 0.0, cos)  # up, square to the slope
        x0 = xa + rafter.get("inset", 0.05)
        for i, y in enumerate(self.rafter_ys(roof)):
            t = pd + rd  # the rafter's underside lies this far below the panel underside, square to the slope
            node = dict(id=f"{roof['id']}_rafter_{i}", type="IfcBeam", IsTypedBy=f"beam_type_rafter_{roof['id']}", ContainedIn=self.storey_id(storey))
            node["Location"] = [r(x0 - t * normal[0]), r(y), r(z0 + self.surface(roof, x0, y) - t * normal[2])]
            node.update(Direction=[round(cos, 9), 0.0, round(slope * cos, 9)], Length=r((xb - x0) / cos))
            self.nodes.append(node)
        p0, p1 = xa + purlin["inset"], xb - purlin["inset"]
        n = math.ceil((p1 - p0) / cos / purlin["max_spacing"] - 1e-9)
        for i in range(n + 1):
            xp = p0 + i * (p1 - p0) / n
            cx, cz = xp - pd / 2.0 * normal[0], z0 + self.surface(roof, xp, ya) - pd / 2.0 * normal[2]  # centre of the purlin, level
            node = dict(id=f"{roof['id']}_purlin_{i}", type="IfcBeam", IsTypedBy=f"beam_type_purlin_{roof['id']}", ContainedIn=self.storey_id(storey))
            node["Location"] = [r(cx), r(ya + purlin["inset"]), r(cz - pd / 2.0)]
            node.update(RefDirection=[0.0, 1.0, 0.0], Length=r(yb - ya - 2 * purlin["inset"]))
            self.nodes.append(node)

    @staticmethod
    def edges(roof):
        c = roof["corners"]
        return [(tuple(c[i]), tuple(c[(i + 1) % len(c)])) for i in range(len(c))]

    @staticmethod
    def inset(roof, orient, fixed, thickness):
        """Centreline of a wall whose outer face is flush with the roof edge at `fixed`: half a thickness towards the roof's middle."""
        centre = sum(c[1 if orient == "x" else 0] for c in roof["corners"]) / len(roof["corners"])
        return r(fixed + (thickness / 2.0 if centre > fixed else -thickness / 2.0))

    def roof_walls(self, roof, specs):
        """Parapets under the eaves (`parapet`: edge numbers), and a wall under each sloped edge named in `edge_walls`, up to the roof surface.
        Edge i runs from corner i to corner i + 1. Where another roof meets an edge there is no wall below that roof's surface."""
        storey, rise, material = roof["storey"], roof.get("wall_height", 0.0), roof.get("wall", "aac")
        z0 = self.elevation(storey)
        edges = self.edges(roof)
        for i in roof.get("parapet", []):
            (xa, ya, _), (xb, yb, _) = edges[i]
            orient, fixed, a, b = ("x", ya, min(xa, xb), max(xa, xb)) if ya == yb else ("y", xa, min(ya, yb), max(ya, yb))
            self.wall_run(storey, orient, self.inset(roof, orient, fixed, WALL_THICKNESS[material]), material, a, b, [], height=rise, owner=roof["id"])
        others = [(o, e) for o in specs if o is not roof and o["storey"] == storey for e in self.edges(o)]
        for i, (A, B) in enumerate(edges):
            if A[:2] == B[:2] or (A[2] == 0 and B[2] == 0):
                continue  # the eaves line: only the parapets stand there
            axis_aligned = A[1] == B[1] or A[0] == B[0]
            if not axis_aligned:
                assert any({tuple(map(r, A)), tuple(map(r, B))} == {tuple(map(r, P)), tuple(map(r, Q))} for _, (P, Q) in others), \
                    f"{roof['id']}: the sloped edge {i} needs the neighbouring roof's edge to meet it"
                continue  # a hip or valley between two slopes needs no wall
            choice = roof.get("edge_walls", {}).get(str(i))
            if not choice:
                continue  # a wall is opt-in: `true` for the roof's own wall type, or {"wall": ..., "doors": [...]}
            choice = {} if choice is True else choice
            self.edge_wall(roof, i, A, B, z0, rise, choice.get("wall", material), choice.get("doors", []), others)

    def edge_wall(self, roof, i, A, B, z0, rise, material, doors, others):
        orient = "x" if A[1] == B[1] else "y"
        k, f = (0, 1) if orient == "x" else (1, 0)  # k: the coordinate along the edge, f: the one that stays fixed
        (ua, za), (ub, zb), fixed = (A[k], A[2]), (B[k], B[2]), A[f]
        if ua > ub:
            (ua, za), (ub, zb) = (ub, zb), (ua, za)

        top = lambda u: rise + za + (zb - za) * (u - ua) / (ub - ua)
        covers = []  # (from, to, surface height) of each roof edge lying on this edge's line
        for o, (P, Q) in others:
            if P[f] != fixed or Q[f] != fixed or (P[k] == Q[k]):
                continue
            (pa, pz), (pb, pz2) = ((P[k], P[2]), (Q[k], Q[2])) if P[k] < Q[k] else ((Q[k], Q[2]), (P[k], P[2]))
            lo, hi = max(pa, ua), min(pb, ub)
            if hi - lo > 1e-9:
                orise = o.get("wall_height", 0.0)
                covers.append((lo, hi, (lambda u, pa=pa, pz=pz, pb=pb, pz2=pz2, orise=orise: orise + pz + (pz2 - pz) * (u - pa) / (pb - pa))))
        tw = WALL_THICKNESS[material]
        centre = self.inset(roof, orient, fixed, tw)
        if doors:
            assert not covers and za == zb, f"{roof['id']}: doors only fit in a level wall that no other roof touches"
            self.wall_run(roof["storey"], orient, centre, material, ua, ub, [(d["from"], d["to"], d.get("height", DOOR_HEIGHT)) for d in doors],
                          height=r(rise + za), owner=roof["id"])
            return

        xs = {ua, ub} | {v for a, b, _ in covers for v in (a, b)}
        for a, b, g in covers:  # where the slope crosses the surface of a neighbour
            inside = sorted(v for v in xs if a <= v <= b)
            for p, q in zip(inside, inside[1:]):
                d0, d1 = top(p) - g(p), top(q) - g(q)
                if d0 * d1 < -1e-12:
                    xs.add(p + (q - p) * d0 / (d0 - d1))
        xs = sorted(xs)

        def below(u0, u1):  # the neighbour surface under the stretch u0..u1, or None
            mid = (u0 + u1) / 2.0
            found = [g for a, b, g in covers if a <= mid <= b]
            return max(found, key=lambda g: g(mid)) if found else None

        runs, run = [], []  # a run is a list of (u0, lower0, u1, lower1) that join up
        for u0, u1 in zip(xs, xs[1:]):
            g = below(u0, u1)
            l0, l1 = (g(u0), g(u1)) if g else (0.0, 0.0)
            if top(u0) - l0 < 1e-9 and top(u1) - l1 < 1e-9:  # nothing above the neighbour here
                if run:
                    runs.append(run)
                run = []
                continue
            l0, l1 = min(l0, top(u0)), min(l1, top(u1))
            if run and abs(run[-1][3] - l0) > 1e-9:
                runs.append(run)
                run = []
            run.append((u0, l0, u1, l1))
        if run:
            runs.append(run)
        for n, run in enumerate(runs, 1):
            start, end = run[0][0], run[-1][2]
            lower = [[r(run[0][0] - start), r(run[0][1])]] + [[r(s[2] - start), r(s[3])] for s in run]
            upper = [[r(run[0][0] - start), r(top(run[0][0]))]] + [[r(s[2] - start), r(top(s[2]))] for s in run]
            outline = lower + upper[::-1]
            outline = [p for j, p in enumerate(outline) if p != outline[j - 1]]
            node = dict(id=f"{roof['id']}_wall_{i}_{n}", type="IfcWall", IsTypedBy=WALL_TYPES[material], ContainedIn=self.storey_id(roof["storey"]))
            node["Location"] = [r(start), centre, z0] if orient == "x" else [centre, r(start), z0]
            if orient == "y":
                node["RefDirection"] = [0.0, 1.0, 0.0]
            node.update(Length=r(end - start), Height=r(max(p[1] for p in outline)), Outline=outline)
            self.nodes.append(node)

    # ---- knee walls: light posts on the columns under a roof's low edge, tied by a rail the roof rests on ----
    @staticmethod
    def surface(roof, x, y):
        """Height of the roof panel above the roof slab at plan point (x, y), from the plane through its first three corners."""
        (xa, ya, za), (xb, yb, zb), (xc, yc, zc) = roof["corners"][:3]
        ux, uy, uz, vx, vy, vz = xb - xa, yb - ya, zb - za, xc - xa, yc - ya, zc - za
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        return roof.get("wall_height", 0.0) + za - (nx * (x - xa) + ny * (y - ya)) / nz

    @staticmethod
    def covers(roof, x, y, tol=1e-9):
        """True when plan point (x, y) lies over the roof's outline (the edges count)."""
        pts = [(c[0], c[1]) for c in roof["corners"]]
        side = [(bx - ax) * (y - ay) - (by - ay) * (x - ax) for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1])]
        return all(s >= -tol for s in side) or all(s <= tol for s in side)

    def knee_walls(self):
        """Each run is a line (`axis` x or y, at `at`, between `from` and `to`) under one or more roofs. A post stands on every column
        of the `columns` storey along it, as tall as the roof surface above it allows once the rail (the roof rests on it) is counted.
        The rail ties the posts and stops at the face of a rail laid by an earlier run where two runs meet at a corner."""
        spec = self.spec.get("knee_walls")
        if not spec:
            return
        storey, section = spec["storey"], spec["section"]
        z0, w, depth = self.elevation(storey), section["width"], section["depth"]
        roofs = {roof["id"]: roof for roof in self.spec.get("roofs", [])}
        columns = {(float(x), float(y)) for g in self.spec.get("columns", []) if g["storey"] == spec["columns"] for x, y in g["at"]}
        posts, rails = {}, []  # posts: (x, y) -> height; rails: (axis, at, lo, hi, top)
        for run in spec["runs"]:
            axis, at = run["axis"], float(run["at"])
            if "rafter_posts" in run:
                self.rafter_posts(run, roofs[run["rafter_posts"]], z0)
                continue
            k, f = (0, 1) if axis == "x" else (1, 0)  # k: the coordinate along the run, f: the one that stays fixed
            pts = sorted((c for c in columns if abs(c[f] - at) < 1e-9 and run["from"] - 1e-9 <= c[k] <= run["to"] + 1e-9), key=lambda c: c[k])
            pts = sorted(pts + [(float(x), float(y)) for x, y in run.get("on_beam", [])], key=lambda c: c[k])  # posts that stand on a beam, between columns
            assert len(pts) >= 2, f"knee wall {run['id']}: fewer than two columns on the line"
            tops = []
            for x, y in pts:
                roof = next((roofs[i] for i in run["roofs"] if self.covers(roofs[i], x, y)), None)
                assert roof, f"knee wall {run['id']}: no roof over the column at ({x}, {y})"
                tops.append(self.surface(roof, x, y))
            assert max(tops) - min(tops) < 1e-6, f"knee wall {run['id']}: the roof is not level along the run, so a straight rail cannot follow it"
            top, height = r(tops[0]), r(tops[0] - depth)
            tall = {(float(x), float(y)): h for x, y, h in run.get("tall_posts", [])}  # posts that carry something higher than the rail, e.g. a roof corner
            for x, y in pts:
                if (x, y) in posts:  # a corner shared with an earlier run
                    assert abs(posts[(x, y)] - height) < 1e-6, f"knee wall {run['id']}: the post at ({x}, {y}) is already placed at another height"
                    continue
                posts[(x, y)] = height
                self.add(id=f"knee_post_{slug(r(x))}_{slug(r(y))}", type="IfcColumn", IsTypedBy=KNEE_POST_TYPE, ContainedIn=self.storey_id(storey),
                         Location=[r(x), r(y), z0], Length=tall.get((x, y), height))
            ends = []
            for t, sign in ((pts[0][k], -1), (pts[-1][k], 1)):
                meets = [p for p in rails if p[0] != axis and abs(p[1] - t) < 1e-9 and p[2] - 1e-9 <= at <= p[3] + 1e-9]
                for p in meets:
                    assert abs(p[4] - top) < 1e-6, f"knee wall {run['id']}: meets a rail of another height at {t}"
                ends.append(t - sign * w / 2.0 if meets else t + sign * w / 2.0)
            lo, hi = ends
            rails.append((axis, at, lo, hi, top))
            node = dict(id=f"knee_rail_{run['id']}", type="IfcBeam", IsTypedBy=KNEE_RAIL_TYPE, ContainedIn=self.storey_id(storey))
            node["Location"] = [r(lo), at, r(z0 + height)] if axis == "x" else [at, r(lo), r(z0 + height)]
            if axis == "y":
                node["RefDirection"] = [0.0, 1.0, 0.0]
            node["Length"] = r(hi - lo)
            self.nodes.append(node)

    def rafter_posts(self, run, roof, z0):
        """No rail: a post under each rafter of `roof` where it crosses the line `at` (axis y), up to the rafter's underside.
        Each stands on a column or on the roof beam along the line."""
        assert run["axis"] == "y", f"knee wall {run['id']}: rafter posts are only for a line along y"
        at = float(run["at"])
        for y in self.rafter_ys(roof):
            height = r(self.surface(roof, at, y) - self.frame_drop(roof))
            self.add(id=f"knee_post_{slug(r(at))}_{slug(r(y))}", type="IfcColumn", IsTypedBy=KNEE_POST_TYPE, ContainedIn=self.storey_id(self.spec["knee_walls"]["storey"]),
                     Location=[r(at), r(y), z0], Length=height)

    # ---- beams: they end on the face of a column, or (secondary) on the web of a main beam ------
    def beam_blocks(self):
        """`beams` is one block, or a list of blocks (one per storey, each with its own layout and optional `sections`)."""
        spec = self.spec.get("beams") or []
        return [spec] if isinstance(spec, dict) else spec

    def beams(self):
        for block in self.beam_blocks():
            self.beam_block(block)

    def beam_block(self, spec):
        storey = spec["storey"]
        top = self.elevation(storey)
        sections = {kind: BEAM_SECTIONS[name] for kind, name in {**DEFAULT_SECTIONS, **spec.get("sections", {})}.items()}
        depth = {kind: sec[3] for kind, sec in sections.items()}
        web_half = sections["main"][4] / 2.0
        mains = spec.get("main", [])
        column_half = COLUMN_SIZE / 2.0
        columns = {(float(x), float(y)) for g in self.spec.get("columns", []) for x, y in g["at"]}

        def meets_main(axis, coord, across):
            """True when a main beam runs perpendicular to `axis` at `coord` and covers the secondary's line `across`."""
            return any(m["axis"] != axis and abs(m["at"] - coord) < 1e-9 and any(a - 1e-9 <= across <= b + 1e-9 for a, b in m["spans"]) for m in mains)

        for kind in ("main", "secondary"):
            for beam in spec.get(kind, []):
                axis, at = beam["axis"], beam["at"]
                for i, (a, b) in enumerate(beam["spans"]):
                    def point(t):
                        return (t, at) if axis == "x" else (at, t)

                    if point(a) in columns:
                        a += column_half
                    elif kind == "secondary" and meets_main(axis, a, at):
                        a += web_half
                    if point(b) in columns:
                        b -= column_half
                    elif kind == "secondary" and meets_main(axis, b, at):
                        b -= web_half
                    z = r(top - depth[kind])
                    node = dict(id=f"beam_{storey}_{axis}_{slug(at)}_{kind[0]}{i}", type="IfcBeam", IsTypedBy=sections[kind][0], ContainedIn=self.storey_id(storey))
                    node["Location"] = [r(a), at, z] if axis == "x" else [at, r(a), z]
                    if axis == "y":
                        node["RefDirection"] = [0.0, 1.0, 0.0]
                    node["Length"] = r(b - a)
                    self.nodes.append(node)

    def build(self):
        self.header()
        for step in (self.slabs, self.stairs, self.walls, self.columns, self.beams, self.knee_walls, self.roofs, self.tanks, self.septic_tanks, self.pipes):
            step()
        return self.nodes


def render(nodes):
    """Same layout as the hand-written files: identity and relations on one line, geometry on the next."""
    out = ['{', '  "version": "0.2.0",', '  "data": [']
    for k, n in enumerate(nodes):
        head = [f'"{key}": {json.dumps(n[key])}' for key in HEAD_KEYS if key in n]
        tail = [f'"{key}": {json.dumps(v)}' for key, v in n.items() if key not in HEAD_KEYS]
        out.append('    {')
        if n["type"] in ONE_LINE or not tail:
            out.append('      ' + ', '.join(head + tail))
        else:
            out += ['      ' + ', '.join(head) + ',', '      ' + ', '.join(tail)]
        out.append('    }' + (',' if k < len(nodes) - 1 else ''))
    return '\n'.join(out + ['  ]', '}', ''])


def generate_from_folder(folder):
    spec_path, output_path = Path(folder) / SPEC_NAME, Path(folder) / OUTPUT_NAME
    with open(spec_path) as f:
        nodes = Design(json.load(f)).build()
    output_path.write_text(render(nodes), newline='\n')
    print(f"Wrote {len(nodes)} nodes to '{output_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Build {OUTPUT_NAME} from {SPEC_NAME} inside a project folder.")
    parser.add_argument("folder", help=f"project folder holding {SPEC_NAME}; {OUTPUT_NAME} is written next to it")
    generate_from_folder(parser.parse_args().folder)
