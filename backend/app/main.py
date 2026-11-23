import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response

from app.analyzer import analyze_with_groq, normalize_findings
from app.config import get_settings
from app.reports import (
    load_report,
    render_docx,
    render_markdown,
    safe_report_filename,
    save_report,
)
from app.repository import clone_repository, read_repository_context
from app.schemas import AnalysisReport, AnalyzeRequest

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="QualityCheckAgent API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "QualityCheckAgent"}


@app.get("/api/config")
def config():
    return {"groq_configured": bool(settings.groq_api_key), "model": settings.groq_model}


@app.post("/api/analyze", response_model=AnalysisReport)
async def analyze(request: AnalyzeRequest):
    report_id = uuid4().hex
    workspace = Path(settings.workspace_dir).resolve()
    repo_dir = workspace / "repositories" / report_id
    try:
        repo_name = clone_repository(
            str(request.repository_url),
            repo_dir,
            settings.clone_timeout_seconds,
        )
        context, included = read_repository_context(
            repo_dir,
            settings.max_files,
            settings.max_context_chars,
        )
        if not context.strip():
            raise RuntimeError("No supported text files were found in this repository.")
        result = await analyze_with_groq(settings, repo_name, context)
        omitted = result.get("unverified_findings", 0)
        report_limitations = [
            *[str(item)[:500] for item in result.get("limitations", [])[:20]],
            (
                f"Inspected {len(included)} selected text files; "
                "code was not executed."
            ),
        ]
        if omitted:
            report_limitations.append(
                f"Omitted {omitted} model-suggested finding(s) because they lacked "
                "a source evidence excerpt."
            )
        report = AnalysisReport(
            report_id=report_id,
            repository_url=str(request.repository_url),
            repository_name=repo_name,
            summary=str(result.get("summary", "Analysis completed."))[:4000],
            findings=normalize_findings(result.get("findings", [])),
            strengths=[str(item)[:500] for item in result.get("strengths", [])[:20]],
            limitations=report_limitations,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        save_report(report, workspace)
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Repository analysis failed for %s", request.repository_url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/reports/{report_id}", response_model=AnalysisReport)
def get_report(report_id: str):
    try:
        return load_report(report_id, Path(settings.workspace_dir).resolve())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc


@app.get("/api/reports/{report_id}/markdown", response_class=PlainTextResponse)
def download_report(report_id: str):
    try:
        report = load_report(report_id, Path(settings.workspace_dir).resolve())
        filename = f"{safe_report_filename(report.repository_name)}.md"
        return PlainTextResponse(
            render_markdown(report),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc


@app.get("/api/reports/{report_id}/docx")
def download_report_docx(report_id: str):
    try:
        report = load_report(report_id, Path(settings.workspace_dir).resolve())
        filename = f"{safe_report_filename(report.repository_name)}.docx"
        return Response(
            content=render_docx(report),
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc

from app.qpb_skill import inspect_skill, install_skill, status_dict

@app.get("/api/qpb/skill")
def qpb_skill_status():
    return {
        "version": "1.6.1",
        "pinned_commit": "ee60d579ecf43ee000039736e4bb1edbabe0201a",
        **status_dict(inspect_skill()),
    }


@app.post("/api/qpb/prepare")
def qpb_prepare(request: AnalyzeRequest):
    """Clone a target repository and install the pinned official QPB skill into it."""
    run_id = uuid4().hex
    workspace = Path(settings.workspace_dir).resolve()
    target = workspace / "repositories" / f"qpb-{run_id}"
    try:
        repository_name = clone_repository(
            str(request.repository_url), target, settings.clone_timeout_seconds
        )
        installed = install_skill(target)
        run_dir = workspace / "qpb_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "run_id": run_id,
            "repository_url": str(request.repository_url),
            "repository_name": repository_name,
            "repository_path": str(target),
            "skill": status_dict(installed),
            "skill_fingerprint": __import__(
                "app.qpb_skill", fromlist=["skill_fingerprint"]
            ).skill_fingerprint(target / ".github" / "skills" / "quality-playbook"),
            "status": "prepared",
            "phases": [
                {"number": n, "name": name, "status": "pending", "evidence": []}
                for n, name in enumerate(
                    ["Explore", "Generate", "Code Review", "Spec Audit",
                     "Reconciliation", "Verify"], start=1
                )
            ],
            "runtime_capabilities": {
                "phase_context_isolation": "not_yet_configured",
                "independent_auditor_providers": "not_yet_configured",
                "shell_execution": "not_enabled",
            },
            "message": (
                "Skill installed and validated. Phase execution has not started; "
                "the app will not mark any phase complete without its official gates."
            ),
        }
        (run_dir / "run.json").write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )
        return state
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("QPB skill preparation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/qpb/runs/{run_id}")
def get_qpb_run(run_id: str):
    run_file = Path(settings.workspace_dir).resolve() / "qpb_runs" / run_id / "run.json"
    try:
        return json.loads(run_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="QPB run not found.") from exc
