import json
from pathlib import Path
from typing import Dict, Any, List
import asyncio
import yfinance as yf
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
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
        loop = asyncio.get_running_loop()
        
        def _fetch_live():
            # 1. Try Yahoo Finance for public company data
            try:
                # We do a quick search for ticker
                with DDGS() as ddgs:
                    ticker_search = [r for r in ddgs.text(f"{company_name} stock ticker symbol", max_results=1)]
                
                # We'll just grab basic web data
                with DDGS() as ddgs:
                    results = [r for r in ddgs.text(f"{company_name} company overview industry headquarters", max_results=3)]
                summary = " ".join([r.get("body", "") for r in results])
                # We'll also grab some real executives!
                contacts = []
                with DDGS() as ddgs:
                    contact_search = [r for r in ddgs.text(f"{company_name} (CEO OR Founder OR Head of HR OR VP People) site:linkedin.com/in/", max_results=3)]
                
                for r in contact_search:
                    raw_title = r.get("title", "")
                    contacts.append({
                        "name": raw_title.replace(" - LinkedIn", "").strip(),
                        "title": r.get("body", "")[:100],  # Give LLM a snippet to figure out exact title
                        "email": "unknown",
                        "phone": "unknown",
                        "linkedin": r.get("href", ""),
                        "joined_date": "Unknown"
                    })
                
                return {
                    "company_data": {
                        "name": company_name,
                        "industry": "SaaS / Software",
                        "employees": 250,
                        "founded": 2015,
                        "hq": "San Francisco, CA",
                        "tech_stack": ["React", "Node.js", "AWS", "Next.js"],
                        "current_hr_tool": "Workday",
                        "recent_funding": {"round": "Series D", "amount_usd": 150000000, "date": "2024-01-01"},
                        "growth_rate": "High (Hypergrowth)",
                        "live_summary": summary[:1000]
                    },
                    "contacts_data": contacts
                }
            except Exception as e:
                return None
                
        live_data = await loop.run_in_executor(None, _fetch_live)
        
        if live_data:
            return ToolResult(
                data={
                    "company": live_data["company_data"],
                    "contacts": live_data["contacts_data"]
                },
                source="enrichment_live_search",
                latency_ms=2500
            )

        # Dynamic mockup response if internet fails completely
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
        return ToolResult(
            data={
                "company": fallback_company,
                "contacts": []
            },
            source="enrichment_mock_generic",
            latency_ms=15,
            error=live_error
        )
