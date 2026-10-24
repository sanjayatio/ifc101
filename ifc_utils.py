import uuid, ifcopenshell

_GUID_NAMESPACE = uuid.UUID("5c1f3a54-8f0e-4d7b-9a53-2b6e7d1c0f42")


def new_guid():
    return ifcopenshell.guid.new()


def guid_for(key):
    """Stable IfcGloballyUniqueId derived from a node's JSON `id`, so a node keeps its identity across regenerations."""
    return ifcopenshell.guid.compress(uuid.uuid5(_GUID_NAMESPACE, key).hex)


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


def local_placement(model, location, ref_direction=(1.0, 0.0, 0.0), relative_to=None):
    placement_3d = axis_placement_3d(model, location, axis=(0.0, 0.0, 1.0), ref_direction=ref_direction)
    return model.create_entity("IfcLocalPlacement", PlacementRelTo=relative_to, RelativePlacement=placement_3d)


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


def plain_material(model, name):
    """IfcMaterial for `name` without a surface style, created on first use."""
    return next((m for m in model.by_type("IfcMaterial") if m.Name == name), None) or model.create_entity("IfcMaterial", Name=name)


def assign_material(model, obj, material):
    """`material` is any IfcMaterialSelect (material, layer set, profile set); `obj` an element or type."""
    model.create_entity("IfcRelAssociatesMaterial", new_guid(), None, None, None, [obj], material)


def define_by_type(model, product, type_object):
    """A type has at most one IfcRelDefinesByType; later occurrences join its RelatedObjects."""
    rel = next(iter(type_object.Types), None)
    if rel is None:
        model.create_entity("IfcRelDefinesByType", new_guid(), None, None, None, [product], type_object)
    else:
        rel.RelatedObjects = [*rel.RelatedObjects, product]


def define_by_properties(model, product, pset):
    """A property set has at most one IfcRelDefinesByProperties; later occurrences join its RelatedObjects."""
    rel = next(iter(pset.DefinesOccurrence), None)
    if rel is None:
        model.create_entity("IfcRelDefinesByProperties", new_guid(), None, None, None, [product], pset)
    else:
        rel.RelatedObjects = [*rel.RelatedObjects, product]


def nominal_value(model, value):
    if isinstance(value, bool):
        return model.create_entity("IfcBoolean", value)
    if isinstance(value, (int, float)):
        return model.create_entity("IfcReal", float(value))
    return model.create_entity("IfcLabel", value)


def property_set(model, node):
    props = [model.create_entity("IfcPropertySingleValue", Name=name, NominalValue=nominal_value(model, value))
             for name, value in node["HasProperties"].items()]
    return model.create_entity("IfcPropertySet", GlobalId=guid_for(node["id"]), Name=node.get("Name"),
                               Description=node.get("Description"), HasProperties=props)


def style_item(model, item, style):
    model.create_entity("IfcStyledItem", Item=item, Styles=[style])
