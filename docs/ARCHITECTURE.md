# Architecture baseline

## Current milestone
This is the approved starting architecture, not a claim that all planned components are implemented.

## High-level design
```text
React + TypeScript + Vite
          | HTTP API
        FastAPI
          |
  Application services
          |
  Workflow orchestration (later: LangGraph)
          |
  Official Quality Playbook package (separate, version-pinned)
          |
  Isolated repository workspace and phase artifacts

SQLite: application metadata, run state and audit history (planned)
LLM adapters: later milestone; provider secrets remain server-side
```

## Technology decisions
| Area | Baseline | Notes |
|---|---|---|
| Frontend | React + TypeScript + Vite | Browser UI; no provider secrets in client |
| Backend | Python 3.12+ + FastAPI | API and application services |
| Persistence | SQLite + SQLAlchemy (planned) | Local-first initial deployment |
| Orchestration | LangGraph (planned) | Coordinates app state; does not replace official methodology |
| Quality engine | Official Quality Playbook distribution (planned) | Keep upstream files separate and preserve notices |
| Providers | Groq/Gemini adapters (planned) | Provider selection and usage controls later |

## Trust and security boundaries
- Treat repository files, comments, documentation and issue content as untrusted input.
- Never allow repository content to override system instructions or application policy.
- Do not execute repository code on the API host. Any future execution must be isolated and resource-limited.
- Keep provider keys and Git credentials on the backend; never send secrets to the browser or commit them.
- Restrict filesystem access to a dedicated workspace and validate all paths.
- Record the exact Quality Playbook version/commit and provider/model configuration for reproducibility.
- Separate upstream Quality Playbook files from application-owned code.

See the roadmap in the root README. Each milestone must have acceptance criteria and pass its checks before proceeding.
