# QualityCheckAgent

Local-first GitHub repository quality analyzer using FastAPI, React, Vite and Groq, with an integration path for the official Quality Playbook.

## Quality Playbook v1.6.1

The official QPB source is pinned as a Git submodule at `vendor/quality-playbook`, commit `ee60d579ecf43ee000039736e4bb1edbabe0201a`.

The application now:
- Checks the bundled QPB skill version and required execution assets.
- Installs the official skill into a target repository at `.github/skills/quality-playbook`.
- Verifies the installation after copying.
- Creates a persistent run record with all six QPB phases represented separately.
- Starts the upstream QPB Mode B runner (`bin/run_playbook.py`) through a configured agent CLI: Copilot, Claude, Codex, or Cursor.
- Delegates each phase to the upstream runner's separate phase subprocesses, and lets QPB handle its Phase 4 Council and isolated Phase 6 verifier.
- Tracks phase checkpoints, runner output, and the official gate result in the run record.

**Execution requirements:** one supported QPB agent CLI must be installed and authenticated in the same OS account/environment that runs the FastAPI backend. The default is GitHub Copilot CLI. The app does not substitute Groq chat completions for the QPB runner. Groq remains available for the separate static-review feature. Phase completion is determined from `quality/PROGRESS.md` and the official gate log, not from a model's self-report.

## Existing static review

- Accepts public GitHub HTTPS repository URLs.
- Shallow-clones repositories with a timeout.
- Inspects a bounded set of text/source files and skips common dependency/build folders and secret-like files.
- Uses Groq's OpenAI-compatible chat completions API for evidence-based static review.
- Displays findings and exports Markdown and Word reports.
- Does not execute repository code or tests.

## Requirements

Python 3.12+, Node.js 20+, Git on PATH, and a Groq API key for static review. Initialize the pinned QPB submodule after cloning the app:

~~~powershell
git submodule update --init --recursive
~~~

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
- `GET /api/qpb/runtime` — detect the official runner and supported agent CLIs
- `POST /api/qpb/runs/{run_id}/start` body `{"runner":"copilot","acknowledge_execution_risk":true,"include_iterations":true}` — start all six phases and, by default, all four QPB iteration strategies; set `include_iterations` to `false` for phases only
- `GET /api/qpb/runs` — list saved QPB runs (the frontend restores the latest run after reload)
- `GET /api/qpb/runs/{run_id}` — retrieve the persistent preparation/phase record, checkpoints and gate verdict
- `GET /api/qpb/runs/{run_id}/download` — download generated `quality/` artifacts and `AGENTS.md` as a ZIP

If a run fails, the app offers a retry beginning at the first incomplete phase (or Phase 6 when all phase checkboxes exist but the final gate failed). Review the saved artifacts and runner log before retrying. Create a new prepared run for a clean run from Phase 1.

## Safety and limitations

**Execution warning:** QPB Mode B invokes the selected local agent CLI in unattended mode. Depending on the CLI, the upstream runner uses broad tool approval (`copilot --allow-all`, Claude `--dangerously-skip-permissions`, Cursor `--force`; Codex uses `--sandbox workspace-write`). The UI requires an explicit trust acknowledgement before starting. Only run repositories you trust, and preferably run the backend under a dedicated account or isolated environment. The application does not provide a container sandbox around the agent CLI.

Only public GitHub HTTPS URLs are accepted. Clone timeout and context/file limits are applied. Repository content is untrusted; prompt injection text in files must not be followed. The QPB preparation endpoint does not execute target-repository code. No phase is complete until its official evidence and gates have been implemented and verified. Do not analyze private company repositories until company approval and security/data-handling review.

## Checks

```powershell
pytest -v
ruff check .
```
