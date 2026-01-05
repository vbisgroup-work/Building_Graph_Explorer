## tests/test_queries.py
"""
Unit tests for QueryEngine

These tests verify:
- Basic queries
- Graph traversal logic
- Relationship queries
- Analytics queries

All database interactions are fully mocked.
"""

import pytest
from unittest.mock import MagicMock, call

from src.queries import QueryEngine

# --------------------------------------------------
# Helper fixture: mocked QueryEngine
# --------------------------------------------------
@pytest.fixture
def query_engine():
    """
    Create a QueryEngine instance with mocked GraphService and database.
    """
    mock_gs = MagicMock()
    mock_db = MagicMock()

    mock_gs.db = mock_db
    mock_gs.vertices = MagicMock()

    return QueryEngine(mock_gs)


# --------------------------------------------------
# Test Case 1: get_elements_by_type
# --------------------------------------------------
def test_get_elements_by_type(query_engine):
    """
    Verify that elements are filtered by type correctly.
    """
    mock_cursor = [
        {"_key": "rm_1", "type": "Room", "name": "Room 1"},
        {"_key": "rm_2", "type": "Room", "name": "Room 2"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    result = query_engine.get_elements_by_type("Room")

    assert len(result) == 2
    assert all(e["type"] == "Room" for e in result)
    
    # Verify the query was called with correct parameters
    query_engine.db.aql.execute.assert_called_once()
    call_args = query_engine.db.aql.execute.call_args
    assert call_args[1]["bind_vars"]["type"] == "Room"


def test_get_elements_by_type_empty_result(query_engine):
    """
    Verify that empty list is returned when no elements match
    """
    query_engine.db.aql.execute.return_value = iter([])

    result = query_engine.get_elements_by_type("NonExistent")

    assert len(result) == 0
    assert result == []


def test_get_elements_by_type_different_types(query_engine):
    """
    Verify that different element types can be queried
    """
    mock_cursor = [
        {"_key": "dr_1", "type": "Door"},
        {"_key": "dr_2", "type": "Door"},
        {"_key": "dr_3", "type": "Door"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    result = query_engine.get_elements_by_type("Door")

    assert len(result) == 3
    assert all(e["type"] == "Door" for e in result)


# --------------------------------------------------
# Test Case 2: get_element_by_id
# --------------------------------------------------
def test_get_element_by_id(query_engine):
    """
    Verify that a single element is retrieved by ID.
    """
    query_engine.gs.vertices.get.return_value = {
        "_key": "rm_001",
        "type": "Room",
        "name": "Test Room",
        "properties": {"area_sqm": 50}
    }

    result = query_engine.get_element_by_id("rm_001")

    assert result["_key"] == "rm_001"
    assert result["type"] == "Room"
    query_engine.gs.vertices.get.assert_called_once_with("rm_001")


def test_get_element_by_id_not_found(query_engine):
    """
    Verify that None is returned when element doesn't exist
    """
    query_engine.gs.vertices.get.return_value = None

    result = query_engine.get_element_by_id("nonexistent")

    assert result is None


# --------------------------------------------------
# Test Case 3: get_children
# --------------------------------------------------
def test_get_children(query_engine):
    """
    Verify that direct children are returned correctly.
    """
    mock_cursor = [
        {"_key": "flr_1", "type": "Floor", "name": "Floor 1"},
        {"_key": "flr_2", "type": "Floor", "name": "Floor 2"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    children = query_engine.get_children("bld_1")

    assert len(children) == 2
    assert children[0]["_key"] == "flr_1"
    assert children[1]["_key"] == "flr_2"


def test_get_children_no_children(query_engine):
    """
    Verify that empty list is returned when element has no children
    """
    query_engine.db.aql.execute.return_value = iter([])

    children = query_engine.get_children("rm_001")

    assert len(children) == 0
    assert children == []


# --------------------------------------------------
# Test Case 4: get_descendants (DFS traversal)
# --------------------------------------------------
def test_get_descendants(query_engine):
    """
    Verify DFS traversal returns all descendant nodes.
    """
    # Setup: root has child_1, child_1 has child_2
    def mock_get_children(element_id):
        if element_id == "root":
            return [{"_key": "child_1", "type": "Floor"}]
        elif element_id == "child_1":
            return [{"_key": "child_2", "type": "Room"}]
        return []
    
    def mock_get_element_by_id(element_id):
        elements = {
            "child_1": {"_key": "child_1", "type": "Floor", "name": "Child 1"},
            "child_2": {"_key": "child_2", "type": "Room", "name": "Child 2"}
        }
        return elements.get(element_id)

    query_engine.get_children = MagicMock(side_effect=mock_get_children)
    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    descendants = query_engine.get_descendants("root")

    assert len(descendants) == 2
    assert descendants[0]["_key"] in ["child_1", "child_2"]
    assert descendants[1]["_key"] in ["child_1", "child_2"]


def test_get_descendants_with_max_depth(query_engine):
    """
    Verify DFS traversal respects max_depth parameter.
    """
    # Setup: root -> level1 -> level2 -> level3
    def mock_get_children(element_id):
        if element_id == "root":
            return [{"_key": "level1", "type": "Floor"}]
        elif element_id == "level1":
            return [{"_key": "level2", "type": "Room"}]
        elif element_id == "level2":
            return [{"_key": "level3", "type": "Door"}]
        return []
    
    def mock_get_element_by_id(element_id):
        elements = {
            "level1": {"_key": "level1", "type": "Floor"},
            "level2": {"_key": "level2", "type": "Room"},
            "level3": {"_key": "level3", "type": "Door"}
        }
        return elements.get(element_id)

    query_engine.get_children = MagicMock(side_effect=mock_get_children)
    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    # With max_depth=1, should only get level1
    descendants = query_engine.get_descendants("root", max_depth=1)

    assert len(descendants) == 1
    assert descendants[0]["_key"] == "level1"


def test_get_descendants_no_descendants(query_engine):
    """
    Verify that empty list is returned when element has no descendants
    """
    query_engine.get_children = MagicMock(return_value=[])
    query_engine.get_element_by_id = MagicMock(return_value=None)

    descendants = query_engine.get_descendants("leaf_node")

    assert len(descendants) == 0
    assert descendants == []


def test_get_descendants_avoids_cycles(query_engine):
    """
    Verify DFS doesn't get stuck in cycles (visited set works)
    """
    call_count = {"count": 0}
    
    def mock_get_children(element_id):
        call_count["count"] += 1
        if call_count["count"] > 10:  # Safety limit
            return []
        if element_id == "root":
            return [{"_key": "child_1", "type": "Floor"}]
        return []
    
    def mock_get_element_by_id(element_id):
        return {"_key": element_id, "type": "Floor"}

    query_engine.get_children = MagicMock(side_effect=mock_get_children)
    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    descendants = query_engine.get_descendants("root")

    # Should only process each node once
    assert len(descendants) == 1


# --------------------------------------------------
# Test Case 5: get_ancestors
# --------------------------------------------------
def test_get_ancestors(query_engine):
    """
    Verify ancestors are returned in correct order.
    """
    mock_cursor = [
        {"_key": "flr_002", "type": "Floor", "name": "First Floor"},
        {"_key": "bld_001", "type": "Building", "name": "Building"},
        {"_key": "site_001", "type": "Site", "name": "Site"},
        {"_key": "prj_001", "type": "Project", "name": "Project"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    ancestors = query_engine.get_ancestors("rm_011")

    assert len(ancestors) == 4
    assert ancestors[0]["_key"] == "flr_002"
    assert ancestors[3]["_key"] == "prj_001"


def test_get_ancestors_no_ancestors(query_engine):
    """
    Verify that empty list is returned for root element
    """
    query_engine.db.aql.execute.return_value = iter([])

    ancestors = query_engine.get_ancestors("prj_001")

    assert len(ancestors) == 0


def test_get_ancestors_single_parent(query_engine):
    """
    Verify that single ancestor is returned correctly
    """
    mock_cursor = [
        {"_key": "flr_001", "type": "Floor", "name": "Ground Floor"}
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    ancestors = query_engine.get_ancestors("rm_001")

    assert len(ancestors) == 1
    assert ancestors[0]["_key"] == "flr_001"


# --------------------------------------------------
# Test Case 6: get_connected_rooms
# --------------------------------------------------
def test_get_connected_rooms(query_engine):
    """
    Verify rooms connected via doors are returned.
    """
    mock_cursor = [
        {"_key": "rm_2", "type": "Room", "name": "Room 2"},
        {"_key": "rm_3", "type": "Room", "name": "Room 3"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    rooms = query_engine.get_connected_rooms("rm_1")

    assert len(rooms) == 2
    assert rooms[0]["_key"] == "rm_2"
    assert rooms[1]["_key"] == "rm_3"


def test_get_connected_rooms_no_connections(query_engine):
    """
    Verify that empty list is returned when room has no connections
    """
    query_engine.db.aql.execute.return_value = iter([])

    rooms = query_engine.get_connected_rooms("isolated_room")

    assert len(rooms) == 0


def test_get_connected_rooms_single_connection(query_engine):
    """
    Verify single connected room is returned
    """
    mock_cursor = [
        {"_key": "rm_2", "type": "Room", "name": "Room 2"}
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    rooms = query_engine.get_connected_rooms("rm_1")

    assert len(rooms) == 1
    assert rooms[0]["_key"] == "rm_2"


# --------------------------------------------------
# Test Case 7: get_room_openings
# --------------------------------------------------
def test_get_room_openings(query_engine):
    """
    Verify doors and windows are separated correctly.
    """
    mock_cursor = [
        {"_key": "d1", "type": "Door", "name": "Main Door"},
        {"_key": "w1", "type": "Window", "name": "Window 1"},
        {"_key": "w2", "type": "Window", "name": "Window 2"},
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    openings = query_engine.get_room_openings("rm_1")

    assert len(openings["doors"]) == 1
    assert len(openings["windows"]) == 2
    assert openings["doors"][0]["_key"] == "d1"
    assert openings["windows"][0]["_key"] == "w1"
    assert openings["windows"][1]["_key"] == "w2"


def test_get_room_openings_no_openings(query_engine):
    """
    Verify that empty lists are returned when room has no openings
    """
    query_engine.db.aql.execute.return_value = iter([])

    openings = query_engine.get_room_openings("rm_1")

    assert len(openings["doors"]) == 0
    assert len(openings["windows"]) == 0
    assert openings == {"doors": [], "windows": []}


def test_get_room_openings_only_doors(query_engine):
    """
    Verify correct grouping when only doors exist
    """
    mock_cursor = [
        {"_key": "d1", "type": "Door", "name": "Door 1"},
        {"_key": "d2", "type": "Door", "name": "Door 2"}
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    openings = query_engine.get_room_openings("rm_1")

    assert len(openings["doors"]) == 2
    assert len(openings["windows"]) == 0


def test_get_room_openings_only_windows(query_engine):
    """
    Verify correct grouping when only windows exist
    """
    mock_cursor = [
        {"_key": "w1", "type": "Window", "name": "Window 1"},
        {"_key": "w2", "type": "Window", "name": "Window 2"}
    ]
    query_engine.db.aql.execute.return_value = iter(mock_cursor)

    openings = query_engine.get_room_openings("rm_1")

    assert len(openings["doors"]) == 0
    assert len(openings["windows"]) == 2


# --------------------------------------------------
# Test Case 8: find_path (BFS)
# --------------------------------------------------
def test_find_path(query_engine):
    """
    Verify BFS path finding works correctly.
    """
    # Mock the traversal: rm_1 -> rm_2 -> rm_3
    def mock_aql_execute(query, bind_vars):
        start = bind_vars["start"]
        if "rm_1" in start:
            return iter(["rm_2"])
        elif "rm_2" in start:
            return iter(["rm_1", "rm_3"])
        elif "rm_3" in start:
            return iter(["rm_2"])
        return iter([])
    
    def mock_get_element_by_id(element_id):
        elements = {
            "rm_1": {"_key": "rm_1", "type": "Room", "name": "Room 1"},
            "rm_2": {"_key": "rm_2", "type": "Room", "name": "Room 2"},
            "rm_3": {"_key": "rm_3", "type": "Room", "name": "Room 3"},
        }
        return elements.get(element_id)

    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)
    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    path = query_engine.find_path("rm_1", "rm_3")

    assert len(path) == 3
    assert path[0]["_key"] == "rm_1"
    assert path[1]["_key"] == "rm_2"
    assert path[2]["_key"] == "rm_3"


def test_find_path_direct_connection(query_engine):
    """
    Verify path finding for directly connected nodes
    """
    def mock_aql_execute(query, bind_vars):
        start = bind_vars["start"]
        if "rm_1" in start:
            return iter(["rm_2"])
        return iter([])
    
    def mock_get_element_by_id(element_id):
        elements = {
            "rm_1": {"_key": "rm_1", "type": "Room"},
            "rm_2": {"_key": "rm_2", "type": "Room"}
        }
        return elements.get(element_id)

    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)
    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    path = query_engine.find_path("rm_1", "rm_2")

    assert len(path) == 2
    assert path[0]["_key"] == "rm_1"
    assert path[1]["_key"] == "rm_2"


def test_find_path_no_path(query_engine):
    """
    Verify that empty list is returned when no path exists.
    """
    query_engine.db.aql.execute.return_value = iter([])

    path = query_engine.find_path("rm_1", "rm_999")

    assert len(path) == 0
    assert path == []


def test_find_path_same_node(query_engine):
    """
    Verify path finding when start and end are the same
    """
    def mock_get_element_by_id(element_id):
        return {"_key": element_id, "type": "Room"}

    query_engine.get_element_by_id = MagicMock(side_effect=mock_get_element_by_id)

    path = query_engine.find_path("rm_1", "rm_1")

    assert len(path) == 1
    assert path[0]["_key"] == "rm_1"


# --------------------------------------------------
# Test Case 9: get_element_statistics
# --------------------------------------------------
def test_get_element_statistics(query_engine):
    """
    Verify element statistics and total area calculation.
    """
    mock_descendants = [
        {"_key": "flr_1", "type": "Floor", "properties": {"area_sqm": 100}},
        {"_key": "flr_2", "type": "Floor", "properties": {"area_sqm": 150}},
        {"_key": "rm_1", "type": "Room", "properties": {"area_sqm": 30}},
        {"_key": "rm_2", "type": "Room", "properties": {"area_sqm": 20}},
        {"_key": "d_1", "type": "Door", "properties": {}},
        {"_key": "w_1", "type": "Window", "properties": {}},
    ]
    
    query_engine.get_descendants = MagicMock(return_value=mock_descendants)

    stats = query_engine.get_element_statistics("bld_1")

    assert stats["Floor"] == 2
    assert stats["Room"] == 2
    assert stats["Door"] == 1
    assert stats["Window"] == 1
    assert stats["total_area_sqm"] == 250  # Only counts Floor area


def test_get_element_statistics_empty_building(query_engine):
    """
    Verify statistics for empty building
    """
    query_engine.get_descendants = MagicMock(return_value=[])

    stats = query_engine.get_element_statistics("empty_bld")

    assert stats["Floor"] == 0
    assert stats["Room"] == 0
    assert stats["Door"] == 0
    assert stats["Window"] == 0
    assert stats["total_area_sqm"] == 0


def test_get_element_statistics_missing_area(query_engine):
    """
    Verify handling of missing area_sqm property
    """
    mock_descendants = [
        {"_key": "flr_1", "type": "Floor", "properties": {}},  # Missing area_sqm
        {"_key": "rm_1", "type": "Room", "properties": {}}
    ]
    
    query_engine.get_descendants = MagicMock(return_value=mock_descendants)

    stats = query_engine.get_element_statistics("bld_1")

    assert stats["Floor"] == 1
    assert stats["total_area_sqm"] == 0  # Default to 0 when missing


# --------------------------------------------------
# Test Case 10: get_room_capacity_report
# --------------------------------------------------
def test_get_room_capacity_report(query_engine):
    """
    Verify room capacity aggregation by room type.
    """
    mock_descendants = [
        {
            "_key": "rm_1",
            "type": "Room",
            "properties": {"room_type": "MeetingRoom", "capacity": 10},
        },
        {
            "_key": "rm_2",
            "type": "Room",
            "properties": {"room_type": "MeetingRoom", "capacity": 8},
        },
        {
            "_key": "rm_3",
            "type": "Room",
            "properties": {"room_type": "Office", "capacity": 4},
        },
        {
            "_key": "d_1",
            "type": "Door",
            "properties": {},
        },
    ]
    
    query_engine.get_descendants = MagicMock(return_value=mock_descendants)

    report = query_engine.get_room_capacity_report("bld_1")

    assert report["MeetingRoom"]["count"] == 2
    assert report["MeetingRoom"]["total_capacity"] == 18
    assert report["Office"]["count"] == 1
    assert report["Office"]["total_capacity"] == 4
    assert "Door" not in report  # Only rooms should be in report


def test_get_room_capacity_report_missing_properties(query_engine):
    """
    Verify handling of rooms with missing properties.
    """
    mock_descendants = [
        {
            "_key": "rm_1",
            "type": "Room",
            "properties": {"room_type": "Office", "capacity": 5},
        },
        {
            "_key": "rm_2",
            "type": "Room",
            "properties": {},  # Missing room_type and capacity
        },
    ]
    
    query_engine.get_descendants = MagicMock(return_value=mock_descendants)

    report = query_engine.get_room_capacity_report("bld_1")

    assert report["Office"]["count"] == 1
    assert report["Office"]["total_capacity"] == 5
    assert report["Other"]["count"] == 1  # Default room_type
    assert report["Other"]["total_capacity"] == 0  # Default capacity


def test_get_room_capacity_report_empty_building(query_engine):
    """
    Verify report for building with no rooms
    """
    query_engine.get_descendants = MagicMock(return_value=[])

    report = query_engine.get_room_capacity_report("empty_bld")

    assert report == {}


def test_get_room_capacity_report_multiple_types(query_engine):
    """
    Verify report handles multiple room types correctly
    """
    mock_descendants = [
        {"_key": "rm_1", "type": "Room", "properties": {"room_type": "Office", "capacity": 2}},
        {"_key": "rm_2", "type": "Room", "properties": {"room_type": "Conference", "capacity": 20}},
        {"_key": "rm_3", "type": "Room", "properties": {"room_type": "Lab", "capacity": 15}},
        {"_key": "rm_4", "type": "Room", "properties": {"room_type": "Office", "capacity": 3}},
    ]
    
    query_engine.get_descendants = MagicMock(return_value=mock_descendants)

    report = query_engine.get_room_capacity_report("bld_1")

    assert len(report) == 3
    assert report["Office"]["count"] == 2
    assert report["Office"]["total_capacity"] == 5
    assert report["Conference"]["total_capacity"] == 20
    assert report["Lab"]["total_capacity"] == 15


# --------------------------------------------------
# Test Case 11: get_graph_metadata
# --------------------------------------------------
def test_get_graph_metadata(query_engine):
    """
    Verify graph metadata collection.
    """
    # Mock vertex stats query
    vertex_result = {
        "total_elements": 118,
        "element_counts": [
            {"Project": 1},
            {"Site": 1},
            {"Building": 2},
            {"Floor": 7},
            {"Room": 43},
            {"Door": 40},
            {"Window": 24}
        ]
    }
    
    # Mock edge stats query
    edge_results = [
        {"PART_OF": 117},
        {"CONTAINS": 107},
        {"HAS_OPENING": 64},
        {"CONNECTS_TO": 40}
    ]
    
    def mock_aql_execute(query):
        if "element_counts" in query:
            return iter([vertex_result])
        else:
            return iter(edge_results)
    
    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)

    metadata = query_engine.get_graph_metadata()

    assert metadata["total_elements"] == 118
    assert metadata["element_counts"]["Project"] == 1
    assert metadata["element_counts"]["Room"] == 43
    assert metadata["element_counts"]["Door"] == 40
    assert metadata["relationships"]["PART_OF"] == 117
    assert metadata["relationships"]["CONNECTS_TO"] == 40


def test_get_graph_metadata_empty_graph(query_engine):
    """
    Verify metadata for empty graph
    """
    vertex_result = {
        "total_elements": 0,
        "element_counts": []
    }
    
    edge_results = []
    
    def mock_aql_execute(query):
        if "element_counts" in query:
            return iter([vertex_result])
        else:
            return iter(edge_results)
    
    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)

    metadata = query_engine.get_graph_metadata()

    assert metadata["total_elements"] == 0
    assert metadata["element_counts"] == {}
    assert metadata["relationships"] == {}


def test_get_graph_metadata_single_type(query_engine):
    """
    Verify metadata with single element type
    """
    vertex_result = {
        "total_elements": 5,
        "element_counts": [
            {"Room": 5}
        ]
    }
    
    edge_results = [
        {"PART_OF": 5}
    ]
    
    def mock_aql_execute(query):
        if "element_counts" in query:
            return iter([vertex_result])
        else:
            return iter(edge_results)
    
    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)

    metadata = query_engine.get_graph_metadata()

    assert metadata["total_elements"] == 5
    assert len(metadata["element_counts"]) == 1
    assert metadata["element_counts"]["Room"] == 5
    assert metadata["relationships"]["PART_OF"] == 5


def test_get_graph_metadata_structure(query_engine):
    """
    Verify metadata has correct structure
    """
    vertex_result = {
        "total_elements": 10,
        "element_counts": [{"Room": 10}]
    }
    
    edge_results = [{"CONTAINS": 10}]
    
    def mock_aql_execute(query):
        if "element_counts" in query:
            return iter([vertex_result])
        else:
            return iter(edge_results)
    
    query_engine.db.aql.execute = MagicMock(side_effect=mock_aql_execute)

    metadata = query_engine.get_graph_metadata()

    # Verify structure
    assert "total_elements" in metadata
    assert "element_counts" in metadata
    assert "relationships" in metadata
    assert isinstance(metadata["total_elements"], int)
    assert isinstance(metadata["element_counts"], dict)
    assert isinstance(metadata["relationships"], dict)