from app.agents.trigger_monitor import TriggerMonitorAgent
from app.agents.icp_matcher import ICPMatcherAgent
from app.agents.company_enricher import CompanyEnricherAgent
from app.agents.persona_finder import PersonaFinderAgent
from app.agents.contact_enricher import ContactEnricherAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.validator_agent import ValidatorAgent
from app.agents.shadow_agent import ShadowAgent

# Instantiate singletons
trigger_monitor = TriggerMonitorAgent()
icp_matcher = ICPMatcherAgent()
company_enricher = CompanyEnricherAgent()
persona_finder = PersonaFinderAgent()
contact_enricher = ContactEnricherAgent()
summary_agent = SummaryAgent()
validator_agent = ValidatorAgent()
shadow_agent = ShadowAgent()

# Registry
agent_registry = {
    "trigger_monitor": trigger_monitor,
    "icp_matcher": icp_matcher,
    "company_enricher": company_enricher,
    "persona_finder": persona_finder,
    "contact_enricher": contact_enricher,
    "summary_agent": summary_agent,
    "validator_agent": validator_agent,
    "shadow_agent": shadow_agent
}

def get_agent(name: str):
    return agent_registry.get(name)
