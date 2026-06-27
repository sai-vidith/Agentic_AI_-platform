import asyncio

async def search_linkedin(name: str, company: str) -> str:
    """Searches LinkedIn to find the email and phone number of a person at a company."""
    await asyncio.sleep(0.5) # Simulate network delay
    
    if "priya" in name.lower() or "razorx" in company.lower():
        return '{"email": "priya.sharma@razorx.com", "phone": "+1-555-0199", "linkedin": "linkedin.com/in/priyasharma"}'
    
    return '{"email": "unknown", "phone": "unknown", "linkedin": "unknown"}'
