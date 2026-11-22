import re
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from app.schemas import AnalysisReport


def safe_report_filename(repository_name: str) -> str:
    """Return a filesystem- and download-safe repository filename."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", repository_name.strip()).strip("._-")
    return (name or "repository")[:100]


def _severity_counts(report: AnalysisReport) -> dict[str, int]:
    severities = ("critical", "high", "medium", "low", "info")
    return {severity: sum(item.severity == severity for item in report.findings) for severity in severities}


def render_markdown(report: AnalysisReport) -> str:
    counts = _severity_counts(report)
    lines = [
        f"# Repository Quality Report: {report.repository_name}",
        "",
        "| Report detail | Value |",
        "|---|---|",
        f"| Repository | {report.repository_url} |",
        f"| Generated (UTC) | {report.generated_at} |",
        f"| Total findings | {len(report.findings)} |",
        "",
        "## Executive Summary",
        "",
        report.summary,
        "",
        "## Findings Overview",
        "",
        "| Severity | Count |",
        "|---|---:|",
        *[f"| {severity.title()} | {counts[severity]} |" for severity in counts],
        "",
        "## Detailed Findings",
        "",
    ]
    if not report.findings:
        lines.append(
            "No concrete findings were returned. This does not prove the repository is defect-free."
        )
        lines.append("")
    for index, item in enumerate(report.findings, 1):
        location = item.file + (f":{item.line}" if item.line else "")
        lines += [
            f"### {index}. [{item.severity.upper()}] {item.title}",
            "",
            f"**Location:** `{location}`",
            "",
            "**Evidence and impact**",
            "",
            item.description,
            "",
            "**Recommended action**",
            "",
            item.recommendation,
            "",
        ]
    lines += ["## Strengths", ""]
    lines += [f"- {item}" for item in report.strengths] or ["- No strengths were recorded."]
    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in report.limitations] or ["- No limitations were recorded."]
    lines += [
        "",
        "## Review Scope and Disclaimer",
        "",
        (
            "AI-assisted static review of selected repository text files only. "
            "No repository code or tests were executed, and official Quality Playbook "
            "verification gates were not run by this MVP. Findings are model-generated "
            "review leads and should be validated by an engineer."
        ),
        "",
    ]
    return "\n".join(lines)


def render_docx(report: AnalysisReport) -> bytes:
    """Build a formatted Word report using the same findings as the Markdown report."""
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10)
    styles["Title"].font.name = "Aptos Display"
    styles["Title"].font.color.rgb = RGBColor(20, 45, 68)
    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        styles[style_name].font.name = "Aptos Display"
        styles[style_name].font.color.rgb = RGBColor(20, 105, 92)

    title = document.add_heading("Repository Quality Report", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph(report.repository_name)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    metadata = document.add_table(rows=0, cols=2)
    metadata.style = "Light Shading Accent 1"
    for label, value in (
        ("Repository", report.repository_url),
        ("Generated (UTC)", report.generated_at),
        ("Total findings", str(len(report.findings))),
    ):
        cells = metadata.add_row().cells
        cells[0].text = label
        cells[1].text = value

    document.add_heading("Executive Summary", level=1)
    document.add_paragraph(report.summary)

    document.add_heading("Findings Overview", level=1)
    counts = _severity_counts(report)
    overview = document.add_table(rows=1, cols=2)
    overview.style = "Light Shading Accent 1"
    overview.rows[0].cells[0].text = "Severity"
    overview.rows[0].cells[1].text = "Count"
    for severity, count in counts.items():
        cells = overview.add_row().cells
        cells[0].text = severity.title()
        cells[1].text = str(count)

    document.add_heading("Detailed Findings", level=1)
    if not report.findings:
        document.add_paragraph(
            "No concrete findings were returned. This does not prove the repository is defect-free."
        )
    for index, finding in enumerate(report.findings, 1):
        document.add_heading(
            f"{index}. [{finding.severity.upper()}] {finding.title}", level=2
        )
        location = finding.file + (f":{finding.line}" if finding.line else "")
        paragraph = document.add_paragraph()
        paragraph.add_run("Location: ").bold = True
        paragraph.add_run(location)
        paragraph = document.add_paragraph()
        paragraph.add_run("Evidence and impact").bold = True
        document.add_paragraph(finding.description)
        paragraph = document.add_paragraph()
        paragraph.add_run("Recommended action").bold = True
        document.add_paragraph(finding.recommendation)

    document.add_heading("Strengths", level=1)
    for item in report.strengths or ["No strengths were recorded."]:
        document.add_paragraph(item, style="List Bullet")

    document.add_heading("Limitations", level=1)
    for item in report.limitations or ["No limitations were recorded."]:
        document.add_paragraph(item, style="List Bullet")

    document.add_heading("Review Scope and Disclaimer", level=1)
    document.add_paragraph(
        "AI-assisted static review of selected repository text files only. "
        "No repository code or tests were executed, and official Quality Playbook "
        "verification gates were not run by this MVP. Findings are model-generated "
        "review leads and should be validated by an engineer."
    )

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("QualityCheckAgent · AI-assisted static review")

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def save_report(report: AnalysisReport, workspace: Path) -> None:
    folder = workspace / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / f"{report.report_id}.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def load_report(report_id: str, workspace: Path) -> AnalysisReport:
    if not report_id.isalnum():
        raise FileNotFoundError(report_id)
    path = workspace / "reports" / f"{report_id}.json"
    if not path.exists():
        raise FileNotFoundError(report_id)
    return AnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
