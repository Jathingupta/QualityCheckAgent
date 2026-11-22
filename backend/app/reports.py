from pathlib import Path

from app.schemas import AnalysisReport


def render_markdown(report: AnalysisReport) -> str:
    lines = [
        f"# Quality Analysis: {report.repository_name}",
        "",
        f"Repository: {report.repository_url}",
        f"Generated: {report.generated_at}",
        "",
        "## Summary",
        "",
        report.summary,
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append(
            "No concrete findings were returned. "
            "This does not prove the repository is defect-free."
        )
    for index, item in enumerate(report.findings, 1):
        location = item.file + (f":{item.line}" if item.line else "")
        lines += [
            f"### {index}. [{item.severity.upper()}] {item.title}",
            "",
            f"Location: `{location}`",
            "",
            item.description,
            "",
            f"Recommendation: {item.recommendation}",
            "",
        ]
    lines += ["## Strengths", ""] + [f"- {item}" for item in report.strengths]
    lines += ["", "## Limitations", ""] + [
        f"- {item}" for item in report.limitations
    ]
    lines += [
        "",
        (
            "> AI-assisted static review only. No repository code, tests "
            "or official QPB verification gates were executed."
        ),
        "",
    ]
    return "\n".join(lines)


def save_report(report: AnalysisReport, workspace: Path) -> None:
    folder = workspace / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / f"{report.report_id}.json"
    markdown_path = folder / f"{report.report_id}.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def load_report(report_id: str, workspace: Path) -> AnalysisReport:
    if not report_id.isalnum():
        raise FileNotFoundError(report_id)
    path = workspace / "reports" / f"{report_id}.json"
    if not path.exists():
        raise FileNotFoundError(report_id)
    return AnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
