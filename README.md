# QualityCheckAgent

A repository quality-engineering application built around the official Quality Playbook methodology.

> **Project status:** Foundation stage. The official Quality Playbook engine has not yet been added. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Planned capabilities
- Ingest and inspect a Git repository.
- Run the six official Quality Playbook phases: Explore, Generate, Review, Audit, Reconcile, and Verify.
- Preserve phase artifacts, evidence, and verification results.
- Support configurable LLM providers through a backend adapter layer.
- Track runs, costs, and status in a local database.
- Provide a web dashboard for starting and inspecting audits.

The application will orchestrate the official methodology; it will not silently replace or simplify it.

## Technology
- Backend: Python 3.12+, FastAPI; SQLite persistence will be introduced in the persistence milestone.
- Frontend: React, TypeScript, Vite.
- Workflow orchestration: LangGraph (later milestone).
- Quality engine: official Quality Playbook distribution, kept separately and version-pinned.

## Roadmap
1. Foundation, configuration, dependency and licence inventory.
2. Official Quality Playbook discovery, pinning and installation.
3. Repository ingestion and safe workspace handling.
4. LLM provider abstraction and cost controls.
5. LangGraph orchestration and run state.
6. Integration of the six official phases without changing their methodology.
7. Iteration strategies and additional defect detection.
8. Persistence, checkpointing and recovery.
9. API and dashboard integration.
10. End-to-end, security and reproducibility verification.

Each milestone must pass its checks before the next begins.

## Quick start (Windows PowerShell)
Requirements: Python 3.12+, Node.js 20+, npm, and Git.

### Backend
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --app-dir backend
```
Open http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs.

Run checks:
```powershell
pytest
ruff check .
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

## Secrets and confidential data
Copy `.env.example` to `.env` when local configuration is needed. Never commit API keys, tokens, credentials, private repository contents, or company data. No LLM API key is required for this foundation milestone. Do not connect this prototype to company repositories until security review is complete.

## Licence and third-party components
The application's own licensing position has not yet been selected. The official Quality Playbook is separately distributed under Apache License 2.0; preserve its licence, copyright notices, and applicable NOTICE file when it is added. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
