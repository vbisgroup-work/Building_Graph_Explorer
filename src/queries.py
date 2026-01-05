## src/queries.py
### Part 3: Graph Traversal & Queries (2 hours)
### --------Implement the following query functions:
from typing import List, Dict, Optional
from collections import deque


class QueryEngine:
    def __init__(self, graph_service):
        self.gs = graph_service
        self.db = graph_service.db

    #### 3.1 Basic Queries
    def get_elements_by_type(self, element_type: str) -> List[dict]:
        """
        Get all elements of a specific type

        Example:
            get_elements_by_type("Room")
            # Returns all 43 rooms in the dataset
        """
        query = """
        FOR v IN building_vertices
            FILTER v.type == @type
            RETURN v
        """
        cursor = self.db.aql.execute(query, bind_vars={"type": element_type})
        return [doc for doc in cursor]
    
    def get_element_by_id(self, element_id: str) -> Optional[dict]:
        """
        Get a single element by ID with its properties
        """
        return self.gs.vertices.get(element_id)
    
    #### 3.2 Hierarchy Traversal
    def get_children(self, element_id: str) -> List[dict]:
        """
        Get direct children of an element

        Example:
            get_children("bld_001")
            # Returns: [flr_001, flr_002, flr_003, flr_004]
        """
        query = """
        FOR v, e IN 1..1 OUTBOUND @start building_edges
            FILTER e.relationship == "CONTAINS"
            RETURN v
        """
        cursor = self.db.aql.execute(
            query, 
            bind_vars={"start": f"building_vertices/{element_id}"}
        )
        return [doc for doc in cursor]
    
    def get_descendants(self, element_id: str, max_depth: int = None) -> List[dict]:
        """
        Get all descendants using DFS traversal

        Example:
            get_descendants("flr_002")
            # Returns all rooms, doors, windows on First Floor
        """

        descendants = []
        stack = [(element_id, 0)]  # (current_id, current_depth)
        visited = set()

        while stack:
            current_id, depth = stack.pop()

            if current_id in visited:
                continue

            if max_depth is not None and depth > max_depth:
                continue

            visited.add(current_id)

            if current_id != element_id:
                node = self.get_element_by_id(current_id)
                if node:
                    descendants.append(node)

            children = self.get_children(current_id)
            for child in children:
                stack.append((child["_key"], depth + 1))
            
        return descendants
    # def get_descendants(self, element_id: str, max_depth: int = None) -> List[dict]:
    #     """
    #     Get all descendant elements using ArangoDB traversal (AQL)
    #     """

    #     depth = max_depth if max_depth is not None else 100

    #     query = """
    #     FOR v, e IN 1..@depth OUTBOUND
    #         @start
    #         building_edges
    #         FILTER e.relationship == "CONTAINS"
    #         RETURN v
    #     """

    #     cursor = self.db.aql.execute(
    #         query,
    #         bind_vars={
    #             "start": f"building_vertices/{element_id}",
    #             "depth": depth
    #         }
    #     )

    #     return list(cursor)

    def get_ancestors(self, element_id: str) -> List[dict]:
        """
        Get all ancestors up to root (excluding the node itself)
        Example:
            get_ancestors("rm_011")
            # Returns: [flr_002, bld_001, site_001, prj_001]
        """
        query = """
            FOR v, e, p IN 1..5 OUTBOUND 
                CONCAT('building_vertices/', @element_id)
                building_edges
                OPTIONS {uniqueVertices: 'global', bfs: true}
                FILTER e.relationship == 'PART_OF'
                SORT LENGTH(p.edges) ASC
                RETURN v
            """
            
        cursor = self.db.aql.execute(
            query,
            bind_vars={'element_id': element_id}
        )
        
        return [doc for doc in cursor]
    
    #### 3.3 Relationship Queries
    def get_connected_rooms(self, room_id: str) -> List[dict]:
        """
        Get all rooms connected to a room via doors

        Example:
            get_connected_rooms("rm_001")  # Main Lobby
            # Returns: [rm_002 (Reception), rm_003 (Security), ...]
        """
        query = """
        FOR v, e IN 1..1 OUTBOUND @start building_edges
            FILTER e.relationship == "CONNECTS_TO"
            RETURN v
        """

        cursor = self.db.aql.execute(
            query,
            bind_vars={"start": f"building_vertices/{room_id}"}
        )
        return [doc for doc in cursor]
    
    def get_room_openings(self, room_id: str) -> dict:
        """
        Get all doors and windows in a room

        Example:
            get_room_openings("rm_010")
            # Returns: {"doors": [...], "windows": [...]}
        """
        query = """
        FOR v, e IN 1..1 OUTBOUND @start building_edges
            FILTER e.relationship == "HAS_OPENING"
            RETURN v
        """
        cursor = self.db.aql.execute(
            query,
            bind_vars={"start": f"building_vertices/{room_id}"}
        )

        elements = [doc for doc in cursor]

        return {
            "doors": [element for element in elements if element["type"] == "Door"],
            "windows": [element for element in elements if element["type"] == "Window"]
        }
    
    def find_path(self, from_id: str, to_id: str) -> List[dict]:
        """
        Find path between two elements (BFS)

        Example:
            find_path("rm_001", "rm_032")  # Lobby to Board Room
            # Returns path through floors and connections
        """

        queue = deque([[from_id]])
        visited = {from_id}

        while queue:
            path = queue.popleft()
            current_id = path[-1]

            if current_id == to_id:
                return [self.get_element_by_id(node_id) for node_id in path]

            query = """
            FOR v, e IN 1..1 ANY @start building_edges
                RETURN v._key
            """
            cursor = self.db.aql.execute(
                query,
                bind_vars={"start": f"building_vertices/{current_id}"}
            )

            for neighbor_id in cursor:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])

        return []  # No path found
    # def find_path(self, from_id: str, to_id: str):
    #     query = """
    #     LET path = (
    #         FOR v, e IN ANY SHORTEST_PATH
    #             @from TO @to building_edges
    #             OPTIONS { uniqueVertices: "path" }
    #             RETURN v
    #     )
    #     RETURN path
    #     """

    #     cursor = self.db.aql.execute(
    #         query,
    #         bind_vars={
    #             "from": f"building_vertices/{from_id}",
    #             "to": f"building_vertices/{to_id}"
    #         }
    #     )

    #     result = list(cursor)
    #     return result[0] if result else []
        
    #### 3.4 Analytics Queries
    def get_element_statistics(self, building_id: str) -> dict:
        """
        Count elements by type within a building

        Example:
            get_element_statistics("bld_001")
            # Returns: {
            #     "Floor": 4,
            #     "Room": 28,
            #     "Door": 26,
            #     "Window": 18,
            #     "total_area_sqm": 4800
            # }
        """

        descendants = self.get_descendants(building_id)
        stats = {
            "Floor": 0,
            "Room": 0,
            "Door": 0,
            "Window": 0,
            "total_area_sqm": 0
        }

        for element in descendants:
            element_type = element["type"]
            if element_type in stats:
                stats[element_type] += 1
            
            if element_type == "Floor":
                stats["total_area_sqm"] += element.get("properties", {}).get("area_sqm", 0)
            
        return stats
    
    def get_room_capacity_report(self, building_id: str) -> dict:
        """
        Generate capacity report by room type

        Example:
            get_room_capacity_report("bld_001")
            # Returns: {
            #     "OpenOffice": {"count": 2, "total_capacity": 75},
            #     "MeetingRoom": {"count": 4, "total_capacity": 42},
            #     ...
            # }
        """
        descendants = self.get_descendants(building_id)
        report: Dict[str, Dict[str, int]] = {}

        for element in descendants:
            if element["type"] != "Room":
                continue

            room_type = element.get("properties", {}).get("room_type", "Other")
            capacity = element.get("properties", {}).get("capacity", 0)

            if room_type not in report:
                report[room_type] = {"count": 0, "total_capacity": 0}

            report[room_type]["count"] += 1
            report[room_type]["total_capacity"] += capacity

        return report
    
    def get_graph_metadata(self) -> dict:
        """
        Get comprehensive metadata about the building graph
        Returns statistics similar to the JSON metadata structure
        """
        # Query 1: Count total vertices and group by type
        vertex_stats_aql = """
        RETURN {
            total_elements: LENGTH(building_vertices),
            element_counts: (
                FOR v IN building_vertices
                COLLECT type = v.type WITH COUNT INTO count
                RETURN {[type]: count}
            )
        }
        """
        
        # Query 2: Count edges by relationship type
        edge_stats_aql = """
        FOR e IN building_edges
        COLLECT relationship = e.relationship WITH COUNT INTO count
        RETURN {[relationship]: count}
        """
        
        # Execute queries
        vertex_result = list(self.db.aql.execute(vertex_stats_aql))[0]
        edge_results = list(self.db.aql.execute(edge_stats_aql))
        
        # Process element_counts from list of dicts to single dict
        element_counts = {}
        for item in vertex_result['element_counts']:
            element_counts.update(item)
        
        # Process relationships from list of dicts to single dict
        relationships = {}
        for item in edge_results:
            relationships.update(item)
        
        # Build final metadata structure
        metadata = {
            "total_elements": vertex_result['total_elements'],
            "element_counts": element_counts,
            "relationships": relationships
        }
        
        return metadata