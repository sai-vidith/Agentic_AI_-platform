"""Unit tests for the relational GraphRAG multi-hop traversals."""
import pytest
import networkx as nx
from app.knowledge_graph.graph import KnowledgeGraphManager

@pytest.fixture
def temp_graph_manager():
    """Returns a KnowledgeGraphManager with a clean test graph."""
    manager = KnowledgeGraphManager()
    # Replace in-memory graph with a blank directed graph for isolated testing
    manager.graph = nx.DiGraph()
    return manager

def test_find_warm_connections_by_tech(temp_graph_manager):
    mgr = temp_graph_manager
    
    # 1. Setup target company and its technology stack
    mgr.add_entity("TargetFintech", "company")
    mgr.add_entity("Python", "technology")
    mgr.add_entity("React", "technology")
    
    mgr.add_relation("TargetFintech", "Python", "USES_TECH")
    mgr.add_relation("TargetFintech", "React", "USES_TECH")
    
    # 2. Setup a peer company using the same technology (with low ICP)
    mgr.add_entity("PeerA", "company", {"icp_score": 40, "status": "new"})
    mgr.add_relation("PeerA", "Python", "USES_TECH")
    
    # 3. Setup a high-quality client company using the same technology (with high ICP)
    mgr.add_entity("ClientB", "company", {"icp_score": 90, "status": "closed_won"})
    mgr.add_relation("ClientB", "React", "USES_TECH")
    
    # 4. Run Tech stack traversal query
    results = mgr.find_warm_connections_by_tech("TargetFintech")
    
    # Verify results are sorted by icp_score (ClientB first, then PeerA)
    assert len(results) == 2
    assert results[0]["company"] == "ClientB"
    assert results[0]["shared_tech"] == "React"
    assert results[0]["icp_score"] == 90
    assert results[1]["company"] == "PeerA"
    assert results[1]["shared_tech"] == "Python"

def test_find_influence_paths(temp_graph_manager):
    mgr = temp_graph_manager
    
    # 1. Setup target company and its hiring manager
    mgr.add_entity("TargetFintech", "company")
    mgr.add_entity("Priya Sharma", "person")
    mgr.add_relation("Priya Sharma", "TargetFintech", "WORKS_AT")
    
    # 2. Setup an influencer (e.g., an advisor or investor)
    mgr.add_entity("Alex Stamos", "person")
    mgr.add_relation("Alex Stamos", "Priya Sharma", "INFLUENCES")
    
    # 3. Run influence path traversal query
    paths = mgr.find_influence_paths("TargetFintech")
    
    assert len(paths) == 1
    assert paths[0] == ["Alex Stamos", "INFLUENCES", "Priya Sharma", "WORKS_AT", "TargetFintech"]

def test_nonexistent_entity(temp_graph_manager):
    mgr = temp_graph_manager
    assert mgr.find_warm_connections_by_tech("GhostCorp") == []
    assert mgr.find_influence_paths("GhostCorp") == []
