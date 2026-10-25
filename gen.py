import argparse, json, math
from pathlib import Path

SPEC_NAME, OUTPUT_NAME = "spec.json", "design.ifcjson"
HEAD_KEYS = ("id", "type", "IsTypedBy", "ContainedIn", "Decomposes", "HasPropertySets", "PredefinedType")
ONE_LINE = {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcPropertySet"}

BEAM_TYPES = {"main": ("beam_type_wf_200x100", "WF_200x100", 0.1, 0.2, 0.0055, 0.008),
              "secondary": ("beam_type_wf_150x75", "WF_150x75", 0.075, 0.15, 0.005, 0.007)}
WALL_TYPES = {"brick": "wall_type_brick_100", "aac": "wall_type_aac_100", "sandwich": "wall_type_steel_sandwich_50",
              "polycarbonate": "wall_type_polycarbonate_framed"}
WALL_THICKNESS = {"brick": 0.1, "aac": 0.1, "sandwich": 0.05, "polycarbonate": 0.016}  # the sum of each type's layers
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

    # ---- rainwater: a tank and the pipes that feed and drain it -----------------------------
    def tanks(self):
        for tank in self.spec.get("tanks", []):
            x0, y0, x1, y1 = tank["rect"]
            self.add(id=tank["id"], type="IfcTank", PredefinedType="STORAGE", ContainedIn=self.storey_id(tank["storey"]), Name=tank.get("name", tank["id"]),
                     Location=[0.0, 0.0, tank.get("z", self.elevation(tank["storey"]))], OuterCurve=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                     Height=tank["height"])

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
                     OuterCurve=[[r(x), r(y), r(z)] for x, y, z in corners])
            self.roof_walls(roof, specs)

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
        """Parapets under the eaves (`parapet`: edge numbers), and a wall under every sloped edge, up to the roof surface.
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
            choice = roof.get("edge_walls", {}).get(str(i), {})
            if choice is None:
                continue
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
        for step in (self.slabs, self.stairs, self.walls, self.columns, self.beams, self.roofs, self.tanks, self.pipes):
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
