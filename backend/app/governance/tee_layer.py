from cryptography.fernet import Fernet
from app.config import settings

class TEEVault:
    """Simulates a Trusted Execution Environment (TEE) encrypted memory vault."""
    
    def __init__(self):
        # Fernet key needs to be 32 URL-safe base64-encoded bytes
        # If it is loaded directly from settings, ensure it's valid
        key = settings.TEE_ENCRYPTION_KEY.encode()
        try:
            self.cipher = Fernet(key)
        except Exception:
            # Re-generate a valid key for safety
            fallback_key = Fernet.generate_key()
            self.cipher = Fernet(fallback_key)

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        return self.cipher.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text:
            return ""
        try:
            return self.cipher.decrypt(cipher_text.encode()).decode()
        except Exception as e:
            return f"[Decryption Error: {str(e)}]"

# Shared instance
tee_vault = TEEVault()
