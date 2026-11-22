from app.analyzer import (
    _source_evidence_is_valid,
    normalize_findings,
)
from app.schemas import Finding


def test_normalize_findings_requires_source_evidence():
    findings = normalize_findings([
        {
            "title": "Unsupported claim",
            "severity": "critical",
            "file": "src/app.py",
            "line": 10,
            "description": "No source excerpt was supplied.",
            "recommendation": "Investigate.",
        },
        {
            "title": "Evidence-backed issue",
            "severity": "high",
            "file": "src/app.py",
            "line": 12,
            "evidence": "unsafe_call(value)",
            "description": "The call uses untrusted input.",
            "recommendation": "Validate the input.",
        },
    ])

    assert len(findings) == 1
    assert findings[0].title == "Evidence-backed issue"
    assert findings[0].evidence == "unsafe_call(value)"
    assert findings[0].line == 12


def test_finding_evidence_defaults_for_older_saved_reports():
    finding = Finding(
        title="Legacy finding",
        severity="low",
        description="Older report record.",
        recommendation="Review manually.",
    )

    assert finding.evidence == ""


def test_source_evidence_requires_exact_quote_and_matching_line():
    context = (
        "--- FILE: src/app.py ---\n"
        "   10 | def handler(value):\n"
        "   11 |     cleaned = value.strip()\n"
        "   12 |     unsafe_call(cleaned)\n"
        "   13 |     return True\n"
    )
    finding = {
        "file": "src/app.py",
        "line": 12,
        "evidence": "unsafe_call(cleaned)",
    }

    assert _source_evidence_is_valid(finding, context)
    assert not _source_evidence_is_valid(
        {**finding, "line": 11},
        context,
    )
    assert not _source_evidence_is_valid(
        {**finding, "evidence": "missing_call(value)"},
        context,
    )
    assert not _source_evidence_is_valid(
        {**finding, "file": "src/other.py"},
        context,
    )
