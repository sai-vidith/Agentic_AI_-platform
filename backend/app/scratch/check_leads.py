import urllib.request
import json

leads_req = urllib.request.Request("http://127.0.0.1:8000/v2/workflows/leads")
try:
    with urllib.request.urlopen(leads_req) as response:
        leads = json.loads(response.read().decode("utf-8"))
        print(f"Total leads: {len(leads)}")
        
        # Sort leads by created_at (descending)
        leads_sorted = sorted(leads, key=lambda l: l.get("created_at", ""), reverse=True)
        
        print("\nLatest 5 Leads in Database:")
        for idx, l in enumerate(leads_sorted[:5]):
            print(f"{idx+1}. Lead ID: {l.get('id')}, Company: {l.get('company_name')}, ICP Score: {l.get('icp_score')}, Status: {l.get('status')}, Created At: {l.get('created_at')}")
except Exception as e:
    print("Error fetching leads:", e)
