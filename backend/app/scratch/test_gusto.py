import urllib.request
import json
import time

# 1. Trigger Gusto workflow run (First run)
url = "http://127.0.0.1:8000/v2/workflows/run"
data = {
    "domain": "hr_saas",
    "company_name": "Gusto"
}
payload = json.dumps(data).encode("utf-8")

req1 = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    print("=== FIRST RUN FOR GUSTO ===")
    print("Triggering workflow for Gusto...")
    with urllib.request.urlopen(req1) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("Response:", json.dumps(res_data, indent=2))
        
    print("Waiting 15 seconds for first run topological execution...")
    time.sleep(15)
    
    # Query leads database to verify first Gusto record
    leads_req = urllib.request.Request("http://127.0.0.1:8000/v2/workflows/leads")
    with urllib.request.urlopen(leads_req) as leads_res:
        leads_before = json.loads(leads_res.read().decode("utf-8"))
        gusto_before = [l for l in leads_before if "gusto" in l["company_name"].lower()]
        print(f"\nTotal leads before second run: {len(leads_before)}")
        print(f"Total Gusto leads before second run: {len(gusto_before)}")
        if gusto_before:
            first_gusto = gusto_before[-1]
            print("First Gusto lead ID:", first_gusto["id"])
            print("Website:", first_gusto["company_details"].get("website"))
            print("LinkedIn:", first_gusto["company_details"].get("linkedin"))
            print("Contacts Count:", len(first_gusto.get("contacts", [])))
            print("Sources:", json.dumps(first_gusto.get("sources", []), indent=2))
            
    # 2. Trigger Gusto workflow run (Second run - Duplicate)
    print("\n=== SECOND RUN FOR GUSTO (DUPLICATE) ===")
    print("Triggering workflow for Gusto again...")
    with urllib.request.urlopen(req1) as response:
        res_data2 = json.loads(response.read().decode("utf-8"))
        print("Response:", json.dumps(res_data2, indent=2))
        
    print("Waiting 15 seconds for second run topological execution...")
    time.sleep(15)
    
    # Query leads database to check if a new Gusto lead was added, or if it was silently merged
    with urllib.request.urlopen(leads_req) as leads_res:
        leads_after = json.loads(leads_res.read().decode("utf-8"))
        gusto_after = [l for l in leads_after if "gusto" in l["company_name"].lower()]
        print(f"\nTotal leads after second run: {len(leads_after)}")
        print(f"Total Gusto leads after second run: {len(gusto_after)}")
        if gusto_after:
            latest_gusto = gusto_after[-1]
            print("Latest Gusto lead ID:", latest_gusto["id"])
            print("Contacts Count:", len(latest_gusto.get("contacts", [])))
            print("Sources Count:", len(latest_gusto.get("sources", [])))
            
except Exception as e:
    print("Error:", e)
