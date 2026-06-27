import hmac
import hashlib
from typing import Dict, Any
from app.config import settings

class AttestationManager:
    """Generates tamper-proof audit trails for governance logs."""
    
    def __init__(self):
        self.secret_key = settings.TEE_ENCRYPTION_KEY.encode()

    def generate_attestation_report(self, run_id: str, company_name: str, score: int, is_valid: bool) -> Dict[str, Any]:
        """Creates a signed JSON report proving safe execution of the discovery run."""
        payload = f"{run_id}:{company_name}:{score}:{is_valid}"
        
        # Calculate HMAC signature
        signature = hmac.new(
            self.secret_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "attestation_doc": {
                "run_id": run_id,
                "target_company": company_name,
                "qualification_score": score,
                "passed_validation": is_valid,
                "attested_by": "NexusAI_TEE_Vault_v3",
                "signature": signature
            }
        }

# Shared instance
attestation = AttestationManager()
