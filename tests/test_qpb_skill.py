from pathlib import Path

from app import qpb_skill


def _make_skill(root: Path) -> None:
    for relative in qpb_skill.REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "metadata:\n  version: 1.6.1\n" if relative == "SKILL.md" else "test asset\n",
            encoding="utf-8",
        )


def test_skill_manifest_accepts_complete_v161_bundle(tmp_path):
    _make_skill(tmp_path)
    missing, version = qpb_skill._manifest(tmp_path)
    assert missing == []
    assert version == "1.6.1"


def test_skill_manifest_reports_missing_files(tmp_path):
    (tmp_path / "SKILL.md").write_text("metadata:\n  version: 1.6.1\n", encoding="utf-8")
    missing, version = qpb_skill._manifest(tmp_path)
    assert version == "1.6.1"
    assert "phase_prompts/phase6_auditor.md" in missing


def test_phase_prompt_rejects_invalid_phase(tmp_path):
    try:
        qpb_skill.phase_prompt(tmp_path, 7)
    except ValueError as exc:
        assert "between 1 and 6" in str(exc)
    else:
        raise AssertionError("Invalid phase should be rejected")
