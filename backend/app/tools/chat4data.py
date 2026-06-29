import json
import re
from typing import Dict, Any, List, Optional
from app.tools.base_tool import BaseTool, ToolResult
from app.tools.llm_tool import llm_service
from app.config import settings

class Chat4DataTool(BaseTool):
    """
    Chat4Data is a structured extraction engine. 
    It processes raw scraped text/HTML from BeautifulSoup/Scrapy and uses LLM routing
    to parse and return strict JSON structures matching our database schemas.
    """
    def __init__(self):
        super().__init__(name="chat4data")

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        text = params.get("text", "")
        schema_type = params.get("schema_type", "both")  # "company", "contacts", or "both"
        company_name = params.get("company_name", "Target Company")
        domain = params.get("domain", "hr_saas")

        if not text:
            return ToolResult(data={"company_details": {}, "contacts": []}, source="chat4data_empty")

        prompt = f"""
        You are Chat4Data, an elite structured web-scraping parser.
        Your task is to extract high-accuracy structured data from the raw scraped page text below.
        
        Domain context: {domain}
        Company name query: {company_name}
        
        Raw scraped text:
        ---
        {text[:6000]}
        ---
        
        Extract information matching the following JSON schema:
        {{
          "company_details": {{
            "name": "Exact company name",
            "industry": "Specific industry (e.g. Cybersecurity, HR Tech, EdTech)",
            "website": "Company website homepage URL",
            "linkedin": "LinkedIn company page URL",
            "employees": null, // integer count of employees if found, otherwise null
            "founded": null, // integer founding year if found, otherwise null
            "hq": "City, Country headquarters location",
            "description": "2-3 sentence overview of what the company does",
            "tech_stack": ["List of core tech tools or software used if mentioned"],
            "current_hr_tool": "HR SaaS tool or ATS system identified if mentioned, otherwise unknown",
            "growth_rate": "e.g. High (Hypergrowth), Stable, or null",
            "recent_funding": {{
              "round": "e.g. Series A / Seed / null",
              "amount_usd": null, // integer amount in USD or null
              "date": "YYYY-MM-DD or null"
            }}
          }},
          "contacts": [
            {{
              "name": "Full name of executive or key contact",
              "title": "Exact professional title (e.g. Chief Information Security Officer, VP of Talent)",
              "persona_match": "Must match one of: CEO, CTO, CISO, VP_HR, HEAD_RECRUITING, VP_ENG, IT_DIR",
              "confidence": "HIGH, MEDIUM, or LOW",
              "linkedin": "LinkedIn profile URL or unknown",
              "email": "email address or unknown",
              "phone": "phone number or unknown"
            }}
          ]
        }}
        
        Rules:
        1. Only output valid JSON. No conversational wrapper or explanations.
        2. If a field is not found, set it to null or "unknown" as schema indicates.
        3. Do not hallucinate or guess fields unless they are supported by the scraped text.
        """

        try:
            # Execute structured LLM completion
            llm_response = await llm_service.acompletion(
                messages=[
                    {"role": "system", "content": "You are Chat4Data. You only output valid JSON conforming exactly to the requested schema. No prose."},
                    {"role": "user", "content": prompt}
                ],
                agent_name="chat4data",
                response_format={"type": "json_object"}
            )
            
            # Extract content from LiteLLM response structure
            content = ""
            if hasattr(llm_response, "choices") and llm_response.choices:
                content = llm_response.choices[0].message.content
            elif isinstance(llm_response, dict) and "choices" in llm_response:
                content = llm_response["choices"][0]["message"]["content"]
            else:
                content = str(llm_response)

            # Strip any markdown backticks if returned
            content_clean = re.sub(r"^```json\s*", "", content.strip())
            content_clean = re.sub(r"\s*```$", "", content_clean)
            
            parsed_data = json.loads(content_clean)
            
            # Normalize schema
            company_details = parsed_data.get("company_details", {})
            contacts = parsed_data.get("contacts", [])

            # Filter response based on requested schema_type
            if schema_type == "company":
                return ToolResult(data={"company_details": company_details}, source="chat4data_live")
            elif schema_type == "contacts":
                return ToolResult(data={"contacts": contacts}, source="chat4data_live")
            else:
                return ToolResult(data={"company_details": company_details, "contacts": contacts}, source="chat4data_live")

        except Exception as e:
            print(f"[Chat4Data] Live extraction failed: {e}. Checking mock fallback...")
            return await self._get_fallback_mock_data(company_name, params, str(e))

    async def _get_fallback_mock_data(self, company_name: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        # Check settings first
        if not settings.ALLOW_MOCK_FALLBACK:
            raise ValueError(f"Chat4Data live parsing failed: {live_error}")

        # Basic fallback matching the expected database schema
        mock_company = {
            "name": company_name,
            "industry": "Technology",
            "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
            "linkedin": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}",
            "employees": 150,
            "founded": 2020,
            "hq": "San Francisco, USA",
            "description": f"{company_name} is a leading innovator in technology services.",
            "tech_stack": ["React", "Python", "Cloudflare"],
            "current_hr_tool": "Workday",
            "growth_rate": "Stable",
            "recent_funding": {"round": "Series B", "amount_usd": 20000000, "date": "2025-01-01"}
        }

        mock_contacts = [
            {
                "name": f"Jane Doe",
                "title": "CTO",
                "persona_match": "CTO",
                "confidence": "HIGH",
                "linkedin": "https://www.linkedin.com/in/janedoe",
                "email": "unknown",
                "phone": "unknown"
            }
        ]

        schema_type = params.get("schema_type", "both")
        if schema_type == "company":
            return ToolResult(data={"company_details": mock_company}, source="chat4data_mock", error=live_error)
        elif schema_type == "contacts":
            return ToolResult(data={"contacts": mock_contacts}, source="chat4data_mock", error=live_error)
        else:
            return ToolResult(data={"company_details": mock_company, "contacts": mock_contacts}, source="chat4data_mock", error=live_error)

# Singleton tool instance
chat4data = Chat4DataTool()
