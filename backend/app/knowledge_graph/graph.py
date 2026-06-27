import networkx as nx
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

GRAPH_PATH = Path(__file__).resolve().parent.parent / "mock_data" / "knowledge_graph.json"

class KnowledgeGraphManager:
    """Manages the in-memory NetworkX Knowledge Graph and persists it."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.load_graph()

    def load_graph(self):
        if GRAPH_PATH.exists():
            try:
                with open(GRAPH_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct Graph from serialized links
                    for node in data.get("nodes", []):
                        self.graph.add_node(node["id"], **node.get("attributes", {}))
                    for edge in data.get("edges", []):
                        self.graph.add_edge(edge["from"], edge["to"], relation=edge.get("relation", ""))
            except Exception as e:
                print(f"Error loading graph from disk: {e}. Starting fresh.")
                self.graph = nx.DiGraph()
        else:
            self.graph = nx.DiGraph()

    def save_graph(self):
        # Create parent dirs if not existing
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        nodes = []
        for n, attrs in self.graph.nodes(data=True):
            nodes.append({"id": n, "attributes": attrs})
        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            edges.append({"from": u, "to": v, "relation": attrs.get("relation", "")})
            
        with open(GRAPH_PATH, "w", encoding="utf-8") as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

    def add_entity(self, name: str, entity_type: str, attributes: Dict[str, Any] = None):
        if not attributes:
            attributes = {}
        attributes["type"] = entity_type
        self.graph.add_node(name, **attributes)
        self.save_graph()

    def add_relation(self, source: str, target: str, relation: str):
        # Ensure nodes exist
        if not self.graph.has_node(source):
            self.graph.add_node(source, type="unknown")
        if not self.graph.has_node(target):
            self.graph.add_node(target, type="unknown")
        self.graph.add_edge(source, target, relation=relation)
        self.save_graph()

    def query_connections(self, entity_name: str) -> List[Tuple[str, str, str]]:
        """Returns direct outbound and inbound connections for an entity."""
        if not self.graph.has_node(entity_name):
            return []
            
        connections = []
        # Outbound edges
        for target in self.graph.neighbors(entity_name):
            rel = self.graph[entity_name][target].get("relation", "")
            connections.append((entity_name, rel, target))
            
        # Inbound edges
        for source in self.graph.predecessors(entity_name):
            rel = self.graph[source][entity_name].get("relation", "")
            connections.append((source, rel, entity_name))
            
        return connections

    def get_subgraph_data(self, start_nodes: List[str], depth: int = 1) -> Dict[str, Any]:
        """Gets node/edge data surrounding start_nodes to display visually."""
        visited = set(start_nodes)
        queue = list(start_nodes)
        
        # Simple BFS to find surrounding nodes
        for _ in range(depth):
            next_level = []
            for node in queue:
                if not self.graph.has_node(node):
                    continue
                # Outbound
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.append(neighbor)
                # Inbound
                for pred in self.graph.predecessors(node):
                    if pred not in visited:
                        visited.add(pred)
                        next_level.append(pred)
            queue = next_level

        sub_nodes = []
        sub_edges = []
        
        for node in visited:
            if not self.graph.has_node(node):
                continue
            sub_nodes.append({
                "id": node,
                "label": node,
                "type": self.graph.nodes[node].get("type", "unknown")
            })
            
        for u, v in self.graph.edges():
            if u in visited and v in visited:
                sub_edges.append({
                    "source": u,
                    "target": v,
                    "relation": self.graph[u][v].get("relation", "")
                })
                
        return {"nodes": sub_nodes, "edges": sub_edges}

# Shared singleton instance
kg_manager = KnowledgeGraphManager()
