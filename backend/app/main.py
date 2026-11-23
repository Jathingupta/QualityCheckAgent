import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response

from app.analyzer import analyze_with_groq, normalize_findings
from app.config import get_settings
from app.qpb_runner import (
    build_runner_command,
    execute_qpb_run,
    load_run,
    qpb_checkout,
    runner_availability,
    save_run,
)
from app.qpb_skill import inspect_skill, install_skill, skill_fingerprint, status_dict
from app.reports import (
    load_report,
    render_docx,
    render_markdown,
    safe_report_filename,
    save_report,
)
from app.repository import clone_repository, read_repository_context
from app.schemas import AnalysisReport, AnalyzeRequest, QpbStartRequest

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
            "skill_fingerprint": skill_fingerprint(
                target / ".github" / "skills" / "quality-playbook"
            ),
            "status": "prepared",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "phases": [
                {"number": n, "name": name, "status": "pending", "evidence": []}
                for n, name in enumerate(
                    ["Explore", "Generate", "Code Review", "Spec Audit",
                     "Reconciliation", "Verify"], start=1
                )
            ],
            "runtime_capabilities": {
                "official_mode_b_runner": True,
                "available_agent_clis": runner_availability(),
                "phase_context_isolation": "official QPB runner: separate phase subprocesses",
                "phase_4_council": "delegated to configured QPB Council roster",
                "phase_6_auditor": "fresh phase subprocess per QPB Mode B contract",
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
    try:
        return load_run(Path(settings.workspace_dir).resolve(), run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="QPB run not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/qpb/runtime")
def qpb_runtime_status():
    return {
        "official_runner_available": (qpb_checkout() / "bin" / "run_playbook.py").is_file(),
        "agent_clis": runner_availability(),
        "default_runner": "copilot",
    }


@app.post("/api/qpb/runs/{run_id}/start")
def start_qpb_run(
    run_id: str,
    request: QpbStartRequest,
    background_tasks: BackgroundTasks,
):
    workspace = Path(settings.workspace_dir).resolve()
    try:
        state = load_run(workspace, run_id)
        if state.get("status") == "running":
            raise HTTPException(status_code=409, detail="This QPB run is already running.")
        if state.get("status") == "completed":
            raise HTTPException(status_code=409, detail="This QPB run has already passed its gate.")
        if not request.acknowledge_execution_risk:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Acknowledge that the selected agent CLI can execute repository "
                    "commands and tests before starting QPB."
                ),
            )
        target = Path(state["repository_path"]).resolve()
        skill_status = inspect_skill(target / ".github" / "skills" / "quality-playbook")
        if not skill_status.installed:
            raise HTTPException(
                status_code=409,
                detail="The installed QPB skill is incomplete; reinstall it before execution.",
            )
        available = runner_availability()
        if not available.get(request.runner, False):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"The {request.runner} CLI was not detected on the backend PATH. "
                    "Install it and authenticate in the same OS account that runs the backend."
                ),
            )
        phase_states = state.get("phases", [])
        pending_numbers = [
            int(phase["number"])
            for phase in phase_states
            if phase.get("status") != "completed"
        ]
        first_phase = min(pending_numbers) if pending_numbers else 6
        phases_to_run = list(range(first_phase, 7))
        build_runner_command(
            target, request.runner, request.model, request.council_roster,
            phases_to_run, include_iterations=request.include_iterations,
        )
        state.update({
            "status": "running",
            "runner": request.runner,
            "model": request.model,
            "council_roster": request.council_roster,
            "include_iterations": request.include_iterations,
            "requested_phases": phases_to_run,
            "message": (
                f"Official QPB Mode B execution queued from Phase {first_phase}."
            ),
        })
        save_run(workspace, run_id, state)
        background_tasks.add_task(
            execute_qpb_run,
            workspace,
            run_id,
            request.runner,
            request.model,
            request.council_roster,
            phases_to_run,
            request.include_iterations,
        )
        return state
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="QPB run not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not start QPB run %s", run_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/qpb/runs/{run_id}/download")
def download_qpb_artifacts(run_id: str):
    workspace = Path(settings.workspace_dir).resolve()
    try:
        state = load_run(workspace, run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="QPB run not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    target = Path(state["repository_path"]).resolve()
    expected_root = (workspace / "repositories").resolve()
    if expected_root not in target.parents:
        raise HTTPException(status_code=400, detail="QPB target is outside the workspace.")

    quality_dir = target / "quality"
    files = [
        path for path in quality_dir.rglob("*")
        if path.is_file() and not path.is_symlink()
    ] if quality_dir.is_dir() else []
    agents_file = target / "AGENTS.md"
    if agents_file.is_file():
        files.append(agents_file)
    if not files:
        raise HTTPException(status_code=404, detail="No QPB artifacts have been generated yet.")

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(target).as_posix())
    archive_buffer.seek(0)
    repository_name = re.sub(
        r"[^A-Za-z0-9._-]+", "-", state.get("repository_name", "repository")
    ).strip("-") or "repository"
    filename = f"{repository_name}-quality-playbook-{run_id[:8]}.zip"
    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/qpb/runs")
def list_qpb_runs():
    run_root = Path(settings.workspace_dir).resolve() / "qpb_runs"
    if not run_root.is_dir():
        return {"runs": []}
    runs = []
    for run_file in run_root.glob("*/run.json"):
        try:
            runs.append(json.loads(run_file.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            logger.warning("Skipping unreadable QPB run record: %s", run_file)
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"runs": runs}
