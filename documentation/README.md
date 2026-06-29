# NexusAI — Cognitive Orchestrator Documentation

Welcome to the documentation for **NexusAI** (Cognitive Orchestrator), a production-grade Agentic AI platform built for automated B2B customer discovery, ICP verification, and prospect intelligence.

---

## 1. Team Details

*   **Sai vidith** — *Team Lead*
*   **Padala Srishanth** — *Technical Lead*
*   **Rohith** — *Product Manager*

---

## 2. Project Overview

NexusAI solves the core challenge of B2B sales intelligence: **trust and accuracy**. Standard B2B databases suffer from high decay rates, stale contact listings, and false positive matches. 

NexusAI automates this research using a multi-agent framework that does not just collect data but dynamically debates and self-heals its way to gold-tier prospect profiles.

### Core Differentiators:
1.  **Topological DAG Execution**: Orchestrates 8 specialized agents using a Directed Acyclic Graph (DAG) with dynamic pruning.
2.  **Adversarial Debate Protocol**: Uses a Advocate-vs-Shadow agent debate protocol to stress-test target leads, dropping false positives by over 60%.
3.  **Self-Healing Resilience**: Integrates a Multi-LLM fallback chain (Groq $\rightarrow$ Cerebras $\rightarrow$ Gemini) that routes around rate-limits and network faults.
4.  **Secure Cryptographic Vault**: Simulates an enterprise-grade TEE encrypted lock system, keeping prospect communication records encrypted at rest using AES-256 keys.
5.  **Configurable Domain Engine**: Allows non-technical users to swap target domains (e.g. HR SaaS to Cybersecurity) instantly by editing YAML configuration matrices.

---

## 3. GitHub Repository Link

The official code repository for NexusAI is hosted at:
👉 **[GitHub: sai-vidith/Agentic_AI_-platform](https://github.com/sai-vidith/Agentic_AI_-platform)**

---

## 4. Setup and Installation Instructions

Follow these steps to run the NexusAI platform locally.

### Prerequisites
*   **Python**: Version 3.10 or higher (Python 3.14 used in development)
*   **Node.js**: Version 18.0 or higher (npm included)

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/sai-vidith/Agentic_AI_-platform.git
cd Agentic_AI_-platform
```

---

### Step 2: Configure Environment Variables
Copy `.env.example` in the root directory to `.env` and configure your API keys:
```bash
cp .env.example .env
```

Ensure your `.env` contains the required keys:
*   `GROQ_API_KEY`: Groq console API key (primary model pool)
*   `CEREBRAS_API_KEY`: Cerebras console API key (secondary fallback)
*   `SERPER_API_KEY`: Google Serper search API key
*   `NEWS_API_KEY`: NewsAPI client key for signal tracking
*   `FIRECRAWL_API_KEY`: Firecrawl API key for markdown scraping

---

### Step 3: Set Up and Start the Backend Server
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI server via Uvicorn:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   *The API backend will start running at `http://127.0.0.1:8000`.*

---

### Step 4: Set Up and Start the Frontend Dev Server
1. Open a new terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   *The client interface will start running at `http://localhost:3000`.*

---

## 5. Additional Notes

### Verification Testing
To run a standalone backend validation of the agent orchestration engine without starting the web server, you can execute our DAG suite directly from the `backend` directory:
```bash
python test_dag.py
```
This runs a simulated qualification trace for the company `RazorX Fintech` across all 8 agents and saves the resulting entities in `nexusai.db`.

### Observability Audit Logs
All trace spans, cost footprint metrics, and attestation validity indicators can be monitored in real-time inside the **Observability & Governance** dashboard pane.
