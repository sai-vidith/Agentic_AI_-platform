import json
from pathlib import Path
from typing import Dict, Any, List
from app.tools.base_tool import BaseTool, ToolResult, DATA_DIR

class EnrichmentTool(BaseTool):
    """Enrichment tool for companies and decision-maker contacts."""
    
    def __init__(self):
        super().__init__(name="enrichment_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        # Returns the entire golden dict, including company, contacts, and graph edges
        return golden_data

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        company_name = params.get("company_name", "")
        if not company_name:
            return ToolResult(data={}, source="enrichment_live")

        # Query mock database files
        companies_path = DATA_DIR / "companies.json"
        contacts_path = DATA_DIR / "contacts.json"
        
        company_info = {}
        contacts_info = []
        
        if companies_path.exists():
            with open(companies_path, "r", encoding="utf-8") as f:
                companies = json.load(f)
                # Find matching company
                for c in companies:
                    if company_name.lower() in c.get("name", "").lower():
                        company_info = c
                        break
                        
        if contacts_path.exists():
            with open(contacts_path, "r", encoding="utf-8") as f:
                contacts = json.load(f)
                for entry in contacts:
                    if company_name.lower() in entry.get("company_name", "").lower():
                        contacts_info = entry.get("contacts", [])
                        break

        if company_info:
            return ToolResult(
                data={
                    "company": company_info,
                    "contacts": contacts_info
                },
                source="enrichment_mock_db",
                latency_ms=10
            )
            
        return await self._get_fallback_mock_data(company_name, params, "Company not found in mock database")

    async def _get_fallback_mock_data(self, company_name: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        # Dynamic mockup response for companies not in database
        fallback_company = {
            "name": company_name,
            "industry": "Software",
            "employees": 120,
            "founded": 2021,
            "hq": "San Francisco, US",
            "tech_stack": ["React", "Node.js", "Slack", "Google Workspace"],
            "current_hr_tool": "Excel",
            "recent_funding": {"round": "Series A", "amount_usd": 12000000, "date": "2026-02-01"},
            "growth_rate": "30% headcount growth"
        }
        fallback_contacts = [
            {
                "name": "Jane Smith",
                "title": "Head of People",
                "email": "jane.smith@generic.io",
                "phone": "+1-555-0155",
                "linkedin": f"linkedin.com/in/janesmith-{company_name.lower().replace(' ', '')}",
                "joined_date": "2025-05-10"
            }
        ]
        return ToolResult(
            data={
                "company": fallback_company,
                "contacts": fallback_contacts
            },
            source="enrichment_mock_generic",
            latency_ms=15,
            error=live_error
        )
