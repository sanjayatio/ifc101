import argparse, json, ifcopenshell, ifcopenshell.template
from pathlib import Path
from types import SimpleNamespace
from ifc_utils import guid_for, aggregate, local_placement, add_to_storey, define_by_type, define_by_properties, property_set
from ifc_components import BUILDERS, TYPE_BUILDERS

INPUT_NAME, OUTPUT_NAME = "design.ifcjson", "render.ifc"
SPATIAL = {"IfcSite", "IfcBuilding", "IfcBuildingStorey"}


def build_spatial(scene, node):
    attrs = {k: node[k] for k in ("Elevation",) if k in node}
    return scene.model.create_entity(node["type"], GlobalId=guid_for(node["id"]), Name=node.get("Name"), **attrs)


def build_node(scene, node):
    """Create the IFC entity for one node; parents, types and property sets must appear earlier in the file."""
    kind, model = node["type"], scene.model
    if kind == "IfcProject":
        project = model.by_type("IfcProject")[0]
        project.GlobalId, project.Name = guid_for(node["id"]), node.get("Name")
        return project
    if kind in SPATIAL:
        return build_spatial(scene, node)
    if kind == "IfcPropertySet":
        return property_set(model, node)
    if kind in TYPE_BUILDERS:
        return TYPE_BUILDERS[kind](scene, node)

    parent = scene.entities.get(node.get("Decomposes"))
    placement = local_placement(model, node.get("Location", (0.0, 0.0, 0.0)), node.get("RefDirection", (1.0, 0.0, 0.0)),
                                getattr(parent, "ObjectPlacement", None))
    return BUILDERS[kind](scene, node, placement)


def relate(scene, node, entity):
    model, entities = scene.model, scene.entities
    if "Decomposes" in node:
        aggregate(model, entities[node["Decomposes"]], entity)
    if "ContainedIn" in node:
        add_to_storey(model, entity, entities[node["ContainedIn"]])
    if node["type"] in BUILDERS:  # occurrences only; types carry their property sets as HasPropertySets
        if "IsTypedBy" in node:
            define_by_type(model, entity, entities[node["IsTypedBy"]])
        for pset_id in node.get("HasPropertySets", []):
            define_by_properties(model, entity, entities[pset_id])


def create_ifc_from_folder(folder):
    json_path, output_ifc_path = Path(folder) / INPUT_NAME, Path(folder) / OUTPUT_NAME
    with open(json_path, 'r') as f:
        nodes = json.load(f).get("data", [])

    # the name lands in the STEP header, where a path's backslashes would be read as escape sequences
    model = ifcopenshell.template.create(filename=output_ifc_path.name, schema_identifier="IFC4")
    body_context = next((c for c in model.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body"), model.by_type("IfcGeometricRepresentationContext")[0])
    scene = SimpleNamespace(model=model, context=body_context, nodes={n["id"]: n for n in nodes}, entities={})

    for node in nodes:
        entity = build_node(scene, node)
        scene.entities[node["id"]] = entity
        relate(scene, node, entity)

    model.write(str(output_ifc_path))
    print(f"🚀 SUCCESS: Model with Hip Roof generated completely inside '{output_ifc_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Build {OUTPUT_NAME} from {INPUT_NAME} inside a project folder.")
    parser.add_argument("folder", help=f"project folder holding {INPUT_NAME}; {OUTPUT_NAME} is written next to it")
    create_ifc_from_folder(parser.parse_args().folder)
