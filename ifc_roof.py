import math
from ifc_utils import (new_guid, point, create_face, add_to_storey, aggregate, identity_placement,
                       body_shape, get_material, assign_material, style_item)

# name -> (RGB colour, transparency, panel thickness in metres)
ROOF_MATERIALS = {
    "metal":         ((0.62, 0.65, 0.68), 0.0, 0.03),
    "polycarbonate": ((0.70, 0.88, 0.95), 0.6, 0.01),
}


# ---- panel shapes: each returns a list of (x, y, z) vertices ----------------

def isosceles_triangle(base_a, base_b, apex):
    assert math.isclose(math.dist(base_a, apex), math.dist(base_b, apex), rel_tol=1e-6), "apex is not equidistant from base ends"
    return [base_a, base_b, apex]


def right_triangle(corner, leg_a, leg_b):
    va = [a - c for a, c in zip(leg_a, corner)]
    vb = [b - c for b, c in zip(leg_b, corner)]
    assert math.isclose(sum(x * y for x, y in zip(va, vb)), 0.0, abs_tol=1e-6), "legs are not perpendicular"
    return [corner, leg_a, leg_b]


def slanted_rectangle(origin, along, rise):
    """Rectangle spanning `along` (horizontal edge vector) and `rise` (sloped edge vector, perpendicular to `along`)."""
    assert math.isclose(sum(x * y for x, y in zip(along, rise)), 0.0, abs_tol=1e-6), "edges are not perpendicular"
    o = origin
    return [o, tuple(a + b for a, b in zip(o, along)),
            tuple(a + b + c for a, b, c in zip(o, along, rise)), tuple(a + b for a, b in zip(o, rise))]


def trapezoid(a, b, c, d):
    return [a, b, c, d]


# ---- hip roof layout ---------------------------------------------------------

def hip_panels(min_x, min_y, max_x, max_y, pitch_deg):
    """Faces of a hip roof over a rectangle, keyed by side (south = min_y)."""
    half = (max_x - min_x) / 2.0
    h = half * math.tan(math.radians(pitch_deg))
    rx = min_x + half
    sw, se = (min_x, min_y, 0.0), (max_x, min_y, 0.0)
    ne, nw = (max_x, max_y, 0.0), (min_x, max_y, 0.0)
    r_s, r_n = (rx, min_y + half, h), (rx, max_y - half, h)
    return {
        "south": isosceles_triangle(sw, se, r_s),
        "east":  trapezoid(se, ne, r_n, r_s),
        "north": isosceles_triangle(ne, nw, r_n),
        "west":  trapezoid(nw, sw, r_s, r_n),
    }


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
