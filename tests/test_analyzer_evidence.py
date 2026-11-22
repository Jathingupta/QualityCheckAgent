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


def test_analyzer_prompt_requires_runtime_semantic_verification():
    from app.analyzer import SYSTEM_PROMPT

    assert "perform an adversarial semantic check" in SYSTEM_PROMPT
    assert "underlying function" in SYSTEM_PROMPT
    normalized_prompt = " ".join(SYSTEM_PROMPT.split())
    assert "from __future__ import annotations" in normalized_prompt
    assert "names used only in annotations are not evaluated" in normalized_prompt
    assert "runtime path from the quoted code to" in normalized_prompt
    assert "Do not label code defective just because it looks unusual." in SYSTEM_PROMPT


def test_analyzer_prompt_requires_impact_and_severity_calibration():
    from app.analyzer import SYSTEM_PROMPT

    normalized_prompt = " ".join(SYSTEM_PROMPT.split())
    assert "attacker-controlled input" in normalized_prompt
    assert "reachable entry point" in normalized_prompt
    assert "violated security property" in normalized_prompt
    assert "signature forgery" in normalized_prompt
    assert "does not by itself demonstrate" in normalized_prompt
    assert "Calibrate severity to demonstrated impact and exploitability" in normalized_prompt
    assert "Reserve critical/high for concrete severe consequences" in normalized_prompt


def test_analyzer_prompt_distinguishes_permissive_parsing_from_security_bypass():
    from app.analyzer import SYSTEM_PROMPT

    normalized_prompt = " ".join(SYSTEM_PROMPT.split())
    assert "Do not automatically infer that downstream validation or security checks are bypassed." in normalized_prompt
    assert "Follow the transformed value through its consumers." in normalized_prompt
    assert "security impact was not demonstrated" in normalized_prompt
    assert "do not prescribe stricter parsing as an automatic fix" in normalized_prompt


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
