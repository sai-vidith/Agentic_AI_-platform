"""Token cost and latency metrics tracker for LLM usage across the platform."""
from datetime import datetime, timezone
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict


# Estimated cost per 1M tokens (input/output) for free-tier providers
COST_TABLE = {
    "groq/llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},   # Free tier
    "groq/llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},       # Free tier
    "cerebras/llama-3.3-70b": {"input": 0.0, "output": 0.0},          # Free tier
    "gemini/gemini-2.0-flash": {"input": 0.0, "output": 0.0},         # Free tier
    "mock": {"input": 0.0, "output": 0.0},
}


@dataclass
class LLMCallMetric:
    model: str
    agent_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    timestamp: str = ""
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """Collects and aggregates LLM usage metrics across all agent calls."""
    
    def __init__(self):
        self.call_history: List[LLMCallMetric] = []
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.total_calls = 0
        self.failed_calls = 0
    
    def record_call(
        self,
        model: str,
        agent_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
    ):
        """Record a single LLM API call metric."""
        total = input_tokens + output_tokens
        
        # Calculate estimated cost
        cost_per_m = COST_TABLE.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens * cost_per_m["input"] + output_tokens * cost_per_m["output"]) / 1_000_000
        
        metric = LLMCallMetric(
            model=model,
            agent_name=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            estimated_cost_usd=cost,
            timestamp=datetime.now(timezone.utc).isoformat(),
            success=success,
        )
        
        self.call_history.append(metric)
        self.total_tokens += total
        self.total_cost_usd += cost
        self.total_calls += 1
        if not success:
            self.failed_calls += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        by_agent = {}
        by_model = {}
        
        for m in self.call_history:
            # Per agent
            if m.agent_name not in by_agent:
                by_agent[m.agent_name] = {"calls": 0, "tokens": 0, "cost": 0.0, "avg_latency_ms": 0}
            by_agent[m.agent_name]["calls"] += 1
            by_agent[m.agent_name]["tokens"] += m.total_tokens
            by_agent[m.agent_name]["cost"] += m.estimated_cost_usd
            
            # Per model
            if m.model not in by_model:
                by_model[m.model] = {"calls": 0, "tokens": 0}
            by_model[m.model]["calls"] += 1
            by_model[m.model]["tokens"] += m.total_tokens
        
        # Calculate average latencies
        for agent_name in by_agent:
            agent_calls = [m for m in self.call_history if m.agent_name == agent_name]
            if agent_calls:
                by_agent[agent_name]["avg_latency_ms"] = sum(m.latency_ms for m in agent_calls) // len(agent_calls)
        
        return {
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "by_agent": by_agent,
            "by_model": by_model,
        }
    
    def get_recent_calls(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent LLM call metrics."""
        return [m.to_dict() for m in self.call_history[-limit:]]


# Shared singleton
metrics_collector = MetricsCollector()
