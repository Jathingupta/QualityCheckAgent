from io import BytesIO

from app.reports import render_docx, render_markdown, safe_report_filename
from app.schemas import AnalysisReport, Finding
from docx import Document


def sample_report() -> AnalysisReport:
    return AnalysisReport(
        report_id="abc123",
        repository_url="https://github.com/pallets/itsdangerous",
        repository_name="itsdangerous",
        summary="A concise repository assessment.",
        findings=[
            Finding(
                title="Example issue",
                severity="high",
                file="src/example.py",
                line=12,
                description="Evidence-backed description.",
                recommendation="Apply a targeted fix.",
            )
        ],
        strengths=["Clear project structure."],
        limitations=["Only selected text files were inspected."],
        generated_at="2026-11-22T12:00:00+00:00",
    )


def test_markdown_report_contains_overview_and_scope():
    markdown = render_markdown(sample_report())
    assert "# Repository Quality Report: itsdangerous" in markdown
    assert "| High | 1 |" in markdown
    assert "Evidence and impact" in markdown
    assert "Review Scope and Disclaimer" in markdown


def test_docx_report_contains_findings_and_sections():
    document_bytes = render_docx(sample_report())
    document = Document(BytesIO(document_bytes))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Repository Quality Report" in text
    assert "Example issue" in text
    assert "Recommended action" in text
    assert "Review Scope and Disclaimer" in text
    assert len(document.tables) == 2


def test_safe_report_filename_removes_unsafe_characters():
    assert safe_report_filename("../my repo?") == "my-repo"
    assert safe_report_filename("...") == "repository"
