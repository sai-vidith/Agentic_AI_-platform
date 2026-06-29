from fastapi import FastAPI, Body
from typing import Dict, Any

app = FastAPI()

@app.get("/status")
async def status():
    return {"running": True}

@app.post("/command")
async def command(payload: Dict[str, Any] = Body(...)):
    action = payload.get("action")
    args = payload.get("args", {})
    session = payload.get("session")
    
    print(f"[MockWebBridge] Received command: action={action}, args={args}, session={session}")
    
    if action == "evaluate":
        code = args.get("code", "")
        if "document.title" in code:
            return {"value": "Mock Kimi Audited Page Title"}
        elif "querySelectorAll" in code or "map" in code:
            return {"value": [
                "https://www.linkedin.com/company/vanta",
                "https://www.linkedin.com/in/nathan-hunstad-2625b73",
                "https://www.linkedin.com/in/sarah-jenkins-ciso"
            ]}
        else:
            return {"value": "Mock Kimi WebBridge Audit Result: Verified active recruitment for security roles, headcount growth +30% in 2025, and Series B funding injection."}
            
    return {"status": "success", "value": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=10086)
