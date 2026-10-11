import json, ifcopenshell, ifcopenshell.template
from ifc_utils import new_guid, aggregate, local_placement
from ifc_components import BUILDERS


def create_ifc_from_json(json_path, output_ifc_path):
    with open(json_path, 'r') as f:
        elements = json.load(f).get("data", [])

    model = ifcopenshell.template.create(filename=output_ifc_path, schema_identifier="IFC4")

    project = model.by_type("IfcProject")[0]
    project.Name = "BIM_Exploration_Project"

    body_context = next((c for c in model.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body"), model.by_type("IfcGeometricRepresentationContext")[0])

    site = model.create_entity("IfcSite", GlobalId=new_guid(), Name="Project Site")
    building = model.create_entity("IfcBuilding", GlobalId=new_guid(), Name="Main Building")
    aggregate(model, project, site)
    aggregate(model, site, building)

    f_height = next((float(e.get("floor_height", 2.6)) for e in elements if e.get("type") == "ProjectGlobal"), 2.6)

    storeys_map = {}
    for name, elev in [("Ground Floor", 0.0), ("First Floor", f_height), ("Second Floor", f_height * 2.0)]:
        st = model.create_entity("IfcBuildingStorey", GlobalId=new_guid(), Name=name, Elevation=elev)
        aggregate(model, building, st)
        storeys_map[name] = st

    for element in elements:
        builder = BUILDERS.get(element.get("type"))
        if builder is None:
            continue
        storey = storeys_map[element.get("storey", "Ground Floor")]
        placement = local_placement(model, float(element.get("x", 0.0)), float(element.get("y", 0.0)),
                                    float(element.get("z", 0.0)), float(element.get("rotation", 0.0)))
        builder(model, element, body_context, placement, storey, f_height)

    model.write(output_ifc_path)
    print(f"🚀 SUCCESS: Model with Hip Roof generated completely inside '{output_ifc_path}'")


if __name__ == "__main__":
    create_ifc_from_json("building.ifcjson", "building.ifc")
