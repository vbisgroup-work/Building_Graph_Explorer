## tests/test_graph_service.py
"""
Unit tests for GraphService

These tests focus on verifying the core graph logic:
- GraphService initialization
- Vertex upsert logic
- Edge upsert logic
- Graph construction from BuildingElement data

ArangoDB is fully mocked to ensure these are true unit tests
(no real database connection is required).
"""

import pytest
from unittest.mock import MagicMock, patch, call

from src.graph_service import GraphService
from src.models import BuildingElement


# --------------------------------------------------
# Fixtures
# --------------------------------------------------
@pytest.fixture
def mock_arango_setup():
    """
    Setup mock ArangoDB client and related objects
    """
    with patch("src.graph_service.ArangoClient") as mock_client:
        # Mock system database
        mock_sys_db = MagicMock()
        mock_sys_db.has_database.return_value = True
        
        # Mock target database
        mock_db = MagicMock()
        mock_db.has_collection.return_value = True
        mock_db.has_graph.return_value = False  # Graph doesn't exist initially
        
        # Mock graph object
        mock_graph = MagicMock()
        mock_db.create_graph.return_value = mock_graph
        
        # Mock collections
        mock_vertices = MagicMock()
        mock_edges = MagicMock()
        mock_db.collection.side_effect = lambda name: (
            mock_vertices if name == "building_vertices" else mock_edges
        )
        
        # Setup client to return databases
        mock_client.return_value.db.side_effect = [mock_sys_db, mock_db]
        
        yield {
            'client': mock_client,
            'sys_db': mock_sys_db,
            'db': mock_db,
            'graph': mock_graph,
            'vertices': mock_vertices,
            'edges': mock_edges
        }


# --------------------------------------------------
# Test Case 1: GraphService initialization
# --------------------------------------------------
def test_graph_service_initialization(mock_arango_setup):
    """
    Verify that GraphService initializes correctly:
    - Connects to system database
    - Creates/connects to target database
    - Creates/connects to collections
    - Creates named graph
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password",
        graph_name="test_graph"
    )

    # Verify database connection
    assert service.db == mock_arango_setup['db']
    assert service.vertices == mock_arango_setup['vertices']
    assert service.edges == mock_arango_setup['edges']
    assert service.graph_name == "test_graph"
    
    # Verify graph was created
    mock_arango_setup['db'].create_graph.assert_called_once()
    call_args = mock_arango_setup['db'].create_graph.call_args
    assert call_args[1]['name'] == 'test_graph'


def test_graph_service_initialization_existing_database(mock_arango_setup):
    """
    Verify that GraphService works when database already exists
    """
    mock_arango_setup['sys_db'].has_database.return_value = True
    
    service = GraphService(
        host="http://localhost:8529",
        database="existing_db",
        username="root",
        password="password"
    )
    
    # Should not create database if it exists
    mock_arango_setup['sys_db'].create_database.assert_not_called()
    assert service.db is not None


def test_graph_service_initialization_new_database(mock_arango_setup):
    """
    Verify that GraphService creates database when it doesn't exist
    """
    mock_arango_setup['sys_db'].has_database.return_value = False
    
    service = GraphService(
        host="http://localhost:8529",
        database="new_db",
        username="root",
        password="password"
    )
    
    # Should create database if it doesn't exist
    mock_arango_setup['sys_db'].create_database.assert_called_once_with("new_db")


def test_graph_service_initialization_existing_graph(mock_arango_setup):
    """
    Verify that GraphService uses existing graph if available
    """
    mock_arango_setup['db'].has_graph.return_value = True
    mock_existing_graph = MagicMock()
    mock_arango_setup['db'].graph.return_value = mock_existing_graph
    
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password",
        graph_name="existing_graph"
    )
    
    # Should get existing graph instead of creating new one
    mock_arango_setup['db'].graph.assert_called_once_with("existing_graph")
    mock_arango_setup['db'].create_graph.assert_not_called()


# --------------------------------------------------
# Test Case 2: Upsert vertex
# --------------------------------------------------
def test_upsert_vertex_inserts_correct_data(mock_arango_setup):
    """
    Verify that upsert_vertex:
    - Calls insert on the vertex collection
    - Uses the element id as _key
    - Includes all element data
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    element = BuildingElement(
        id="room_1",
        type="Room",
        name="Living Room",
        properties={"area_sqm": 50, "capacity": 10}
    )

    service.upsert_vertex(element)

    # Ensure insert is called exactly once with overwrite=True
    service.vertices.insert.assert_called_once()
    call_args = service.vertices.insert.call_args
    
    # Validate inserted data
    inserted_data = call_args[0][0]
    assert inserted_data["_key"] == "room_1"
    assert inserted_data["type"] == "Room"
    assert inserted_data["name"] == "Living Room"
    assert inserted_data["properties"]["area_sqm"] == 50
    assert call_args[1]["overwrite"] == True


def test_upsert_vertex_with_parent_id(mock_arango_setup):
    """
    Verify that upsert_vertex correctly handles parent_id
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    element = BuildingElement(
        id="room_1",
        type="Room",
        name="Room 1",
        parent_id="floor_1"
    )

    service.upsert_vertex(element)

    inserted_data = service.vertices.insert.call_args[0][0]
    assert inserted_data["parent_id"] == "floor_1"


# --------------------------------------------------
# Test Case 3: Upsert edge
# --------------------------------------------------
def test_upsert_edge_creates_correct_edge_document(mock_arango_setup):
    """
    Verify that upsert_edge:
    - Inserts an edge with correct _from and _to fields
    - Uses deterministic edge key
    - Includes relationship and properties
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )

    service.upsert_edge(
        from_id="room_1",
        to_id="room_2",
        relationship="CONNECTS_TO",
        properties={"via_door": "door_1"}
    )

    service.edges.insert.assert_called_once()
    
    edge_data = service.edges.insert.call_args[0][0]
    
    assert edge_data["_key"] == "room_1_CONNECTS_TO_room_2"
    assert edge_data["_from"] == "building_vertices/room_1"
    assert edge_data["_to"] == "building_vertices/room_2"
    assert edge_data["relationship"] == "CONNECTS_TO"
    assert edge_data["properties"]["via_door"] == "door_1"
    assert service.edges.insert.call_args[1]["overwrite"] == True


def test_upsert_edge_without_properties(mock_arango_setup):
    """
    Verify that upsert_edge works without properties
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )

    service.upsert_edge(
        from_id="room_1",
        to_id="floor_1",
        relationship="PART_OF"
    )

    edge_data = service.edges.insert.call_args[0][0]
    assert edge_data["properties"] == {}


def test_upsert_edge_handles_special_characters(mock_arango_setup):
    """
    Verify that upsert_edge handles special characters in IDs
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )

    service.upsert_edge(
        from_id="room/1",
        to_id="floor/1",
        relationship="PART_OF"
    )

    edge_data = service.edges.insert.call_args[0][0]
    # Should replace "/" with "_"
    assert "_" in edge_data["_key"]
    assert "/" not in edge_data["_key"]


# --------------------------------------------------
# Test Case 4: Build graph with PART_OF / CONTAINS relationships
# --------------------------------------------------
def test_build_graph_creates_part_of_and_contains_edges(mock_arango_setup):
    """
    Verify that build_graph_from_data:
    - Inserts all vertices
    - Creates PART_OF and CONTAINS edges for parent-child relationships
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    # Mock vertices.has to return True for parent check
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(
            id="floor_1",
            type="Floor",
            name="First Floor"
        ),
        BuildingElement(
            id="room_1",
            type="Room",
            name="Living Room",
            parent_id="floor_1"
        )
    ]

    result = service.build_graph_from_data(elements)

    # Two vertices should be created
    assert result["vertices"] == 2
    assert service.vertices.insert.call_count == 2

    # Two edges: PART_OF (room->floor) and CONTAINS (floor->room)
    assert result["edges"] == 2
    assert service.edges.insert.call_count == 2
    
    # Verify edge relationships
    edge_calls = [call[0][0] for call in service.edges.insert.call_args_list]
    relationships = [edge["relationship"] for edge in edge_calls]
    assert "PART_OF" in relationships
    assert "CONTAINS" in relationships


def test_build_graph_multiple_children(mock_arango_setup):
    """
    Verify that build_graph handles multiple children correctly
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="floor_1", type="Floor", name="Floor 1"),
        BuildingElement(id="room_1", type="Room", name="Room 1", parent_id="floor_1"),
        BuildingElement(id="room_2", type="Room", name="Room 2", parent_id="floor_1"),
        BuildingElement(id="room_3", type="Room", name="Room 3", parent_id="floor_1")
    ]

    result = service.build_graph_from_data(elements)

    assert result["vertices"] == 4
    # 3 rooms × 2 edges each (PART_OF + CONTAINS) = 6 edges
    assert result["edges"] == 6


# --------------------------------------------------
# Test Case 5: Door CONNECTS_TO relationship between rooms
# --------------------------------------------------
def test_build_graph_creates_connects_to_edges_for_door(mock_arango_setup):
    """
    Verify that a Door connecting two rooms:
    - Creates two CONNECTS_TO edges (bidirectional)
    - Includes via_door property
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="room_1", type="Room", name="Room A"),
        BuildingElement(id="room_2", type="Room", name="Room B"),
        BuildingElement(
            id="door_1",
            type="Door",
            name="Main Door",
            connects=["room_1", "room_2"]
        )
    ]

    result = service.build_graph_from_data(elements)

    # 3 vertices
    assert result["vertices"] == 3
    
    # 2 CONNECTS_TO edges (bidirectional)
    assert result["edges"] == 2
    
    # Verify CONNECTS_TO edges with properties
    edge_calls = [call[0][0] for call in service.edges.insert.call_args_list]
    connects_edges = [e for e in edge_calls if e["relationship"] == "CONNECTS_TO"]
    
    assert len(connects_edges) == 2
    assert all(e["properties"]["via_door"] == "door_1" for e in connects_edges)


def test_build_graph_door_with_parent_room(mock_arango_setup):
    """
    Verify that Door creates both HAS_OPENING and CONNECTS_TO edges
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="room_1", type="Room", name="Room A"),
        BuildingElement(id="room_2", type="Room", name="Room B"),
        BuildingElement(
            id="door_1",
            type="Door",
            name="Door",
            parent_id="room_1",
            connects=["room_1", "room_2"]
        )
    ]

    result = service.build_graph_from_data(elements)
    # PART_OF: door_1 -> room_1
    # CONTAINS: room_1 -> door_1
    # HAS_OPENING: room_1 -> door_1
    # CONNECTS_TO: 2 edges
    # 1 PART_OF + 1 CONTAINS + 1 HAS_OPENING + 2 CONNECTS_TO = 5 edges
    assert result["edges"] == 5
    
    edge_calls = [call[0][0] for call in service.edges.insert.call_args_list]
    relationships = [e["relationship"] for e in edge_calls]
    
    assert relationships.count("CONNECTS_TO") == 2
    assert relationships.count("HAS_OPENING") == 1


# --------------------------------------------------
# Test Case 6: HAS_OPENING relationship
# --------------------------------------------------
def test_build_graph_creates_has_opening_for_door(mock_arango_setup):
    """
    Verify that Door with parent_id creates HAS_OPENING edge
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="room_1", type="Room", name="Room 1"),
        BuildingElement(
            id="door_1",
            type="Door",
            name="Door 1",
            parent_id="room_1"
        )
    ]

    result = service.build_graph_from_data(elements)

    assert result["edges"] == 3  # PART_OF, CONTAINS, HAS_OPENING
    
    edge_data = service.edges.insert.call_args[0][0]
    assert edge_data["relationship"] == "HAS_OPENING"
    assert edge_data["_from"] == "building_vertices/room_1"
    assert edge_data["_to"] == "building_vertices/door_1"


def test_build_graph_creates_has_opening_for_window(mock_arango_setup):
    """
    Verify that Window with parent_id creates HAS_OPENING edge
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="room_1", type="Room", name="Room 1"),
        BuildingElement(
            id="window_1",
            type="Window",
            name="Window 1",
            parent_id="room_1"
        )
    ]

    result = service.build_graph_from_data(elements)

    assert result["edges"] == 3 # PART_OF, CONTAINS, HAS_OPENING
    
    edge_data = service.edges.insert.call_args[0][0]
    assert edge_data["relationship"] == "HAS_OPENING"


# --------------------------------------------------
# Test Case 7: Complex hierarchy
# --------------------------------------------------
def test_build_graph_complex_hierarchy(mock_arango_setup):
    """
    Verify that build_graph handles complex hierarchies correctly
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="prj_1", type="Project", name="Project"),
        BuildingElement(id="site_1", type="Site", name="Site", parent_id="prj_1"),
        BuildingElement(id="bld_1", type="Building", name="Building", parent_id="site_1"),
        BuildingElement(id="flr_1", type="Floor", name="Floor", parent_id="bld_1"),
        BuildingElement(id="rm_1", type="Room", name="Room", parent_id="flr_1"),
        BuildingElement(id="dr_1", type="Door", name="Door", parent_id="rm_1"),
        BuildingElement(id="wn_1", type="Window", name="Window", parent_id="rm_1")
    ]

    result = service.build_graph_from_data(elements)

    assert result["vertices"] == 7
    # 4 PART_OF + 4 CONTAINS (prj->site, site->bld, bld->flr, flr->rm, rm->dr, rm->wn) = 12
    # 2 HAS_OPENING (rm->dr, rm->wn) = 2
    # Total = 14
    assert result["edges"] == 14


# --------------------------------------------------
# Test Case 8: Edge cases
# --------------------------------------------------
def test_build_graph_with_missing_parent(mock_arango_setup):
    """
    Verify that build_graph skips edges when parent doesn't exist
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    # Parent doesn't exist
    service.vertices.has.return_value = False

    elements = [
        BuildingElement(
            id="room_1",
            type="Room",
            name="Room 1",
            parent_id="nonexistent_floor"
        )
    ]

    result = service.build_graph_from_data(elements)

    assert result["vertices"] == 1
    assert result["edges"] == 0  # No edges created because parent doesn't exist


def test_build_graph_door_with_one_connection(mock_arango_setup):
    """
    Verify that Door with only one connection doesn't create CONNECTS_TO edges
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.has.return_value = True

    elements = [
        BuildingElement(id="room_1", type="Room", name="Room 1"),
        BuildingElement(
            id="door_1",
            type="Door",
            name="Door",
            connects=["room_1"]  # Only one connection
        )
    ]

    result = service.build_graph_from_data(elements)

    # No CONNECTS_TO edges should be created
    edge_calls = [call[0][0] for call in service.edges.insert.call_args_list]
    connects_edges = [e for e in edge_calls if e["relationship"] == "CONNECTS_TO"]
    assert len(connects_edges) == 0


def test_build_graph_empty_elements(mock_arango_setup):
    """
    Verify that build_graph handles empty element list
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )

    result = service.build_graph_from_data([])

    assert result["vertices"] == 0
    assert result["edges"] == 0


# --------------------------------------------------
# Test Case 9: Delete and Drop operations
# --------------------------------------------------
def test_delete_all_data(mock_arango_setup):
    """
    Verify that delete_all_data truncates collections
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.vertices.truncate.return_value = True
    service.edges.truncate.return_value = True

    result = service.delete_all_data()

    service.vertices.truncate.assert_called_once()
    service.edges.truncate.assert_called_once()
    
    assert "vertices_deleted" in result
    assert "edges_deleted" in result


def test_drop_graph_existing(mock_arango_setup):
    """
    Verify that drop_graph deletes existing graph
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.db.has_graph.return_value = True

    result = service.drop_graph()

    assert result == True
    service.db.delete_graph.assert_called_once_with(
        service.graph_name,
        drop_collections=True
    )


def test_drop_graph_nonexistent(mock_arango_setup):
    """
    Verify that drop_graph returns False when graph doesn't exist
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.db.has_graph.return_value = False

    result = service.drop_graph()

    assert result == False
    service.db.delete_graph.assert_not_called()


# --------------------------------------------------
# Test Case 10: Get graph info
# --------------------------------------------------
def test_get_graph_info_existing(mock_arango_setup):
    """
    Verify that get_graph_info returns correct information
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.db.has_graph.return_value = True
    
    mock_graph = MagicMock()
    mock_graph.edge_definitions.return_value = [
        {
            "edge_collection": "building_edges",
            "from_vertex_collections": ["building_vertices"],
            "to_vertex_collections": ["building_vertices"]
        }
    ]
    mock_graph.vertex_collections.return_value = ["building_vertices"]
    
    service.db.graph.return_value = mock_graph

    info = service.get_graph_info()

    assert info["name"] == service.graph_name
    assert "building_vertices" in info["vertex_collections"]
    assert "building_edges" in info["edge_collections"]


def test_get_graph_info_nonexistent(mock_arango_setup):
    """
    Verify that get_graph_info returns error when graph doesn't exist
    """
    service = GraphService(
        host="http://localhost:8529",
        database="test_db",
        username="root",
        password="password"
    )
    
    service.db.has_graph.return_value = False

    info = service.get_graph_info()

    assert "error" in info
    assert info["error"] == "Graph does not exist"