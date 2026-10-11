from ifc_roof import hip_panels, build_panel
from ifc_utils import (new_guid, point, direction, extrude_up, body_shape,
                       add_to_storey, create_face, axis_placement_3d,
                       get_material, assign_material, style_item)


def build_slab(model, element, context, placement, storey, floor_height):
    pts = element.get("points", [])
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    ifc_pts = [point(model, float(p[0]), float(p[1])) for p in pts]
    prof = model.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=model.create_entity("IfcPolyline", Points=ifc_pts))
    solid = extrude_up(model, prof, float(element.get("thickness", 0.2)))
    slab = model.create_entity("IfcSlab", GlobalId=new_guid(), Name=element.get("name"), PredefinedType="FLOOR",
        ObjectPlacement=placement, Representation=body_shape(model, context, "SweptSolid", [solid]))
    add_to_storey(model, slab, storey)


def build_roof(model, element, context, placement, storey, floor_height):
    """Hip roof assembled from per-side panels; `panel_materials` maps a side
    (south/east/north/west) or "default" to a ROOF_MATERIALS key."""
    pts = element.get("points", [])
    if not pts:
        return
    xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
    panels = hip_panels(min(xs), min(ys), max(xs), max(ys), float(element.get("pitch", 30.0)))
    materials = element.get("panel_materials", {})

    roof = model.create_entity("IfcRoof", GlobalId=new_guid(), Name=element.get("name"), PredefinedType="HIP_ROOF",
        ObjectPlacement=placement)
    for side, verts in panels.items():
        material_name = materials.get(side, materials.get("default", "polycarbonate"))
        build_panel(model, context, placement, roof, f"{element.get('name')}_{side}", verts, material_name)
    add_to_storey(model, roof, storey)


def build_wall(model, element, context, placement, storey, floor_height):
    length = float(element.get("length", 3.0))
    thick = float(element.get("thickness", 0.1))
    height = float(element.get("height", floor_height))
    prof_placement = model.create_entity("IfcAxis2Placement2D", Location=point(model, length / 2.0, 0.0))
    prof = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=prof_placement, XDim=length, YDim=thick)
    solid = extrude_up(model, prof, height)
    wall = model.create_entity("IfcWall", GlobalId=new_guid(), Name=element.get("name"),
        ObjectPlacement=placement, Representation=body_shape(model, context, "SweptSolid", [solid]))
    add_to_storey(model, wall, storey)


def build_stair(model, element, context, placement, storey, floor_height):
    w = float(element.get("width", 1.0))
    r = float(element.get("flight_run", 2.0))
    h = float(element.get("flight_rise", 1.3))
    t = float(element.get("tread_thickness", 0.03))
    num = 7
    rh, td = h / num, r / (num - 1)
    treads = []
    for i in range(num - 1):
        sp = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=point(model, td / 2.0, w / 2.0), XDim=td, YDim=w)
        treads.append(extrude_up(model, sp, t, location=(i * td, 0.0, i * rh)))
    stair = model.create_entity("IfcStair", GlobalId=new_guid(), Name=element.get("name"),
        ObjectPlacement=placement, Representation=body_shape(model, context, "SweptSolid", treads))
    add_to_storey(model, stair, storey)


# (flange width, depth, web thickness, flange thickness) in metres
H_BEAM_150x150 = (0.15, 0.15, 0.007, 0.010)
WF_200x100 = (0.10, 0.20, 0.0055, 0.008)
WF_150x75 = (0.075, 0.15, 0.005, 0.007)


def _i_profile(model, element, section, y_offset=0.0):
    width, depth, web, flange = section
    return model.create_entity("IfcIShapeProfileDef", ProfileType="AREA",
        Position=model.create_entity("IfcAxis2Placement2D", Location=point(model, 0.0, y_offset)),
        OverallWidth=float(element.get("flange_width", width)), OverallDepth=float(element.get("depth", depth)),
        WebThickness=float(element.get("web_thickness", web)), FlangeThickness=float(element.get("flange_thickness", flange)))


def _beam_section(element):
    """Main beams run along the long side (Y, rotation 90); secondary beams along the short side (X)."""
    return WF_200x100 if abs(float(element.get("rotation", 0.0))) % 180.0 == 90.0 else WF_150x75


def _finish_steel(model, product, solid, storey):
    material, style = get_material(model, "Steel_Black", (0.0, 0.0, 0.0))
    style_item(model, solid, style)
    assign_material(model, product, material)
    add_to_storey(model, product, storey)


def build_column(model, element, context, placement, storey, floor_height):
    """Vertical H-beam column; (x, y, z) is the centre of its base, extruded up by `height`."""
    prof = _i_profile(model, element, H_BEAM_150x150)
    solid = extrude_up(model, prof, float(element.get("height", floor_height)))
    column = model.create_entity("IfcColumn", GlobalId=new_guid(), Name=element.get("name"), PredefinedType="COLUMN",
        ObjectPlacement=placement, Representation=body_shape(model, context, "SweptSolid", [solid]))
    _finish_steel(model, column, solid, storey)


def build_beam(model, element, context, placement, storey, floor_height):
    """Horizontal I-beam; (x, y, z) is the start of its underside centreline, running `length` along local X."""
    section = _beam_section(element)
    depth = float(element.get("depth", section[1]))
    prof = _i_profile(model, element, section, y_offset=depth / 2.0)
    # profile X -> world Y, profile Y -> world Z, extrusion (local Z) -> world X
    position = axis_placement_3d(model, axis=(1.0, 0.0, 0.0), ref_direction=(0.0, 1.0, 0.0))
    solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=position,
        ExtrudedDirection=direction(model, 0.0, 0.0, 1.0), Depth=float(element.get("length", 3.0)))
    beam = model.create_entity("IfcBeam", GlobalId=new_guid(), Name=element.get("name"), PredefinedType="BEAM",
        ObjectPlacement=placement, Representation=body_shape(model, context, "SweptSolid", [solid]))
    _finish_steel(model, beam, solid, storey)


BUILDERS = {
    "IfcColumn": build_column,
    "IfcBeam": build_beam,
    "IfcSlab": build_slab,
    "IfcWall": build_wall,
    "IfcStair": build_stair,
    "IfcRoof": build_roof,
}
