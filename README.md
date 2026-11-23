# QualityCheckAgent

Local-first GitHub repository quality analyzer using FastAPI, React, Vite and Groq, with an integration path for the official Quality Playbook.

## Quality Playbook v1.6.1

The official QPB source is pinned as a Git submodule at `vendor/quality-playbook`, commit `ee60d579ecf43ee000039736e4bb1edbabe0201a`.

The application now:
- Checks the bundled QPB skill version and required execution assets.
- Installs the official skill into a target repository at `.github/skills/quality-playbook`.
- Verifies the installation after copying.
- Creates a persistent run record with all six QPB phases represented separately.
- Exposes skill status, preparation, and run-state APIs.

**Current milestone:** skill installation and run preparation. The UI intentionally displays all six phases as pending. It does not claim that the phases have executed. The next milestone is wiring the phase execution runtime, independent auditor dispatch, safe tool execution, official gates, and resumable phase checkpoints. In particular, Phase 4's Council of Three and Phase 6's fresh-context auditor must not be simulated by one model response.

## Existing static review

- Accepts public GitHub HTTPS repository URLs.
- Shallow-clones repositories with a timeout.
- Inspects a bounded set of text/source files and skips common dependency/build folders and secret-like files.
- Uses Groq's OpenAI-compatible chat completions API for evidence-based static review.
- Displays findings and exports Markdown and Word reports.
- Does not execute repository code or tests.

## Requirements

Python 3.12+, Node.js 20+, Git on PATH, and a Groq API key for static review. After cloning the application, initialize its pinned QPB submodule with `git submodule update --init --recursive`.

## Windows setup

From project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env`. Default model: `openai/gpt-oss-20b`.

Terminal 1:

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
- `GET /api/reports/{report_id}/docx`
- `GET /api/qpb/skill` — inspect the pinned QPB skill bundle
- `POST /api/qpb/prepare` — clone a target and install the QPB skill
- `GET /api/qpb/runs/{run_id}` — retrieve the persistent preparation/phase record

## Safety and limitations

Only public GitHub HTTPS URLs are accepted. Clone timeout and context/file limits are applied. Repository content is untrusted; prompt injection text in files must not be followed. The QPB preparation endpoint does not execute target-repository code. No phase is complete until its official evidence and gates have been implemented and verified. Do not analyze private company repositories until company approval and security/data-handling review.

## Checks

```powershell
pytest -v
ruff check .
```
