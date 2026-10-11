import math, ifcopenshell


def new_guid():
    return ifcopenshell.guid.new()


def point(model, *coords):
    return model.create_entity("IfcCartesianPoint", Coordinates=tuple(coords))


def direction(model, *ratios):
    return model.create_entity("IfcDirection", DirectionRatios=tuple(ratios))


def axis_placement_3d(model, location=(0.0, 0.0, 0.0), axis=None, ref_direction=None):
    kwargs = {"Location": point(model, *location)}
    if axis is not None:
        kwargs["Axis"] = direction(model, *axis)
    if ref_direction is not None:
        kwargs["RefDirection"] = direction(model, *ref_direction)
    return model.create_entity("IfcAxis2Placement3D", **kwargs)


def local_placement(model, x, y, z, rotation_deg):
    rad = math.radians(rotation_deg)
    placement_3d = axis_placement_3d(
        model, (x, y, z),
        axis=(0.0, 0.0, 1.0),
        ref_direction=(round(math.cos(rad), 5), round(math.sin(rad), 5), 0.0))
    return model.create_entity("IfcLocalPlacement", PlacementRelTo=None, RelativePlacement=placement_3d)


def extrude_up(model, profile, depth, location=(0.0, 0.0, 0.0)):
    return model.create_entity("IfcExtrudedAreaSolid", SweptArea=profile,
        Position=axis_placement_3d(model, location),
        ExtrudedDirection=direction(model, 0.0, 0.0, 1.0), Depth=depth)


def body_shape(model, context, rep_type, items):
    shape = model.create_entity("IfcShapeRepresentation", context, "Body", rep_type, items)
    return model.create_entity("IfcProductDefinitionShape", Representations=[shape])


def add_to_storey(model, product, storey):
    model.create_entity("IfcRelContainedInSpatialStructure", new_guid(), None, None, None, [product], storey)


def aggregate(model, parent, child):
    model.create_entity("IfcRelAggregates", new_guid(), None, None, None, parent, [child])


def create_face(model, points):
    bound = model.create_entity("IfcFaceOuterBound", Bound=model.create_entity("IfcPolyLoop", Polygon=points), Orientation=True)
    return model.create_entity("IfcFace", Bounds=[bound])


def identity_placement(model, relative_to=None):
    return model.create_entity("IfcLocalPlacement", PlacementRelTo=relative_to, RelativePlacement=axis_placement_3d(model))


def get_material(model, name, color, transparency=0.0):
    """Return (IfcMaterial, IfcSurfaceStyle) for `name`, creating them on first use."""
    material = next((m for m in model.by_type("IfcMaterial") if m.Name == name), None)
    if material is not None:
        style = next(s for s in model.by_type("IfcSurfaceStyle") if s.Name == name)
        return material, style
    rendering = model.create_entity("IfcSurfaceStyleRendering",
        SurfaceColour=model.create_entity("IfcColourRgb", Red=color[0], Green=color[1], Blue=color[2]),
        Transparency=transparency, ReflectanceMethod="NOTDEFINED")
    style = model.create_entity("IfcSurfaceStyle", Name=name, Side="BOTH", Styles=[rendering])
    return model.create_entity("IfcMaterial", Name=name), style


def assign_material(model, product, material):
    model.create_entity("IfcRelAssociatesMaterial", new_guid(), None, None, None, [product], material)


def style_item(model, item, style):
    model.create_entity("IfcStyledItem", Item=item, Styles=[style])
