# NexusAI Installation & Setup Guide

This document provides step-by-step instructions to configure, run, and test the **NexusAI** Prospect Intelligence Platform in development and production environments.

---

## 1. Prerequisites

Before setting up the project, ensure you have the following software installed:

*   **Python**: Version `3.11` or higher.
*   **Node.js**: Version `18` or higher (includes `npm`).
*   **Docker & Docker Compose**: Required for containerized execution (PostgreSQL, Redis, ChromaDB).
*   **API Keys**:
    *   **Groq API Key**: Primary low-latency LLM engine.
    *   **Gemini API Key**: Fallback/secondary LLM engine.
    *   **NewsAPI Key**: (Optional) News monitoring provider.

---

## 2. Configuration (`.env`)

1. Copy the environment template in the project root:
   ```bash
   cp .env.example .env
   ```
2. Open the newly created `.env` file and populate your respective API keys.
3. If you want to test or run the platform in mock mode (without live LLM/API credits), ensure the mock fallback is enabled:
   ```env
   ALLOW_MOCK_FALLBACK=true
   ```

---

## 3. Local Installation & Development

To run the frontend and backend servers locally for active debugging and styling changes:

### A. Backend Setup
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies in editable/development mode:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server with hot-reloading:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The backend API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### B. Frontend Setup
1. Open a new terminal session and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   The web application UI will be accessible at [http://localhost:5173](http://localhost:5173).

---

## 4. Containerized Execution (Docker Compose)

The easiest way to run the entire stack (FastAPI Backend, React Frontend, PostgreSQL Relational Database, Redis Cache, ChromaDB Vector Index) in production mode:

1. In the root workspace directory, build and run the Docker containers:
   ```bash
   docker compose up --build
   ```
2. Access the services:
   *   **Frontend Web App**: [http://localhost:3000](http://localhost:3000)
   *   **Backend REST Server**: [http://localhost:8000](http://localhost:8000)
   *   **OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. Testing the Pipeline & Quality Assurance

To verify execution flows and check the in-memory graph operations:

### A. Run Automated Unit Tests
Activate your virtual environment and run the Pytest suite in the `backend` directory:
```bash
cd backend
python -m pytest tests/
```
This runs the full test suite verifying:
*   Topological DAG resolution.
*   Adversarial Shadow Agent debate logic.
*   PII presidio redaction validation.
*   Relational GraphRAG multi-hop traversal query algorithms.

### B. Run End-to-End Test Runs
To run a test lead qualification pipeline run directly from the CLI:
```bash
cd backend
python test_dag.py
```
This will compile a dynamic DAG for `"RazorX Fintech"`, execute the agents, trigger the background search audit, and write the verified results into `nexusai.db`.

---

## 6. Swapping Business Domains (YAML Configuration)

NexusAI compiles its rules dynamically. To switch target business profiles (e.g., from HR SaaS to Cybersecurity):
1. Navigate to `backend/app/business_config/`.
2. Define the new ICP criteria, personas, and trigger monitoring rules in their respective sub-directories:
   *   `icp_profiles/<domain>_icp.yaml`
   *   `personas/<domain>_personas.yaml`
   *   `triggers/<domain>_triggers.yaml`
3. Restart your uvicorn/Docker servers. The planner agent will automatically load the new YAML configs on the next workflow request.
