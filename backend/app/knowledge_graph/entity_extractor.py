import json
from typing import List, Dict, Any
from app.tools.llm_tool import llm_service
from app.knowledge_graph.graph import kg_manager

class BatchEntityExtractor:
    """Extracts entities & relations from text sources in batches using the LLMRouter."""

    async def extract_and_hydrate(self, documents: List[str], batch_size: int = 3) -> List[Dict[str, Any]]:
        extracted_triples = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            prompt = f"""
            Identify key B2B entities (Companies, People, Technologies, VentureCapitalists) and their relationships from the following text blocks.
            Format the output strictly as a JSON array of objects, containing "subject", "predicate", "object".
            Keep names standardized and clear.
            
            Text Blocks to analyze:
            {self._format_batch(batch)}
            
            Example output:
            [
              {{"subject": "RazorX Fintech", "predicate": "FUNDED_BY", "object": "Sequoia Capital"}},
              {{"subject": "Priya Sharma", "predicate": "WORKS_AT", "object": "RazorX Fintech"}}
            ]
            """
            
            try:
                response = await llm_service.acompletion(
                    model="nexus-fast",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                triples = json.loads(content)
                if isinstance(triples, dict) and "triples" in triples:
                    triples = triples["triples"]
                elif isinstance(triples, dict) and "relations" in triples:
                    triples = triples["relations"]
                elif isinstance(triples, dict):
                    # Check if the dict has a top-level key containing list
                    for val in triples.values():
                        if isinstance(val, list):
                            triples = val
                            break
                            
                if isinstance(triples, list):
                    for t in triples:
                        subj = t.get("subject")
                        pred = t.get("predicate")
                        obj = t.get("object")
                        if subj and pred and obj:
                            # Save to knowledge graph
                            # Deduce types based on predicates/context
                            s_type = self._deduce_type(subj, pred, is_subject=True)
                            o_type = self._deduce_type(obj, pred, is_subject=False)
                            
                            kg_manager.add_entity(subj, s_type)
                            kg_manager.add_entity(obj, o_type)
                            kg_manager.add_relation(subj, obj, pred)
                            
                            extracted_triples.append({
                                "subject": subj,
                                "relation": pred,
                                "object": obj
                            })
            except Exception as e:
                print(f"Error during batch entity extraction: {e}")
                
        return extracted_triples

    def _format_batch(self, batch: List[str]) -> str:
        formatted = ""
        for idx, doc in enumerate(batch):
            formatted += f"--- Document {idx+1} ---\n{doc}\n\n"
        return formatted

    def _deduce_type(self, entity: str, relation: str, is_subject: bool) -> str:
        entity_lower = entity.lower()
        relation_lower = relation.lower()
        
        # Check common patterns
        if "ops" in entity_lower or "manager" in entity_lower or "lead" in entity_lower or "vp" in entity_lower or "ceo" in entity_lower:
            return "Person"
        if "sharma" in entity_lower or "patel" in entity_lower or "jenkins" in entity_lower or "smith" in entity_lower:
            return "Person"
        if "capital" in entity_lower or "partners" in entity_lower or "ventures" in entity_lower:
            return "VentureCapital"
        if "aws" in entity_lower or "react" in entity_lower or "python" in entity_lower or "sheets" in entity_lower or "bamboo" in entity_lower:
            return "Technology"
        if is_subject and "works_at" in relation_lower:
            return "Person"
        if not is_subject and "works_at" in relation_lower:
            return "Company"
        if not is_subject and "funded_by" in relation_lower:
            return "VentureCapital"
            
        # Default
        return "Company" if is_subject else "Company"

batch_extractor = BatchEntityExtractor()
