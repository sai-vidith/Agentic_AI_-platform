from typing import Dict, Any, List, Tuple
from app.config import get_business_config

class GuardrailsEngine:
    """Validates inputs and outputs against safety policy configurations."""
    
    def __init__(self):
        # Load safety configurations
        config = get_business_config()
        guardrails_config = config.get("guardrails", {})
        
        # Load policies
        policies = guardrails_config.get("policies", [])
        self.blocked_keywords = []
        for policy in policies:
            if policy.get("type") == "guardrail":
                self.blocked_keywords.extend(policy.get("blocked_keywords", []))

    def validate_content(self, text: str) -> Tuple[bool, List[str]]:
        """Checks if text contains any blocked keywords. Returns (is_safe, violations)."""
        if not text:
            return True, []
            
        violations = []
        text_lower = text.lower()
        
        for keyword in self.blocked_keywords:
            if keyword.lower() in text_lower:
                violations.append(f"Content contained blocked keyword: '{keyword}'")
                
        return len(violations) == 0, violations

# Shared instance
guardrails = GuardrailsEngine()
