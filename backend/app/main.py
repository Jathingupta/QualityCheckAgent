from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.analyzer import analyze_with_groq, normalize_findings
from app.config import get_settings
from app.repository import clone_repository, read_repository_context
from app.reports import load_report, render_markdown, save_report
from app.schemas import AnalysisReport, AnalyzeRequest

settings = get_settings()
app = FastAPI(title="QualityCheckAgent API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])


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
        repo_name = clone_repository(str(request.repository_url), repo_dir, settings.clone_timeout_seconds)
        context, included = read_repository_context(repo_dir, settings.max_files, settings.max_context_chars)
        if not context.strip():
            raise RuntimeError("No supported text files were found in this repository.")
        result = await analyze_with_groq(settings, repo_name, context)
        report = AnalysisReport(report_id=report_id, repository_url=str(request.repository_url), repository_name=repo_name,
            summary=str(result.get("summary", "Analysis completed."))[:4000], findings=normalize_findings(result.get("findings", [])),
            strengths=[str(x)[:500] for x in result.get("strengths", [])[:20]],
            limitations=[*[str(x)[:500] for x in result.get("limitations", [])[:20]], f"Inspected {len(included)} selected text files; code was not executed."],
            generated_at=datetime.now(timezone.utc).isoformat())
        save_report(report, workspace)
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
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
        return PlainTextResponse(render_markdown(report), headers={"Content-Disposition": f'attachment; filename="quality-report-{report_id}.md"'})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc
