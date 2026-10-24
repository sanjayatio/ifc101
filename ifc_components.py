import math
from ifc_roof import hip_panels, build_panel
from ifc_utils import (guid_for, point, direction, extrude_up, body_shape,
                       axis_placement_3d, get_material, plain_material, assign_material, style_item)

# Materials that carry a surface style; any other material name becomes a plain IfcMaterial.
STYLED_MATERIALS = {"Steel_Black": (0.0, 0.0, 0.0)}


# ---- helpers -----------------------------------------------------------------

def _type_of(scene, node):
    return scene.nodes[node["IsTypedBy"]]


def _properties(scene, node):
    """Merged properties of every property set listed in `node["HasPropertySets"]`."""
    props = {}
    for pset_id in node.get("HasPropertySets", []):
        props.update(scene.nodes[pset_id]["HasProperties"])
    return props


def _thickness(type_node):
    return sum(layer["LayerThickness"] for layer in type_node["MaterialLayers"])


def _material(model, name):
    if name in STYLED_MATERIALS:
        return get_material(model, name, STYLED_MATERIALS[name])[0]
    return plain_material(model, name)


def _style_solid(model, solid, material_name):
    style_item(model, solid, get_material(model, material_name, STYLED_MATERIALS[material_name])[1])


def _product(scene, node, placement, shape=None, **attrs):
    return scene.model.create_entity(node["type"], GlobalId=guid_for(node["id"]), Name=node.get("Name"),
        PredefinedType=node.get("PredefinedType"), ObjectPlacement=placement, Representation=shape, **attrs)


def _i_profile(model, spec, y_offset=0.0):
    assert spec["type"] == "IfcIShapeProfileDef", f"unsupported profile {spec['type']}"
    return model.create_entity("IfcIShapeProfileDef", ProfileType="AREA",
        Position=model.create_entity("IfcAxis2Placement2D", Location=point(model, 0.0, y_offset)),
        OverallWidth=spec["OverallWidth"], OverallDepth=spec["OverallDepth"],
        WebThickness=spec["WebThickness"], FlangeThickness=spec["FlangeThickness"])


# ---- types ---------------------------------------------------------------------

def _type_object(scene, node, material_select=None):
    model = scene.model
    psets = [scene.entities[p] for p in node.get("HasPropertySets", [])]
    type_object = model.create_entity(node["type"], GlobalId=guid_for(node["id"]), Name=node.get("Name"),
        Description=node.get("Description"), HasPropertySets=psets or None, PredefinedType=node["PredefinedType"])
    if material_select is not None:
        assign_material(model, type_object, material_select)
    return type_object


def build_profile_type(scene, node):
    """Beam/column type: the section is an IfcMaterialProfileSet shared by every occurrence."""
    model = scene.model
    profile = model.create_entity("IfcMaterialProfile", Name=node.get("Name"), Material=_material(model, node["Material"]),
        Profile=_i_profile(model, node["Profile"]))
    return _type_object(scene, node, model.create_entity("IfcMaterialProfileSet", Name=node.get("Name"), MaterialProfiles=[profile]))


def build_layered_type(scene, node):
    """Wall/slab type: the build-up is an IfcMaterialLayerSet, which fixes the thickness."""
    model = scene.model
    layers = [model.create_entity("IfcMaterialLayer", Material=_material(model, layer["Material"]) if "Material" in layer else None,
                                  LayerThickness=layer["LayerThickness"]) for layer in node["MaterialLayers"]]
    return _type_object(scene, node, model.create_entity("IfcMaterialLayerSet", MaterialLayers=layers, LayerSetName=node.get("Name")))


def build_plain_type(scene, node):
    return _type_object(scene, node)


# ---- occurrences ---------------------------------------------------------------

def build_slab(scene, node, placement):
    model = scene.model
    pts = [list(p) for p in node["OuterCurve"]]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    ifc_pts = [point(model, float(p[0]), float(p[1])) for p in pts]
    prof = model.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=model.create_entity("IfcPolyline", Points=ifc_pts))
    solid = extrude_up(model, prof, _thickness(_type_of(scene, node)))
    return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", [solid]))


def build_roof(scene, node, placement):
    """Hip roof assembled from per-side panels. Pitch and per-side panel materials come from the
    roof's property set (`PitchAngle`, `PanelMaterial_<Side>` / `PanelMaterial_Default`)."""
    model = scene.model
    pts = node["OuterCurve"]
    xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
    props = _properties(scene, node)
    gable = props.get("GableSide")
    panels = hip_panels(min(xs), min(ys), max(xs), max(ys), float(props.get("PitchAngle", 30.0)),
                        gable.lower() if gable else None, props.get("WestRun"))
    default = props.get("PanelMaterial_Default", "polycarbonate")

    roof = _product(scene, node, placement)
    for side, verts in panels.items():
        material_name = props.get(f"PanelMaterial_{side.capitalize()}", default)
        build_panel(model, scene.context, placement, roof, f"{node['id']}_{side}", verts, material_name)
    return roof


def build_wall(scene, node, placement):
    model = scene.model
    length, thick, height = node["Length"], _thickness(_type_of(scene, node)), node["Height"]
    if node.get("Outline"):  # polygon in the wall's XZ plane, extruded across the thickness
        outline = [tuple(p) for p in node["Outline"]]
        outline.append(outline[0])
        prof = model.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA",
            OuterCurve=model.create_entity("IfcPolyline", Points=[point(model, *p) for p in outline]))
        solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=prof,
            Position=axis_placement_3d(model, (0.0, thick / 2.0, 0.0), axis=(0.0, -1.0, 0.0), ref_direction=(1.0, 0.0, 0.0)),
            ExtrudedDirection=direction(model, 0.0, 0.0, 1.0), Depth=thick)
        return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", [solid]))
    prof_placement = model.create_entity("IfcAxis2Placement2D", Location=point(model, length / 2.0, 0.0))
    prof = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=prof_placement, XDim=length, YDim=thick)
    solid = extrude_up(model, prof, height)
    return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", [solid]))


def build_stair(scene, node, placement):
    """Container only: its flights and landings aggregate into it."""
    return _product(scene, node, placement)


def _flight_steps(rise, rh_min, rh_max):
    """Fewest risers that keep each at or below `rh_max`; the rise is shared evenly between them."""
    n = math.ceil(rise / rh_max - 1e-9)
    if n < 2 or rise / n < rh_min - 1e-9:
        raise ValueError(f"no riser count puts a rise of {rise} m between {rh_min} and {rh_max} m per step")
    return n


def build_stair_flight(scene, node, placement):
    """`Rise` and `Run` are the flight's total height and horizontal length; the riser count, `RiserHeight`
    and `TreadLength` follow from them and the type's `RiserHeightMin` / `RiserHeightMax`."""
    model = scene.model
    props = _properties(scene, _type_of(scene, node))
    w, t = props["Width"], props["TreadThickness"]
    risers = _flight_steps(node["Rise"], props["RiserHeightMin"], props["RiserHeightMax"])
    treads_n = risers - 1
    rh, td = node["Rise"] / risers, node["Run"] / treads_n
    treads = []
    for i in range(treads_n):
        sp = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
            Position=model.create_entity("IfcAxis2Placement2D", Location=point(model, td / 2.0, 0.0)), XDim=td, YDim=w)
        treads.append(extrude_up(model, sp, t, location=(i * td, 0.0, i * rh)))
    return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", treads),
        NumberOfRisers=risers, NumberOfTreads=treads_n, RiserHeight=rh, TreadLength=td)


def build_column(scene, node, placement):
    """Vertical section; Location is the centre of its base, extruded up by `Length`."""
    model = scene.model
    type_node = _type_of(scene, node)
    solid = extrude_up(model, _i_profile(model, type_node["Profile"]), node["Length"])
    _style_solid(model, solid, type_node["Material"])
    return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", [solid]))


def build_beam(scene, node, placement):
    """Horizontal section; Location is the start of its underside centreline, running `Length` along local X."""
    model = scene.model
    type_node = _type_of(scene, node)
    spec = type_node["Profile"]
    prof = _i_profile(model, spec, y_offset=spec["OverallDepth"] / 2.0)
    # profile X -> world Y, profile Y -> world Z, extrusion (local Z) -> world X
    position = axis_placement_3d(model, axis=(1.0, 0.0, 0.0), ref_direction=(0.0, 1.0, 0.0))
    solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=position,
        ExtrudedDirection=direction(model, 0.0, 0.0, 1.0), Depth=node["Length"])
    _style_solid(model, solid, type_node["Material"])
    return _product(scene, node, placement, body_shape(model, scene.context, "SweptSolid", [solid]))


BUILDERS = {
    "IfcColumn": build_column,
    "IfcBeam": build_beam,
    "IfcSlab": build_slab,
    "IfcWall": build_wall,
    "IfcStair": build_stair,
    "IfcStairFlight": build_stair_flight,
    "IfcRoof": build_roof,
}

TYPE_BUILDERS = {
    "IfcBeamType": build_profile_type,
    "IfcColumnType": build_profile_type,
    "IfcWallType": build_layered_type,
    "IfcSlabType": build_layered_type,
    "IfcStairFlightType": build_plain_type,
}
