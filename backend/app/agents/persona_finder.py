import json
from typing import Dict, Any, List
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes

class PersonaFinderAgent(BaseNexusAgent):
    """Filters and identifies key decision makers matching YAML persona definitions."""
    
    def __init__(self):
        super().__init__(name="persona_finder")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        raw_contacts = task_input.get("raw_enrichment_data", {}).get("contacts", [])
        persona_rules = task_input.get("persona_rules", {})
        
        print(f"[PersonaFinder] Received {len(raw_contacts)} raw contacts from enrichment: {json.dumps(raw_contacts, indent=2)}")
        
        # If we have real scraped contacts, clean them up and use them directly
        if raw_contacts:
            cleaned_contacts = []
            for i, c in enumerate(raw_contacts):
                name = c.get("name", "").replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
                # Remove patterns like "John Doe - CEO at Company - LinkedIn"
                if " - " in name:
                    name = name.split(" - ")[0].strip()
                if " | " in name:
                    name = name.split(" | ")[0].strip()
                    
                title_snippet = c.get("title", "")
                linkedin = c.get("linkedin", "")
                
                # Try to infer a title from the snippet
                title = "Executive"
                title_lower = title_snippet.lower()
                if "ceo" in title_lower or "chief executive" in title_lower:
                    title = "CEO"
                elif "cto" in title_lower or "chief technology" in title_lower:
                    title = "CTO"
                elif "cfo" in title_lower or "chief financial" in title_lower:
                    title = "CFO"
                elif "vp" in title_lower or "vice president" in title_lower:
                    title = "VP of Engineering"
                elif "head of" in title_lower:
                    # Extract "Head of X"
                    import re
                    match = re.search(r'(head of \w+)', title_lower)
                    title = match.group(1).title() if match else "Head of Operations"
                elif "founder" in title_lower:
                    title = "Founder"
                elif "director" in title_lower:
                    title = "Director"
                elif "engineer" in title_lower or "software" in title_lower:
                    title = "Engineering Lead"
                
                if name and len(name) > 2:
                    cleaned_contacts.append({
                        "name": name,
                        "title": title,
                        "email": "unknown",
                        "phone": "unknown",
                        "linkedin": linkedin,
                        "joined_date": "Unknown",
                        "persona_rank": i + 1
                    })
            
            if cleaned_contacts:
                print(f"[PersonaFinder] Cleaned {len(cleaned_contacts)} real contacts: {json.dumps(cleaned_contacts, indent=2)}")
                await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": cleaned_contacts})
                return {"contacts": cleaned_contacts}
        
        # Fall back to LLM if no scraped contacts
        prompt = f"""
        Find the most likely decision maker at {company_name} for an HR SaaS product pitch.
        
        Persona Guidelines:
        {json.dumps(persona_rules)}
        
        IMPORTANT: You MUST use REAL names of actual people who work at {company_name}. 
        Do NOT generate fake names. Search your knowledge for real executives at {company_name}.
        
        Return the matched decision makers, sorted by priority.
        Format strictly as JSON:
        {{
          "matched_contacts": [
            {{
              "name": "Full Name of a REAL person at {company_name}",
              "title": "Exact Title",
              "email": "unknown",
              "phone": "unknown",
              "linkedin": "linkedin profile url if known",
              "joined_date": "unknown",
              "persona_rank": 1
            }}
          ]
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        matched = data.get("matched_contacts", [])
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": matched})
        return {"contacts": matched}

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        # Even in fallback, try to use enrichment contacts if they exist
        raw_contacts = task_input.get("raw_enrichment_data", {}).get("contacts", [])
        company = task_input.get("company_name", "Unknown Company")
        
        if raw_contacts:
            cleaned = []
            for i, c in enumerate(raw_contacts):
                name = c.get("name", "").replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
                if " - " in name:
                    name = name.split(" - ")[0].strip()
                if name and len(name) > 2:
                    cleaned.append({
                        "name": name,
                        "title": c.get("title", "Executive")[:50],
                        "email": "unknown",
                        "phone": "unknown",
                        "linkedin": c.get("linkedin", ""),
                        "persona_rank": i + 1
                    })
            if cleaned:
                return {"contacts": cleaned}
        
        # Last resort fallback using LLM knowledge
        return {"contacts": [{
            "name": f"VP of People at {company}",
            "title": "VP of People",
            "email": "unknown",
            "phone": "unknown",
            "linkedin": "unknown",
            "persona_rank": 1
        }]}
