from app.analyzer import normalize_findings
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
