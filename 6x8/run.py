import json
import math
import ifcopenshell
import ifcopenshell.template

def create_ifc_from_json(json_path, output_ifc_path):
    # Load the ifcjson data safely
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Initialize a clean IFC4 file using correct template parameters
    model = ifcopenshell.template.create(
        filename=output_ifc_path,
        schema_identifier="IFC4",
        creator="Developer",
        application="IFCJSON Translator",
        application_version="1.0",
        organization="OpenSource"
    )

    # 1. Retrieve the template's pre-configured geometric contexts
    project = model.by_type("IfcProject")[0]
    # global_context = model.by_type("IfcGeometricRepresentationContext")[0]

    
    # Locate the built-in 'Body' sub-context automatically provided by the template
    body_context = None
    for ctx in model.by_type("IfcGeometricRepresentationSubContext"):
        if ctx.ContextIdentifier == "Body":
            body_context = ctx
            break
            
    # Fallback to global if body isn't explicitly found
    if body_context is None:
        body_context = model.by_type("IfcGeometricRepresentationContext")[0]	

    # Create spatial baseline elements
    site = model.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), Name="Project Site")
    building = model.create_entity("IfcBuilding", GlobalId=ifcopenshell.guid.new(), Name="Main Building")
    
    # Establish base tree linkage
    model.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=project, RelatedObjects=[site])
    model.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=site, RelatedObjects=[building])

    # Dynamic storey registry map
    storeys_map = {}
    elements = json_data.get("data", [])

    for element in elements:
        if element.get("type") != "IfcWall":
            continue
            
        storey_name = element.get("storey", "Ground Floor")
        
        # Dynamically build and map storeys as they appear in the JSON layout
        if storey_name not in storeys_map:
            elevation = 0.0 if "Ground" in storey_name else 2800.0
            new_storey = model.create_entity(
                "IfcBuildingStorey", 
                GlobalId=ifcopenshell.guid.new(), 
                Name=storey_name,
                Elevation=elevation
            )
            model.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=building, RelatedObjects=[new_storey])
            storeys_map[storey_name] = new_storey

        # Extract structural tracking properties from JSON
        w_id = element.get("id")
        w_name = element.get("name", w_id)
        pos_x = float(element.get("x", 0.0))
        pos_y = float(element.get("y", 0.0))
        pos_z = float(element.get("z", 0.0))
        rotation_deg = float(element.get("rotation", 0.0))
        
        length = float(element.get("length", 3000.0))
        thickness = float(element.get("thickness", 100.0))
        height = float(element.get("height", 2800.0))

        # 2. Build Structural 3D Transform Matrices
        rad = math.radians(rotation_deg)
        cos_a = round(math.cos(rad), 4)
        sin_a = round(math.sin(rad), 4)

        local_origin = model.create_entity("IfcCartesianPoint", Coordinates=(pos_x, pos_y, pos_z))
        axis_dir = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)) 
        ref_direction = model.create_entity("IfcDirection", DirectionRatios=(cos_a, sin_a, 0.0)) 
        
        wall_placement_3d = model.create_entity(
            "IfcAxis2Placement3D", 
            Location=local_origin, 
            Axis=axis_dir, 
            RefDirection=ref_direction
        )
        wall_local_placement = model.create_entity(
            "IfcLocalPlacement", 
            PlacementRelTo=None, 
            RelativePlacement=wall_placement_3d
        )

        # 3. Create 2D Profile Footprint with Corner Correction Alignment
        # Offset the center by half length and half thickness to align the wall's start point to your exact coordinates
        profile_origin = model.create_entity("IfcCartesianPoint", Coordinates=(length / 2.0, thickness / 2.0))
        profile_placement = model.create_entity("IfcAxis2Placement2D", Location=profile_origin)
        
        rectangle_profile = model.create_entity(
            "IfcRectangleProfileDef", 
            ProfileType="AREA", 
            ProfileName=f"Profile-{w_id}", 
            Position=profile_placement, 
            XDim=length, 
            YDim=thickness
        )

        # 4. Extrude standard body upward
        extrusion_origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
        extrusion_placement = model.create_entity("IfcAxis2Placement3D", Location=extrusion_origin)
        extrusion_dir = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
        
        extruded_solid = model.create_entity(
            "IfcExtrudedAreaSolid", 
            SweptArea=rectangle_profile, 
            Position=extrusion_placement, 
            ExtrudedDirection=extrusion_dir, 
            Depth=height
        )

        # 5. Bind geometric data to the Body SubContext (Fixes 3D Orbit Rendering)
        shape_rep = model.create_entity(
            "IfcShapeRepresentation", 
            ContextOfItems=body_context,  # Explicit sub-context target
            RepresentationIdentifier="Body", 
            RepresentationType="SweptSolid", 
            Items=[extruded_solid]
        )
        product_definition = model.create_entity("IfcProductDefinitionShape", Representations=[shape_rep])

        # 6. Instantiate Wall object
        ifc_wall = model.create_entity(
            "IfcWall", 
            GlobalId=ifcopenshell.guid.new(), 
            Name=w_name, 
            ObjectPlacement=wall_local_placement, 
            Representation=product_definition
        )

        # 7. Route wall to its designated storey spatial index 
        target_storey = storeys_map[storey_name]
        model.create_entity(
            "IfcRelContainedInSpatialStructure", 
            GlobalId=ifcopenshell.guid.new(), 
            RelatingStructure=target_storey, 
            RelatedElements=[ifc_wall]
        )

    # Save to building.ifc
    model.write(output_ifc_path)
    print(f"✅ Clean translation complete! Box alignment and viewport context tracking corrected.")

if __name__ == "__main__":
    create_ifc_from_json("building.ifcjson", "building.ifc")
