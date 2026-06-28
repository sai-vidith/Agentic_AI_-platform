import json
from typing import Dict, Any, List
from app.core.memory import vector_store

class FeedbackManager:
    """Manages Human-in-the-Loop decision learning to enable In-Context Reinforcement Learning."""
    
    def record_feedback(self, lead_data: Dict[str, Any], action: str):
        """Saves approved/rejected lead profiles to the vector store to guide future runs."""
        lead_id = lead_data.get("id")
        company_name = lead_data.get("company_name", "")
        company_details = lead_data.get("company_details", {})
        icp_score = lead_data.get("icp_score", 0)
        
        # Format profile description dynamically
        industry = company_details.get("industry", "Unknown") if isinstance(company_details, dict) else "Unknown"
        employees = company_details.get("employees", "Unknown") if isinstance(company_details, dict) else "Unknown"
        tech_stack = company_details.get("tech_stack", []) if isinstance(company_details, dict) else []
        current_hr_tool = company_details.get("current_hr_tool", "Unknown") if isinstance(company_details, dict) else "Unknown"
        
        profile_text = (
            f"Company: {company_name}. "
            f"Industry: {industry}. "
            f"Employees: {employees}. "
            f"Tech Stack: {', '.join(tech_stack) if isinstance(tech_stack, list) else str(tech_stack)}. "
            f"Current HR Tool: {current_hr_tool}."
        )
        
        metadata = {
            "lead_id": lead_id,
            "company_name": company_name,
            "action": action,  # "approve" or "reject"
            "icp_score": icp_score
        }
        
        # Add to vector store for dynamic retrieval
        try:
            vector_store.add_document(
                doc_id=f"feedback_{lead_id}",
                text=profile_text,
                metadata=metadata
            )
            print(f"[FeedbackManager] Recorded human decision '{action.upper()}' for {company_name}")
        except Exception as e:
            print(f"[FeedbackManager] Failed to record feedback: {e}")

    def get_similar_feedback(self, company_name: str, company_details: Dict[str, Any], limit: int = 4) -> Dict[str, List[str]]:
        """Queries vector DB to get similar approved and rejected examples for prompt context."""
        if not isinstance(company_details, dict):
            company_details = {}
            
        industry = company_details.get("industry", "Unknown")
        employees = company_details.get("employees", "Unknown")
        tech_stack = company_details.get("tech_stack", [])
        
        query = (
            f"Company: {company_name}. "
            f"Industry: {industry}. "
            f"Employees: {employees}. "
            f"Tech Stack: {', '.join(tech_stack) if isinstance(tech_stack, list) else str(tech_stack)}."
        )
        
        feedback = {
            "approved": [],
            "rejected": []
        }
        
        try:
            results = vector_store.similarity_search(query, limit=limit)
            for doc in results:
                meta = doc.get("metadata", {})
                action = meta.get("action")
                company = meta.get("company_name", "Unknown")
                score = meta.get("icp_score", 0)
                
                # Format bullet point for context
                example = f"- {company} (Industry: {industry}, Size: {employees} employees, ICP Score: {score}/100)"
                if action == "approve":
                    feedback["approved"].append(example)
                elif action == "reject":
                    feedback["rejected"].append(example)
        except Exception as e:
            print(f"[FeedbackManager] Error querying similar feedback: {e}")
            
        return feedback

feedback_manager = FeedbackManager()
