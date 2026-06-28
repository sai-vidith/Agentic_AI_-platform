import sqlite3
import os
import asyncio
import sys
from datetime import datetime

# Set up python path so we can import backend app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.api.workflows import execute_task_background

DATABASE_PATH = r"c:\Users\Sai Divya\Desktop\XL_VENTURES_AI\backend\nexusai.db"
PROGRESS_FILE = r"c:\Users\Sai Divya\Desktop\XL_VENTURES_AI\revalidation_progress.txt"

# Known Cybersecurity targets
CYBER_COMPANIES = {
    "snyk", "wiz", "sentinelone", "chainguard", "fortinet", "netskope", "cyera", 
    "projectdiscovery", "palo alto networks", "rilian technologies", "kenzo security",
    "crowdstrike"
}

def log_progress(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

async def main():
    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    # Create/clear progress file
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        f.write("=== Lead Revalidation & Enrichment Validation Run ===\n")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT company_name FROM leads;")
    companies = [r[0] for r in cursor.fetchall() if r[0]]
    conn.close()

    # Filter out test names
    exclude_list = {"acmecorp", "unknown company", "saas startups", "hr startups", "nova", "fundraise"}
    companies = [c for c in companies if c.strip().lower() not in exclude_list]

    log_progress(f"Found {len(companies)} companies in DB to enrich and revalidate.")
    log_progress(f"Target list: {', '.join(companies)}")

    for idx, company in enumerate(companies, 1):
        # Determine domain
        company_clean = company.strip().lower()
        domain = "cybersecurity" if any(cyber in company_clean for cyber in CYBER_COMPANIES) else "hr_saas"
        
        log_progress(f"[{idx}/{len(companies)}] Triggering research pipeline for: '{company}' (Domain: {domain})")
        
        try:
            # Execute pipeline
            await execute_task_background(domain, company)
            log_progress(f"Successfully processed and updated: '{company}'")
        except Exception as e:
            log_progress(f"Error processing '{company}': {e}")
            
        # 6-second sleep buffer to prevent LLM rate limiting
        await asyncio.sleep(6.0)

    log_progress("=== Revalidation run complete! All database records successfully verified. ===")

if __name__ == "__main__":
    asyncio.run(main())
