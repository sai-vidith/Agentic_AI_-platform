import urllib.request
import json
import time

url = "http://127.0.0.1:8000/v2/webhooks/crunchbase"
data = {
    "source": "crunchbase",
    "event_type": "funding",
    "company": "Stripe",
    "data": {
        "amount_usd": 150000000,
        "round": "Series G"
    }
}
payload = json.dumps(data).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    print("Triggering webhook run for Stripe (Crunchbase trigger)...")
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("Webhook response:", json.dumps(res_data, indent=2))
        
        print("Waiting 15 seconds for agents to execute the DAG...")
        time.sleep(15)
        
        # Query qualified leads database to inspect results
        print("\nFetching leads database to verify Stripe record...")
        leads_req = urllib.request.Request("http://127.0.0.1:8000/v2/workflows/leads")
        with urllib.request.urlopen(leads_req) as leads_res:
            leads = json.loads(leads_res.read().decode("utf-8"))
            print(f"Total leads in event store: {len(leads)}")
            stripe_leads = [l for l in leads if "stripe" in l["company_name"].lower()]
            if stripe_leads:
                print("Found Stripe Lead Details:")
                print(json.dumps(stripe_leads[-1], indent=2)) # print latest stripe run
            else:
                print("Stripe lead has not finished processing or fell under the ICP threshold.")
except Exception as e:
    print("Error triggering workflow:", e)
