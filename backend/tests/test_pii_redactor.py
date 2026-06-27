"""Unit tests for PII Redactor — validates email and phone number masking."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.governance.pii_redactor import PIIRedactor
import pytest


class TestPIIRedactor:
    """Tests for the PII Redactor regex-based masking."""
    
    def setup_method(self):
        self.redactor = PIIRedactor()
    
    def test_email_redaction_preserves_first_two_chars(self):
        text = "Contact john.doe@example.com for details"
        result = self.redactor.redact_text(text)
        assert "jo████@example.com" in result
        assert "john.doe@example.com" not in result
    
    def test_short_email_fully_masked(self):
        text = "Email: ab@test.org"
        result = self.redactor.redact_text(text)
        assert "@test.org" in result
        assert "ab@test.org" not in result
    
    def test_phone_redaction(self):
        text = "Call +1-555-123-4567 for support"
        result = self.redactor.redact_text(text)
        # All digits should be masked
        assert "555" not in result
        assert "123" not in result
        assert "4567" not in result
        # Structure should be preserved
        assert "+" in result
    
    def test_multiple_pii_in_text(self):
        text = "Email: priya@razorx.in, Phone: +91-9876543210"
        result = self.redactor.redact_text(text)
        assert "priya@razorx.in" not in result
        assert "9876543210" not in result
        assert "@razorx.in" in result  # Domain preserved
    
    def test_no_pii_unchanged(self):
        text = "This is a normal business description with no personal data."
        result = self.redactor.redact_text(text)
        assert result == text
    
    def test_empty_input(self):
        assert self.redactor.redact_text("") == ""
        assert self.redactor.redact_text(None) == ""
    
    def test_email_domain_preserved(self):
        text = "Contact: alice.smith@acmecorp.com"
        result = self.redactor.redact_text(text)
        assert "acmecorp.com" in result
        assert "alice.smith" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
