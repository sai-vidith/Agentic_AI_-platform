import urllib.request
import json
import time

url = "http://127.0.0.1:8000/v2/workflows/discover"
data = {
    "domain": "hr_saas",
    "limit": 2
}
payload = json.dumps(data).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    print("Triggering autonomous company discovery...")
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("\nDiscovery Webhook Response:")
        print(json.dumps(res_data, indent=2))
        
        print("\nWaiting 15 seconds for pipelines to trigger...")
        time.sleep(15)
        
        # Query qualified leads database to inspect results
        print("\nFetching leads database to verify discovered company entries...")
        leads_req = urllib.request.Request("http://127.0.0.1:8000/v2/workflows/leads")
        with urllib.request.urlopen(leads_req) as leads_res:
            leads = json.loads(leads_res.read().decode("utf-8"))
            print(f"Total leads: {len(leads)}")
            for l in leads[-3:]: # inspect last 3 runs
                print(f"- Lead ID: {l['id']}, Company: {l['company_name']}, ICP Score: {l['icp_score']}")
except Exception as e:
    print("Error triggering autonomous discovery:", e)
