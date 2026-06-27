import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

# Root directory for mock/golden data
DATA_DIR = Path(__file__).resolve().parent.parent / "mock_data"

class ToolResult:
    def __init__(self, data: Any, source: str, latency_ms: int = 50, error: Optional[str] = None):
        self.data = data
        self.source = source
        self.latency_ms = latency_ms
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "source": self.source,
            "latency_ms": self.latency_ms,
            "error": self.error
        }

class BaseTool(ABC):
    """Base class for all agent tools. Handles Golden Path routing."""
    
    GOLDEN_COMPANIES = {"RazorX Fintech", "RazorX", "AcmeCorp", "ApexData"}
    
    def __init__(self, name: str):
        self.name = name

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        company_name = params.get("company_name", "")
        company_key = self._match_golden_company(company_name)
        
        # Golden Path routing
        if company_key:
            return await self._get_golden_data(company_key, params)
        
        # Fallback to live path
        try:
            return await self._execute_live(params)
        except Exception as e:
            # If live fails, fall back to general mock data if available
            return await self._get_fallback_mock_data(company_name, params, str(e))

    def _match_golden_company(self, name: str) -> Optional[str]:
        if not name:
            return None
        name_lower = name.lower()
        for gc in self.GOLDEN_COMPANIES:
            if gc.lower() in name_lower or name_lower in gc.lower():
                # Map to standard file name
                if "razorx" in name_lower:
                    return "razorx"
                if "acme" in name_lower:
                    return "acmecorp"
                if "apex" in name_lower:
                    return "apexdata" # Wait, we can map to apexdata if we have golden path, or just use general mock
        return None

    async def _get_golden_data(self, company_key: str, params: Dict[str, Any]) -> ToolResult:
        golden_file = DATA_DIR / "golden" / f"{company_key}.json"
        if not golden_file.exists():
            # Try loading general mock
            return await self._get_fallback_mock_data(company_key, params, f"Golden file {company_key}.json not found")
            
        with open(golden_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Customize returned data based on tool type
        result_data = self._slice_golden_data(data)
        return ToolResult(data=result_data, source="golden_path", latency_ms=50)

    @abstractmethod
    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        """Each tool extracts its required slice of the golden data."""
        pass

    @abstractmethod
    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        """Execute real API call (Serper, NewsAPI, Firecrawl, etc.)."""
        pass

    async def _get_fallback_mock_data(self, company_name: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        """Default fallback mock handler to ensure resilience."""
        # Simple generic mock response to prevent system crashes
        return ToolResult(
            data={"message": f"Simulated fallback data for {company_name}", "error_context": live_error},
            source="mock_fallback",
            latency_ms=100
        )
