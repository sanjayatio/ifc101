import json
import math
import ifcopenshell
import ifcopenshell.template

def create_ifc_from_json(json_path, output_ifc_path):
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    model = ifcopenshell.template.create(
        filename=output_ifc_path, schema_identifier="IFC4",
        creator="Developer", application="IFCJSON Translator",
        application_version="1.0", organization="OpenSource"
    )

    # Extract the actual single entity reference from the template list
    project_list = model.by_type("IfcProject")
    project = project_list[0]
    
    body_context = None
    for ctx in model.by_type("IfcGeometricRepresentationSubContext"):
        if ctx.ContextIdentifier == "Body":
            body_context = ctx
            break
    if body_context is None:
        body_context = model.by_type("IfcGeometricRepresentationContext")[0]

    # Spatial Tree Foundations
    site = model.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), Name="Project Site")
    building = model.create_entity("IfcBuilding", GlobalId=ifcopenshell.guid.new(), Name="Main Building")
    
    model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, project, [site])
    model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, site, [building])

    storeys_map = {}
    elements = json_data.get("data", [])

    # Process Global Floor Elevations
    f_height = 2.6  
    for element in elements:
        if element.get("type") == "ProjectGlobal":
            f_height = float(element.get("floor_height", 2.6))

    for storey_name, elev in [("Ground Floor", 0.0), ("First Floor", f_height)]:
        new_storey = model.create_entity("IfcBuildingStorey", GlobalId=ifcopenshell.guid.new(), Name=storey_name, Elevation=elev)
        model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, building, [new_storey])
        storeys_map[storey_name] = new_storey

    # Process Geometry Elements
    for element in elements:
        el_type = element.get("type")
        if el_type not in ["IfcWall", "IfcStair"]:
            continue
            
        storey_name = element.get("storey", "Ground Floor")
        target_storey = storeys_map[storey_name]
        
        pos_x = float(element.get("x", 0.0))
        pos_y = float(element.get("y", 0.0))
        pos_z = float(element.get("z", 0.0))
        rot_deg = float(element.get("rotation", 0.0))
        
        rad = math.radians(rot_deg)
        local_origin = model.create_entity("IfcCartesianPoint", Coordinates=(pos_x, pos_y, pos_z))
        axis_dir = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)) 
        ref_direction = model.create_entity("IfcDirection", DirectionRatios=(round(math.cos(rad), 5), round(math.sin(rad), 5), 0.0)) 
        
        placement_3d = model.create_entity("IfcAxis2Placement3D", Location=local_origin, Axis=axis_dir, RefDirection=ref_direction)
        local_placement = model.create_entity("IfcLocalPlacement", PlacementRelTo=None, RelativePlacement=placement_3d)

        # --- WALL TRANSLATION LOGIC ---
        if el_type == "IfcWall":
            length = float(element.get("length", 3.0))
            thickness = float(element.get("thickness", 0.1))
            height = float(element.get("height", f_height))

            profile_origin = model.create_entity("IfcCartesianPoint", Coordinates=(length / 2.0, 0.0))
            profile_placement = model.create_entity("IfcAxis2Placement2D", Location=profile_origin)
            rectangle_profile = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=profile_placement, XDim=length, YDim=thickness)
            
            extrusion_origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
            extrusion_placement = model.create_entity("IfcAxis2Placement3D", Location=extrusion_origin)
            extrusion_dir = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
            extruded_solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=rectangle_profile, Position=extrusion_placement, ExtrudedDirection=extrusion_dir, Depth=height)
            
            shape_rep = model.create_entity("IfcShapeRepresentation", body_context, "Body", "SweptSolid", [extruded_solid])
            product_definition = model.create_entity("IfcProductDefinitionShape", Representations=[shape_rep])
            
            ifc_wall = model.create_entity("IfcWall", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), ObjectPlacement=local_placement, Representation=product_definition)
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [ifc_wall], target_storey)

        # --- STAIR TRANSLATION LOGIC (CORRECTED U-SHAPE SYSTEM) ---
        elif el_type == "IfcStair":
            width = float(element.get("width", 1.0))      
            f_run = float(element.get("flight_run", 2.0))  
            f_rise = float(element.get("flight_rise", 1.3))
            t_thick = float(element.get("tread_thickness", 0.03)) 
            
            num_risers = 7
            riser_h = f_rise / num_risers
            tread_d = f_run / (num_risers - 1)
            
            stair_components = []
            e_dir = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
            
            # Flight 1: Primary Ascending Run (Shifted Left Track)
            for i in range(num_risers - 1):
                p_origin = model.create_entity("IfcCartesianPoint", Coordinates=(tread_d / 2.0, width / 2.0))
                p_placement = model.create_entity("IfcAxis2Placement2D", Location=p_origin)
                step_profile = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=p_placement, XDim=tread_d, YDim=width)
                
                z_offset = i * riser_h
                x_offset = i * tread_d
                e_origin = model.create_entity("IfcCartesianPoint", Coordinates=(x_offset, 0.0, z_offset))
                e_placement = model.create_entity("IfcAxis2Placement3D", Location=e_origin)
                
                solid_tread = model.create_entity("IfcExtrudedAreaSolid", SweptArea=step_profile, Position=e_placement, ExtrudedDirection=e_dir, Depth=t_thick)
                stair_components.append(solid_tread)
                
            # Midpoint Turning Landing: 1.0m x 2.0m Solid Boundary Rectangle
            l_origin = model.create_entity("IfcCartesianPoint", Coordinates=(width / 2.0, width))
            l_placement = model.create_entity("IfcAxis2Placement2D", Location=l_origin)
            landing_profile = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=l_placement, XDim=width, YDim=width * 2.0)
            
            le_origin = model.create_entity("IfcCartesianPoint", Coordinates=(f_run, 0.0, f_rise - t_thick))
            le_placement = model.create_entity("IfcAxis2Placement3D", Location=le_origin)
            solid_landing = model.create_entity("IfcExtrudedAreaSolid", SweptArea=landing_profile, Position=le_placement, ExtrudedDirection=e_dir, Depth=t_thick)
            stair_components.append(solid_landing)

            # Flight 2: Parallel Returning Run (Flushed Right Track)
            for i in range(num_risers - 1):
                p_origin = model.create_entity("IfcCartesianPoint", Coordinates=(tread_d / 2.0, width / 2.0))
                p_placement = model.create_entity("IfcAxis2Placement2D", Location=p_origin)
                step_profile = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=p_placement, XDim=tread_d, YDim=width)
                
                z_offset = f_rise + (i * riser_h)
                x_offset = f_run - tread_d - (i * tread_d)
                e_origin = model.create_entity("IfcCartesianPoint", Coordinates=(x_offset, width, z_offset))
                e_placement = model.create_entity("IfcAxis2Placement3D", Location=e_origin)
                
                solid_tread = model.create_entity("IfcExtrudedAreaSolid", SweptArea=step_profile, Position=e_placement, ExtrudedDirection=e_dir, Depth=t_thick)
                stair_components.append(solid_tread)

            # --- RESTORED COMPILATION ENGINE BLOCK FOR STAIRS ---
            shape_rep = model.create_entity("IfcShapeRepresentation", body_context, "Body", "SweptSolid", [stair_components[0]])
            shape_rep.Items = stair_components
            product_definition = model.create_entity("IfcProductDefinitionShape", Representations=[shape_rep])
            
            ifc_stair = model.create_entity("IfcStair", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), ObjectPlacement=local_placement, Representation=product_definition)
            
            # SAFE SPATIAL CONTAINMENT INSIDE STAIR SCOPE
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [ifc_stair], target_storey)

    model.write(output_ifc_path)
    print(f"🚀 IFC model generated successfully with correct spatial tree references and stairs!")

if __name__ == "__main__":
    create_ifc_from_json("building.ifcjson", "building.ifc")
