import math
from ifc_utils import (new_guid, point, create_face, add_to_storey, aggregate, identity_placement,
                       body_shape, get_material, assign_material, style_item)

# name -> (RGB colour, transparency, panel thickness in metres)
ROOF_MATERIALS = {
    "metal":         ((0.62, 0.65, 0.68), 0.0, 0.03),
    "polycarbonate": ((0.70, 0.88, 0.95), 0.6, 0.01),
}


# ---- panel shape ---------------------------------------------------------------

def roof_panel(corners):
    """The corners (x, y, z) of one sloped panel: 3 or 4 of them, and a fourth must lie in the plane of the first three."""
    assert len(corners) in (3, 4), "a roof panel has 3 or 4 corners"
    if len(corners) == 4:
        n = _normal(corners[:3])
        off = sum(n[i] * (corners[3][i] - corners[0][i]) for i in range(3))
        assert abs(off) < 1e-6, f"the 4 corners are not in one plane (off by {off:.4f} m)"
    return [tuple(float(c) for c in v) for v in corners]


# ---- panel solid -------------------------------------------------------------

def _normal(verts):
    """Newell normal, normalised."""
    nx = ny = nz = 0.0
    for (x0, y0, z0), (x1, y1, z1) in zip(verts, verts[1:] + verts[:1]):
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    n = math.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / n, ny / n, nz / n


def panel_solid(model, verts, thickness):
    """Closed Brep: the polygon `verts` extruded along its upward normal by `thickness`."""
    if _normal(verts)[2] < 0:
        verts = verts[::-1]
    n = _normal(verts)
    top = [tuple(c + n[i] * thickness for i, c in enumerate(v)) for v in verts]
    bp = [point(model, *v) for v in verts]
    tp = [point(model, *v) for v in top]
    k = len(verts)
    faces = [create_face(model, tp), create_face(model, bp[::-1])]
    faces += [create_face(model, [bp[i], bp[(i + 1) % k], tp[(i + 1) % k], tp[i]]) for i in range(k)]
    return model.create_entity("IfcFacetedBrep", Outer=model.create_entity("IfcClosedShell", CfsFaces=faces))


def build_panel(model, context, roof_placement, roof, name, verts, material_name):
    color, transparency, thickness = ROOF_MATERIALS[material_name]
    material, style = get_material(model, material_name, color, transparency)
    solid = panel_solid(model, verts, thickness)
    style_item(model, solid, style)
    panel = model.create_entity("IfcSlab", GlobalId=new_guid(), Name=f"{name}_{material_name}", PredefinedType="ROOF",
        ObjectPlacement=identity_placement(model, roof_placement), Representation=body_shape(model, context, "Brep", [solid]))
    assign_material(model, panel, material)
    aggregate(model, roof, panel)
