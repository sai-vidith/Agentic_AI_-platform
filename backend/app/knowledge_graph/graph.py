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

    def find_warm_connections_by_tech(self, target_company: str) -> List[Dict[str, Any]]:
        """
        Finds other companies that share technologies with the target company.
        Path: Target Company -> USES_TECH -> Tech -> USES_TECH -> Other Company
        """
        if not self.graph.has_node(target_company):
            return []
            
        # Get all technologies used by target company
        target_techs = {
            node for node in self.graph.neighbors(target_company)
            if self.graph.nodes[node].get("type") == "technology"
        }
        
        connections = []
        seen = set()
        
        for tech in target_techs:
            # Find other companies using the same tech stack
            for other_company in self.graph.predecessors(tech):
                if other_company == target_company or other_company in seen:
                    continue
                    
                attrs = self.graph.nodes[other_company]
                if attrs.get("type") == "company":
                    seen.add(other_company)
                    connections.append({
                        "company": other_company,
                        "shared_tech": tech,
                        "hq": attrs.get("hq", attrs.get("headquarters", "Unknown")),
                        "icp_score": attrs.get("icp_score", 0),
                        "status": attrs.get("status", "new")
                    })
        # Sort by ICP score to return highest quality peers first
        return sorted(connections, key=lambda c: c["icp_score"], reverse=True)[:5]

    def find_influence_paths(self, target_company: str) -> List[List[str]]:
        """
        Finds paths of relationship influence between known executives in the target company and other persons.
        E.g. Person A -> INFLUENCES -> Person B -> WORKS_AT -> Target Company
        """
        if not self.graph.has_node(target_company):
            return []
            
        # Find members working at the target company
        members = []
        for source in self.graph.predecessors(target_company):
            if self.graph.edges[source, target_company].get("relation") == "WORKS_AT":
                members.append(source)
        
        paths = []
        # Check for influence edges involving members
        for member in members:
            # Undirected search to find influence bridges
            for node in self.graph.predecessors(member):
                if self.graph.has_edge(node, member):
                    rel = self.graph[node][member].get("relation", "")
                    if rel == "INFLUENCES":
                        paths.append([node, "INFLUENCES", member, "WORKS_AT", target_company])
            for node in self.graph.neighbors(member):
                if self.graph.has_edge(member, node):
                    rel = self.graph[member][node].get("relation", "")
                    if rel == "INFLUENCES":
                        paths.append([member, "INFLUENCES", node, "WORKS_AT", target_company])
                    
        return paths


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
