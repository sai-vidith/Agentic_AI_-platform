import re
from typing import List

class PIIRedactor:
    """Detects and redacts PII fields such as email and phone numbers."""
    
    def __init__(self):
        self.email_pattern = re.compile(r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
        self.phone_pattern = re.compile(r'(\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}')

    def redact_text(self, text: str) -> str:
        if not text:
            return ""
            
        # Redact emails: keep first 2 letters, then mask, then domain
        def redact_email_match(match):
            user = match.group(1)
            domain = match.group(2)
            if len(user) > 2:
                masked_user = user[:2] + "████"
            else:
                masked_user = "████"
            return f"{masked_user}@{domain}"

        # Redact phone numbers: mask digits, keep structure
        def redact_phone_match(match):
            phone = match.group(0)
            # Mask all numbers except structure details
            masked = re.sub(r'\d', '█', phone)
            # Keep country code if it started with +
            if phone.startswith('+'):
                masked = '+' + masked[1:]
            return masked

        text = self.email_pattern.sub(redact_email_match, text)
        text = self.phone_pattern.sub(redact_phone_match, text)
        return text

# Shared instance
pii_redactor = PIIRedactor()
