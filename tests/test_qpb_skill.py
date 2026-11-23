from pathlib import Path

import pytest
from app import qpb_skill


def _make_installed_skill(root: Path) -> None:
    for relative in qpb_skill.INSTALLED_REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "metadata:\n  version: 1.6.1\n" if relative == "SKILL.md" else "test asset\n",
            encoding="utf-8",
        )


def test_version_reads_skill_frontmatter(tmp_path):
    (tmp_path / "SKILL.md").write_text(
        "metadata:\n  version: 1.6.1\n", encoding="utf-8"
    )
    assert qpb_skill._version(tmp_path) == "1.6.1"


def test_install_manifest_accepts_complete_v161_bundle(tmp_path):
    _make_installed_skill(tmp_path)
    status = qpb_skill.inspect_skill(tmp_path)
    assert status.installed is True
    assert status.version == "1.6.1"
    assert status.missing_files == []


def test_install_manifest_reports_missing_files(tmp_path):
    (tmp_path / "SKILL.md").write_text(
        "metadata:\n  version: 1.6.1\n", encoding="utf-8"
    )
    status = qpb_skill.inspect_skill(tmp_path)
    assert status.installed is False
    assert "phase_prompts/phase6_auditor.md" in status.missing_files


def test_phase_prompt_rejects_invalid_phase(tmp_path):
    with pytest.raises(ValueError, match="between 1 and 6"):
        qpb_skill.phase_prompt(tmp_path, 7)
