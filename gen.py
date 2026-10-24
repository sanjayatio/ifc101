import argparse, json
from pathlib import Path

SPEC_NAME, OUTPUT_NAME = "spec.json", "design.ifcjson"
HEAD_KEYS = ("id", "type", "IsTypedBy", "ContainedIn", "Decomposes", "HasPropertySets", "PredefinedType")
ONE_LINE = {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcPropertySet"}

BEAM_TYPES = {"main": ("beam_type_wf_200x100", "WF_200x100", 0.1, 0.2, 0.0055, 0.008),
              "secondary": ("beam_type_wf_150x75", "WF_150x75", 0.075, 0.15, 0.005, 0.007)}
WALL_TYPES = {"brick": "wall_type_brick_100", "aac": "wall_type_aac_100"}
SLAB_TYPES = {"floor_100": "slab_type_floor_100", "floor_200": "slab_type_floor_200"}
COLUMN_TYPE, COLUMN_SIZE = "column_type_hbeam_150x150", 0.15
DOOR_HEIGHT = 2.1


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
        self.nodes.append(node)

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

        for tid, name, width, depth, web, flange in BEAM_TYPES.values():
            add(id=tid, type="IfcBeamType", Name=name, PredefinedType="BEAM", Material="Steel_Black",
                Profile={"type": "IfcIShapeProfileDef", "OverallWidth": width, "OverallDepth": depth, "WebThickness": web, "FlangeThickness": flange})
        add(id=COLUMN_TYPE, type="IfcColumnType", Name="HBeam_150x150", PredefinedType="COLUMN", Material="Steel_Black",
            Profile={"type": "IfcIShapeProfileDef", "OverallWidth": 0.15, "OverallDepth": 0.15, "WebThickness": 0.007, "FlangeThickness": 0.01})
        add(id="wall_type_brick_100", type="IfcWallType", Name="RedBrick_100", PredefinedType="STANDARD",
            Description="Ground floor load-bearing red brick masonry", MaterialLayers=[{"Material": "Red Brick", "LayerThickness": 0.1}],
            HasPropertySets=["pset_wall_ground_common", "pset_wall_ground_decision"])
        add(id="wall_type_aac_100", type="IfcWallType", Name="AAC_100", PredefinedType="STANDARD",
            Description="Lightweight AAC blocks to reduce structural load on upper level",
            MaterialLayers=[{"Material": "Autoclaved Aerated Concrete (AAC)", "LayerThickness": 0.1}],
            HasPropertySets=["pset_wall_first_common", "pset_wall_first_decision"])
        add(id="slab_type_floor_100", type="IfcSlabType", Name="Floor_100", PredefinedType="FLOOR", MaterialLayers=[{"LayerThickness": 0.1}])
        add(id="slab_type_floor_200", type="IfcSlabType", Name="Floor_200", PredefinedType="FLOOR", MaterialLayers=[{"LayerThickness": 0.2}])
        add(id="slab_type_landing_100", type="IfcSlabType", Name="Landing_100", PredefinedType="LANDING", MaterialLayers=[{"LayerThickness": 0.1}])
        add(id="stair_flight_type_steel", type="IfcStairFlightType", Name="SteelFlight", PredefinedType="STRAIGHT", HasPropertySets=["pset_stair_flight"])

    # ---- slabs ----------------------------------------------------------------------------
    def slabs(self):
        for s in self.spec.get("slabs", []):
            thickness = 0.2 if s.get("type", "floor_100") == "floor_200" else 0.1
            node = dict(id=s["id"], type="IfcSlab", IsTypedBy=SLAB_TYPES[s.get("type", "floor_100")], ContainedIn=self.storey_id(s["storey"]))
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

    def wall_run(self, storey, orient, fixed, material, a, b, openings):
        z, height, n = self.elevation(storey), self.height, 0
        cursor, pieces = a, []
        for o0, o1, oh in openings:
            pieces += [(cursor, o0, z, height)] if o0 > cursor + 1e-9 else []
            pieces.append((o0, o1, z + oh, height - oh))  # lintel above the opening
            cursor = o1
        pieces += [(cursor, b, z, height)] if b > cursor + 1e-9 else []
        for p0, p1, pz, ph in pieces:
            n += 1
            node = dict(id=f"wall_{storey}_{orient}{slug(fixed)}_{n}", type="IfcWall", IsTypedBy=WALL_TYPES[material], ContainedIn=self.storey_id(storey))
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
            for x, y in group["at"]:
                self.add(id=f"col_{storey}_{slug(x)}_{slug(y)}", type="IfcColumn", IsTypedBy=COLUMN_TYPE, ContainedIn=self.storey_id(storey),
                         Location=[float(x), float(y), self.elevation(storey)], Length=self.height)

    def stairs(self):
        for stair in self.spec.get("stairs", []):
            sid, z0 = stair["id"], self.elevation(stair["storey"])
            self.add(id=sid, type="IfcStair", PredefinedType="TWO_STRAIGHT_RUN_STAIR", ContainedIn=self.storey_id(stair["storey"]))
            for i, f in enumerate(stair["flights"], 1):
                dx, dy = f["direction"]
                self.add(id=f"{sid}_flight_{i}", type="IfcStairFlight", PredefinedType="STRAIGHT", Decomposes=sid, IsTypedBy="stair_flight_type_steel",
                         Location=[f["start"][0], f["start"][1], r(z0 + f["start"][2])], RefDirection=[float(dx), float(dy), 0.0], Rise=f["rise"], Run=f["run"])
            for i, land in enumerate(stair.get("landings", []), 1):
                self.add(id=f"{sid}_landing_{i}", type="IfcSlab", IsTypedBy="slab_type_landing_100", Decomposes=sid,
                         Location=[0.0, 0.0, r(z0 + land["z"])], OuterCurve=land["polygon"])

    # ---- beams: they end on the face of a column, or (secondary) on the web of a main beam ------
    def beams(self):
        spec = self.spec.get("beams")
        if not spec:
            return
        storey = spec["storey"]
        top = self.elevation(storey)
        depth = {kind: BEAM_TYPES[kind][3] for kind in BEAM_TYPES}
        web_half = BEAM_TYPES["main"][4] / 2.0
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
                    node = dict(id=f"beam_{axis}_{slug(at)}_{kind[0]}{i}", type="IfcBeam", IsTypedBy=BEAM_TYPES[kind][0], ContainedIn=self.storey_id(storey))
                    node["Location"] = [r(a), at, z] if axis == "x" else [at, r(a), z]
                    if axis == "y":
                        node["RefDirection"] = [0.0, 1.0, 0.0]
                    node["Length"] = r(b - a)
                    self.nodes.append(node)

    def build(self):
        self.header()
        for step in (self.slabs, self.stairs, self.walls, self.columns, self.beams):
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
