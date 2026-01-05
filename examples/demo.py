import os
from src.graph_service import GraphService
from src.queries import QueryEngine
from src.data_loader import load_and_parse_data

def run_demo():
    """
    Demo script for BIM Graph Explorer
    Demonstrates graph construction and query capabilities
    """

    # Example output format
    print("=" * 70)
    print("=== Building Graph Explorer Demo ===\n")
    print("=" * 70)

    # 1. Initialize GraphService with named graph
    print("\n[SETUP] Initializing Graph Service...")
    graph_service = GraphService(
        host="http://localhost:8529",
        database="bim_graph_db",
        username="root",
        password="password",
        graph_name="building_graph"  # Named graph for better performance
    )

    # 2. Clean existing data
    print("\n[SETUP] Cleaning existing data...")
    deleted = graph_service.delete_all_data()
    print(f"✓ Deleted {deleted.get('vertices_deleted', 0)} vertices")
    print(f"✓ Deleted {deleted.get('edges_deleted', 0)} edges")

    # 3. Load and build graph
    query_engine = QueryEngine(graph_service)
    data_path = os.path.join("data", "building_data.json")
    
    print("\n[LOAD] Loading BIM data...")
    data = load_and_parse_data(data_path)
    print(f"✓ Loaded {len(data)} elements from JSON")

    print("\n[BUILD] Building graph from data...")
    stats = graph_service.build_graph_from_data(data)
    print(f"✓ Created {stats['vertices']} vertices")
    print(f"✓ Created {stats['edges']} edges")

    # 4. Graph info
    print("\n" + "=" * 70)
    print("GRAPH STRUCTURE INFO")
    print("=" * 70)
    
    graph_info = graph_service.get_graph_info()
    print(f"\nGraph Name: {graph_info['name']}")
    print(f"Vertex Collections: {', '.join(graph_info['vertex_collections'])}")
    print(f"Edge Collections  : {', '.join(graph_info['edge_collections'])}")

    # 5. Query demonstrations
    print("\n" + "=" * 70)
    print("QUERY DEMONSTRATIONS")
    print("=" * 70)

    # Query 1: All Meeting Rooms
    print("\n[Q1] All Meeting Rooms:")
    rooms = query_engine.get_elements_by_type("Room")
    rooms = [
        r for r in rooms
        if r.get("properties", {}).get("room_type") == "MeetingRoom"
    ]

    for room in rooms:
        capacity = room['properties']['capacity']
        print(f"  • {room['name']:20s} (Capacity: {capacity})")
    print(f"  Total: {len(rooms)} meeting rooms")

    # Query 2: Get building statistics
    print("\n[Q2] Building Statistics for Main Office Tower (bld_001):")    
    stats = query_engine.get_element_statistics("bld_001")
    print(f"   Floors: {stats['Floor']}")
    print(f"   Rooms: {stats['Room']}")
    print(f"   Doors: {stats['Door']}")
    print(f"   Windows: {stats['Window']}")
    print(f"   Total Area: {stats['total_area_sqm']} sqm")

    # Query 3: Path Finding
    print("\n[Q3] Path from Main Lobby (rm_001) to Board Room (rm_032):")
    path = query_engine.find_path("rm_001", "rm_032")
    for step in path:
        print(f"   → {step['name']} ({step['type']})")

    # Query 4: Room Connections
    print("\n[Q4] Rooms connected to Main Lobby (rm_001):")
    connected = query_engine.get_connected_rooms("rm_001")
    for room in connected:
        print(f"   - {room['name']}")
    print(f"  Total: {len(connected)} connected rooms")

    ## Demo All Queries Demonstration
    # Query 5. Get all rooms with get_element_by_type
    print("\n[Q5]. Rooms in the building:")
    all_rooms = query_engine.get_elements_by_type("Room")
    count = len(all_rooms)
    print(f"   Total Rooms: {count}")

    # Query 6: Element Details
    print("\n[Q6] Details of Door dr_001 (Main Entrance):")

    door = query_engine.get_element_by_id("dr_001")

    if door is None:
        print("   Door with ID 'dr_001' not found.")
    else:
        print(f"   ID        : {door.get('_key')}")
        print(f"   Name      : {door.get('name')}")
        print(f"   Type      : {door.get('type')}")
        print(f"   Parent ID : {door.get('parent_id')}")

        print("   Properties:")
        for k, v in door.get("properties", {}).items():
            print(f"     - {k}: {v}")

        print(f"   Connects  : {door.get('connects')}")

    # Query 7: Children of Building
    print("\n[Q7] Direct Children of Building (bld_001):")
    children = query_engine.get_children("bld_001")
    if not children:
        print("   No children found.")
    else:
        for child in children:
            print(f"   ID        : {child.get('_key')}")
            print(f"   Name      : {child.get('name')}")
            print(f"   Type      : {child.get('type')}")
            print(f"   Parent ID : {child.get('parent_id')}")

            properties = child.get("properties", {})
            if properties:
                print("   Properties:")
                for k, v in properties.items():
                    print(f"     - {k}: {v}")
                print("------------------------------")
            else:
                print("   Properties: None")

    # Query 8: Descendants Analysis
    print("\n[Q8] Descendants of Floor flr_002 (First Floor):")
    descendants = query_engine.get_descendants("flr_002")
    if not descendants:
        print("   No descendants found.")
    else:
        summary = {}

        for desc in descendants:
            element_type = desc.get("type", "Unknown")
            summary[element_type] = summary.get(element_type, 0) + 1

        print("   Summary:")
        for element_type, count in summary.items():
            print(f"   - {element_type}: {count}")

    ## Query 9: Ancestors
    print("\n[Q9] Ancestors of Room rm_011 (Meeting Room 1A):")
    ancestors = query_engine.get_ancestors("rm_011")
    if not ancestors:
        print("   No ancestors found.")
    else:
        for anc in ancestors:
            print(f"   → {anc['_key']} ({anc['type']})")

    # Query 10: Get connected rooms via doors
    print("\n[Q10]. Rooms connected to Room (Reception) rm_002 via Doors:")
    connected_rooms = query_engine.get_connected_rooms("rm_002")
    if not connected_rooms:
        print("   No connected rooms found.")
    else:
        for room in connected_rooms:
            print(f"   - {room['name']} ({room['type']})")

    # Query 11: Room Openings
    print("\n[Q11] Openings in Open Office 1A (rm_010):")
    openings = query_engine.get_room_openings("rm_010")

    print("   Doors:")
    if openings["doors"]:
        for door in openings["doors"]:
            print(f"     - {door['name']} ({door['_key']})")
    else:
        print("     None")

    print("   Windows:")
    if openings["windows"]:
        for window in openings["windows"]:
            print(f"     - {window['name']} ({window['_key']})")
    else:
        print("     None")

    # Query 12: Find path between two rooms
    print("\n[Q12]. Path from Main Lobby to Executive Office A:")
    path = query_engine.find_path("rm_001", "rm_030")
    if not path:
        print("   No path found.")
    else:
        for step in path:
            print(f"   → {step['name']} ({step['type']})")

    # Query 13: Element statistics for a building
    print("\n[Q13]. Building Statistics for bld_002:")
    stats = query_engine.get_element_statistics("bld_002")

    print(f"   Floors : {stats['Floor']}")
    print(f"   Rooms  : {stats['Room']}")
    print(f"   Doors  : {stats['Door']}")
    print(f"   Windows: {stats['Window']}")
    print(f"   Total Area: {stats['total_area_sqm']} sqm")

    # Query 14: Room capacity report by room type
    print("\n[Q14]. Room Capacity Report for bld_001:")
    report = query_engine.get_room_capacity_report("bld_001")

    for room_type, info in report.items():
        print(f"   {room_type}:")
        print(f"     - Count         : {info['count']}")
        print(f"     - Total Capacity: {info['total_capacity']}")

    # Query 15: Get metadata summary
    print("\n[Q15] Complete Graph Metadata:")
    metadata = query_engine.get_graph_metadata()
    print(f"\n  Total Elements: {metadata['total_elements']}")
    print("\n  Element Counts:")
    for elem_type, count in sorted(metadata['element_counts'].items()):
        print(f"   {elem_type}: {count}")
    
    print("\n  Relationships:")
    for rel_type, count in sorted(metadata['relationships'].items()):
        print(f"   {rel_type}: {count}")

    # Final summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETED SUCCESSFULLY")
    print("=" * 70)
if __name__ == "__main__":
    run_demo()