# QualityCheckAgent MVP

Local-first GitHub repository analyzer using FastAPI, React, Vite and Groq.

## Features
- Accepts public GitHub HTTPS repository URLs.
- Shallow-clones repositories with a timeout.
- Inspects a bounded set of text/source files; skips common dependency/build folders and secret-like files.
- Uses Groq's OpenAI-compatible chat completions API for evidence-based static review.
- Displays findings, severity, file references, recommendations and a Markdown report download.
- Does not execute repository code or tests.

## QPB integration status — read carefully
The official Quality Playbook v1.6.1 remains a separately pinned Git submodule in the existing project at `vendor/quality-playbook`. This MVP is a Groq-powered static repository review; it does **not** claim to execute the full official QPB workflow, independent phase contexts, official scripts or verification gates. Full QPB execution needs an agent runtime adapter. The UI and repository-ingestion service are structured so that adapter can be added separately.

## Requirements
Python 3.12+, Node.js 20+, Git on PATH, Groq API key.

## Windows setup
From project root:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```
Edit `.env` and set `GROQ_API_KEY`. Default model: `openai/gpt-oss-20b`.

Terminal 1 (project root):
```powershell
uvicorn app.main:app --reload --app-dir backend
```
Terminal 2:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## API
- `GET /health`
- `GET /api/config`
- `POST /api/analyze` body `{"repository_url":"https://github.com/owner/repo"}`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/markdown`

## Safety and limitations
Only public GitHub HTTPS URLs are accepted. Clone timeout and context/file limits are applied. Repository content is untrusted; prompt injection text in files must not be followed. No repository code is executed. Do not analyze private company repositories until company approval and security/data-handling review. Model output is not proof that a defect exists; verify findings manually.

## Checks
```powershell
pytest -v
ruff check .
```
