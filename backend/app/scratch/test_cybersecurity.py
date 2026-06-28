import urllib.request
import json
import time

url = "http://127.0.0.1:8000/v2/workflows/run"
data = {
    "domain": "cybersecurity",
    "company_name": "Snyk"
}
payload = json.dumps(data).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    print("Triggering cybersecurity workflow for Snyk...")
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("Response:", json.dumps(res_data, indent=2))
        
    print("Waiting 15 seconds for pipeline execution...")
    time.sleep(15)
    
    # Query leads database to verify Snyk record
    leads_req = urllib.request.Request("http://127.0.0.1:8000/v2/workflows/leads")
    with urllib.request.urlopen(leads_req) as leads_res:
        leads = json.loads(leads_res.read().decode("utf-8"))
        snyk_leads = [l for l in leads if "snyk" in l["company_name"].lower()]
        print(f"Total leads in event store: {len(leads)}")
        print(f"Snyk leads found: {len(snyk_leads)}")
        if snyk_leads:
            print("Snyk Lead details:")
            print(json.dumps(snyk_leads[-1], indent=2))
            
except Exception as e:
    print("Error:", e)
