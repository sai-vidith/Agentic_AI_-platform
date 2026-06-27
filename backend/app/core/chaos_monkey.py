import random
from typing import List

class ChaosMonkey:
    """Toggles and manages simulated failures in agent runs."""
    
    def __init__(self):
        self.enabled = False
        self.failure_targets = ["company_enricher", "news_tool"]
        
    def toggle(self, enable: bool):
        self.enabled = enable

    def should_fail(self, agent_name: str) -> bool:
        if not self.enabled:
            return False
        # 80% failure rate for targets
        return agent_name in self.failure_targets and random.random() < 0.8
        
    def inject_failure(self, agent_name: str):
        failures = [
            TimeoutError(f"Simulated timeout error in agent '{agent_name}'"),
            ConnectionError(f"DNS resolution failed when agent '{agent_name}' accessed external tool"),
            RuntimeError(f"500 Internal upstream API error injected in agent '{agent_name}'")
        ]
        raise random.choice(failures)

# Shared instance
chaos_monkey = ChaosMonkey()
