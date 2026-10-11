import json, math, ifcopenshell, ifcopenshell.template

def create_ifc_from_json(json_path, output_ifc_path):
    with open(json_path, 'r') as f:
        elements = json.load(f).get("data", [])
    
    model = ifcopenshell.template.create(filename=output_ifc_path, schema_identifier="IFC4")
    
    project = model.by_type("IfcProject")[0]
    project.Name = "BIM_Exploration_Project"
    
    body_context = next((c for c in model.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body"), model.by_type("IfcGeometricRepresentationContext")[0])
    
    site = model.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), Name="Project Site")
    building = model.create_entity("IfcBuilding", GlobalId=ifcopenshell.guid.new(), Name="Main Building")
    
    model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, project, [site])
    model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, site, [building])

    f_height = next((float(e.get("floor_height", 2.6)) for e in elements if e.get("type") == "ProjectGlobal"), 2.6)
    
    storeys_map = {}
    for name, elev in [("Ground Floor", 0.0), ("First Floor", f_height), ("Second Floor", f_height * 2.0)]:
        st = model.create_entity("IfcBuildingStorey", GlobalId=ifcopenshell.guid.new(), Name=name, Elevation=elev)
        model.create_entity("IfcRelAggregates", ifcopenshell.guid.new(), None, None, None, building, [st])
        storeys_map[name] = st

    for element in elements:
        el_type = element.get("type")
        if el_type not in ["IfcSlab", "IfcWall", "IfcStair", "IfcRoof"]: continue
        
        target_storey = storeys_map[element.get("storey", "Ground Floor")]
        px, py, pz = float(element.get("x", 0.0)), float(element.get("y", 0.0)), float(element.get("z", 0.0))
        rad = math.radians(float(element.get("rotation", 0.0)))
        
        placement_3d = model.create_entity("IfcAxis2Placement3D", 
            Location=model.create_entity("IfcCartesianPoint", Coordinates=(px, py, pz)),
            Axis=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            RefDirection=model.create_entity("IfcDirection", DirectionRatios=(round(math.cos(rad), 5), round(math.sin(rad), 5), 0.0)))
        local_placement = model.create_entity("IfcLocalPlacement", PlacementRelTo=None, RelativePlacement=placement_3d)

        # --- SLAB TRANSLATION ---
        if el_type == "IfcSlab":
            pts = element.get("points", [])
            if pts and pts[0] != pts[-1]:
                pts.append(pts[0])
            ifc_pts = [model.create_entity("IfcCartesianPoint", Coordinates=(float(p[0]), float(p[1]))) for p in pts]
            prof = model.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=model.create_entity("IfcPolyline", Points=ifc_pts))
            solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, 
                Position=model.create_entity("IfcAxis2Placement3D", Location=model.create_entity("IfcCartesianPoint", Coordinates=(0.0,0.0,0.0))), 
                ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0,0.0,1.0)), Depth=float(element.get("thickness", 0.2)))
            shape = model.create_entity("IfcShapeRepresentation", body_context, "Body", "SweptSolid", [solid])
            slab = model.create_entity("IfcSlab", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), PredefinedType="FLOOR", ObjectPlacement=local_placement, Representation=model.create_entity("IfcProductDefinitionShape", Representations=[shape]))
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [slab], target_storey)

        # --- ROOF TRANSLATION (FIXED HIP ROOF BREP ROUTINE) ---
        elif el_type == "IfcRoof":
            pts = element.get("points", [])
            if not pts: continue
            
            x_coords = [float(p[0]) for p in pts]
            y_coords = [float(p[1]) for p in pts]
            
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            width = max_x - min_x
            length = max_y - min_y
            
            pitch_deg = 30.0
            pitch_rad = math.radians(pitch_deg)
            half_width = width / 2.0
            roof_height = half_width * math.tan(pitch_rad)
            
            ridge_y_start = min_y + half_width
            ridge_y_end = max_y - half_width
            ridge_x = min_x + half_width
            
            v0 = model.create_entity("IfcCartesianPoint", Coordinates=(min_x, min_y, 0.0))
            v1 = model.create_entity("IfcCartesianPoint", Coordinates=(max_x, min_y, 0.0))
            v2 = model.create_entity("IfcCartesianPoint", Coordinates=(max_x, max_y, 0.0))
            v3 = model.create_entity("IfcCartesianPoint", Coordinates=(min_x, max_y, 0.0))
            v4 = model.create_entity("IfcCartesianPoint", Coordinates=(ridge_x, ridge_y_start, roof_height))
            v5 = model.create_entity("IfcCartesianPoint", Coordinates=(ridge_x, ridge_y_end, roof_height))
            
            def create_face(points_list):
                bounds = model.create_entity("IfcFaceOuterBound", Bound=model.create_entity("IfcPolyLoop", Polygon=points_list), Orientation=True)
                return model.create_entity("IfcFace", Bounds=[bounds])
            
            f_south = create_face([v0, v1, v4])
            f_east = create_face([v1, v2, v5, v4])
            f_north = create_face([v2, v3, v5])
            f_west = create_face([v3, v0, v4, v5])
            f_bottom = create_face([v3, v2, v1, v0])
            
            closed_shell = model.create_entity("IfcClosedShell", CfsFaces=[f_south, f_east, f_north, f_west, f_bottom])
            solid = model.create_entity("IfcFacetedBrep", Outer=closed_shell)
            
            shape = model.create_entity("IfcShapeRepresentation", body_context, "Body", "Brep", [solid])
            roof = model.create_entity("IfcRoof", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), PredefinedType="HIP_ROOF", ObjectPlacement=local_placement, Representation=model.create_entity("IfcProductDefinitionShape", Representations=[shape]))
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [roof], target_storey)

        # --- WALL TRANSLATION ---
        elif el_type == "IfcWall":
            length, thick, height = float(element.get("length", 3.0)), float(element.get("thickness", 0.1)), float(element.get("height", f_height))
            wall_profile_origin = model.create_entity("IfcCartesianPoint", Coordinates=(length / 2.0, 0.0))
            prof_placement = model.create_entity("IfcAxis2Placement2D", Location=wall_profile_origin)
            prof = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=prof_placement, XDim=length, YDim=thick)
            solid = model.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=model.create_entity("IfcAxis2Placement3D", Location=model.create_entity("IfcCartesianPoint", Coordinates=(0.0,0.0,0.0))), ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0,0.0,1.0)), Depth=height)
            shape = model.create_entity("IfcShapeRepresentation", body_context, "Body", "SweptSolid", [solid])
            wall = model.create_entity("IfcWall", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), ObjectPlacement=local_placement, Representation=model.create_entity("IfcProductDefinitionShape", Representations=[shape]))
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [wall], target_storey)

        # --- STAIR TRANSLATION ---
        elif el_type == "IfcStair":
            w, r, h, t = float(element.get("width", 1.0)), float(element.get("flight_run", 2.0)), float(element.get("flight_rise", 1.3)), float(element.get("tread_thickness", 0.03))
            num = 7
            rh, td = h / num, r / (num - 1)
            stair_components = []
            for i in range(num - 1):
                sp = model.create_entity("IfcRectangleProfileDef", ProfileType="AREA", Position=model.create_entity("IfcCartesianPoint", Coordinates=(td/2.0, w/2.0)), XDim=td, YDim=w)
                st = model.create_entity("IfcExtrudedAreaSolid", SweptArea=sp, Position=model.create_entity("IfcAxis2Placement3D", Location=model.create_entity("IfcCartesianPoint", Coordinates=(i*td, 0.0, i*rh))), ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0,0.0,1.0)), Depth=t)
                stair_components.append(st)
            shape = model.create_entity("IfcShapeRepresentation", body_context, "Body", "SweptSolid", stair_components)
            stair = model.create_entity("IfcStair", GlobalId=ifcopenshell.guid.new(), Name=element.get("name"), ObjectPlacement=local_placement, Representation=model.create_entity("IfcProductDefinitionShape", Representations=[shape]))
            model.create_entity("IfcRelContainedInSpatialStructure", ifcopenshell.guid.new(), None, None, None, [stair], target_storey)

    model.write(output_ifc_path)
    print(f"🚀 SUCCESS: Model with Hip Roof generated completely inside '{output_ifc_path}'")

if __name__ == "__main__":
    create_ifc_from_json("building.ifcjson", "building.ifc")
