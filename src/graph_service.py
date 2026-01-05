## src/graph_service.py
from arango import ArangoClient
from arango.graph import Graph
from typing import List
from .models import BuildingElement


class GraphService:
    def __init__(
            self, 
            host: str, 
            database: str, 
            username: str, 
            password: str,
            graph_name: str = "building_graph"
        ):
        """
        Initialize connection to ArangoDB
        Args:
        host: ArangoDB server URL
        database: Database name
        username: Database username
        password: Database password
        graph_name: Name for the graph structure
        """
        self.graph_name = graph_name
        client = ArangoClient(hosts=host)

        # Connect to system DB to create database if needed
        sys_db = client.db("_system", username=username, password=password)
        if not sys_db.has_database(database):
            sys_db.create_database(database)

        # Connect to target database
        self.db = client.db(database, username=username, password=password)

        # Create vertex collection
        if not self.db.has_collection("building_vertices"):
            self.db.create_collection("building_vertices")

        # Create edge collection
        if not self.db.has_collection("building_edges"):
            self.db.create_collection("building_edges", edge=True)

        self.vertices = self.db.collection("building_vertices")
        self.edges = self.db.collection("building_edges")

        ## Create or get graph_name
        self.graph = self._create_or_get_graph()
    
    def _create_or_get_graph(self) ->Graph:
        """
        Create named graph if it doesn't exist, otherwise return existing graph.
        Named graphs provide better query optimization and cleaner traversal syntax.
        """
        if self.db.has_graph(self.graph_name):
            return self.db.graph(self.graph_name)
        
        # Create graph with edge definitions
        return self.db.create_graph(
            name=self.graph_name,
            edge_definitions=[
                {
                    "edge_collection": "building_edges",
                    "from_vertex_collections": ["building_vertices"],
                    "to_vertex_collections": ["building_vertices"]
                }
            ]
        )        

    def upsert_vertex(self, element: BuildingElement) -> dict:
        """Insert or update a vertex in the graph"""
        data = element.model_dump()
        data["_key"] = element.id
        return self.vertices.insert(data, overwrite=True)

    def upsert_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        properties: dict = None
    ) -> dict:
        """Insert or update an edge between vertices"""
        edge_key = f"{from_id}_{relationship}_{to_id}".replace("/", "_")

        edge_data = {
            "_key": edge_key,
            "_from": f"building_vertices/{from_id}",
            "_to": f"building_vertices/{to_id}",
            "relationship": relationship,
            "properties": properties or {}
        }

        return self.edges.insert(edge_data, overwrite=True)

    def build_graph_from_data(self, elements: List[BuildingElement]) -> dict:
        """
        Build complete graph from JSON data
        Returns statistics about created vertices and edges
        """
        # --------------------------------------------------
        # 1. Insert vertices
        # --------------------------------------------------
        vertex_count = 0
        edge_count = 0

        for element in elements:
            self.upsert_vertex(element)
            vertex_count += 1

        # --------------------------------------------------
        # 2. Create relationships (edges)
        # --------------------------------------------------
        for element in elements:
            # 2.1 PART_OF and CONTAINS
            if element.parent_id and self.vertices.has(element.parent_id):
                self.upsert_edge(element.id, element.parent_id, "PART_OF")
                self.upsert_edge(element.parent_id, element.id, "CONTAINS")
                edge_count += 2

            # 2.2 HAS_OPENING (Room -> Door/Window)
            if element.type in ["Door", "Window"] and element.parent_id:
                if self.vertices.has(element.parent_id):
                    self.upsert_edge(element.parent_id, element.id, "HAS_OPENING")
                    edge_count += 1

            # 2.3 CONNECTS_TO (Room <-> Room via Door)
            if element.type == "Door" and element.connects and len(element.connects) == 2:
                room_1, room_2 = element.connects
                if self.vertices.has(room_1) and self.vertices.has(room_2):
                    self.upsert_edge(
                        room_1,
                        room_2,
                        "CONNECTS_TO",
                        {"via_door": element.id}
                    )
                    self.upsert_edge(
                        room_2,
                        room_1,
                        "CONNECTS_TO",
                        {"via_door": element.id}
                    )
                    edge_count += 2

        return {
            "vertices": vertex_count,
            "edges": edge_count
        }
    
    def delete_all_data(self) -> dict:
        """
        Clear all vertices and edges (useful for testing or resetting)
        Returns counts of deleted documents
        """
        edges_deleted = self.edges.truncate()
        vertices_deleted = self.vertices.truncate()
        
        return {
            "vertices_deleted": vertices_deleted,
            "edges_deleted": edges_deleted
        }
    
    def drop_graph(self) -> bool:
        """
        Drop the entire graph including collections
        WARNING: This will delete all data!
        """
        try:
            if self.db.has_graph(self.graph_name):
                self.db.delete_graph(
                    self.graph_name,
                    drop_collections=True  # Also delete the collections
                )
                return True
            return False
        except Exception as e:
            print(f"Error dropping graph: {e}")
            return False
    
    def get_graph_info(self) -> dict:
        """
        Get information about the graph structure
        """
        if not self.db.has_graph(self.graph_name):
            return {"error": "Graph does not exist"}
        
        graph = self.db.graph(self.graph_name)
        
        return {
            "name": self.graph_name,
            "edge_definitions": graph.edge_definitions(),
            "vertex_collections": graph.vertex_collections(),
            "edge_collections": [ed["edge_collection"] for ed in graph.edge_definitions()]
        }
