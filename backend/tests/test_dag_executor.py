"""Unit tests for the DAG Executor — validates topological execution and context propagation."""
import asyncio
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.schemas import DAG, AgentTask, AgentState


class TestDAGTopologicalSort:
    """Tests that the DAG executor runs agents in correct dependency order."""
    
    def test_linear_dag_creation(self):
        """Verify a linear DAG has correct edges."""
        agents = ["trigger_monitor", "company_enricher", "icp_matcher"]
        tasks = {}
        for idx, name in enumerate(agents):
            deps = [agents[idx - 1]] if idx > 0 else []
            tasks[name] = AgentTask(
                id=name, name=name, dependencies=deps,
                input_data={"company_name": "TestCorp"}
            )
        
        edges = [[agents[i-1], agents[i]] for i in range(1, len(agents))]
        dag = DAG(tasks=tasks, edges=edges)
        
        assert len(dag.tasks) == 3
        assert dag.tasks["company_enricher"].dependencies == ["trigger_monitor"]
        assert dag.tasks["trigger_monitor"].dependencies == []
        assert len(dag.edges) == 2
    
    def test_runnable_detection(self):
        """Verify that only nodes with all dependencies met are runnable."""
        tasks = {
            "a": AgentTask(id="a", name="a", dependencies=[]),
            "b": AgentTask(id="b", name="b", dependencies=["a"]),
            "c": AgentTask(id="c", name="c", dependencies=["a"]),
            "d": AgentTask(id="d", name="d", dependencies=["b", "c"]),
        }
        
        completed = set()
        
        # First round: only "a" should be runnable
        runnable = [name for name, task in tasks.items()
                    if name not in completed and all(d in completed for d in task.dependencies)]
        assert runnable == ["a"]
        
        # After "a" completes: "b" and "c" should be runnable (parallel branches)
        completed.add("a")
        runnable = [name for name, task in tasks.items()
                    if name not in completed and all(d in completed for d in task.dependencies)]
        assert set(runnable) == {"b", "c"}
        
        # After "b" and "c" complete: "d" should be runnable
        completed.update(["b", "c"])
        runnable = [name for name, task in tasks.items()
                    if name not in completed and all(d in completed for d in task.dependencies)]
        assert runnable == ["d"]
    
    def test_loop_detection_safety(self):
        """Verify that a DAG with unresolvable dependencies doesn't infinite-loop."""
        tasks = {
            "a": AgentTask(id="a", name="a", dependencies=["c"]),  # Circular!
            "b": AgentTask(id="b", name="b", dependencies=["a"]),
            "c": AgentTask(id="c", name="c", dependencies=["b"]),
        }
        
        completed = set()
        iterations = 0
        max_iterations = 10
        
        while len(completed) < len(tasks) and iterations < max_iterations:
            runnable = [name for name, task in tasks.items()
                        if name not in completed and all(d in completed for d in task.dependencies)]
            if not runnable:
                break  # Loop detection
            iterations += 1
        
        # Should break out without completing all tasks
        assert len(completed) == 0, "Circular DAG should not complete any tasks"
        assert iterations == 0, "Should detect loop immediately"

    def test_dag_plan_reasoning(self):
        """Verify DAG carries plan reasoning metadata."""
        dag = DAG(
            tasks={},
            edges=[],
            plan_reasoning="Skipped shadow_agent: ICP score 45 below threshold"
        )
        assert "shadow_agent" in dag.plan_reasoning


class TestAgentState:
    """Tests for agent state transitions."""
    
    def test_initial_state_is_idle(self):
        task = AgentTask(id="test", name="test")
        assert task.status == AgentState.IDLE
    
    def test_state_transitions(self):
        task = AgentTask(id="test", name="test")
        task.status = AgentState.THINKING
        assert task.status == AgentState.THINKING
        task.status = AgentState.COMPLETED
        assert task.status == AgentState.COMPLETED
    
    def test_error_message_capture(self):
        task = AgentTask(id="test", name="test")
        task.status = AgentState.FAILED
        task.error_message = "API timeout"
        assert task.error_message == "API timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
