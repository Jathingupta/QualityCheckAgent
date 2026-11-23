from pathlib import Path

import pytest
from app import qpb_skill


def _make_installed_skill(root: Path) -> None:
    required = list(qpb_skill.INSTALLED_REQUIRED_FILES)
    for directory in ("references", "phase_prompts", "agents"):
        source_dir = qpb_skill.skill_source() / directory
        if source_dir.is_dir():
            required.extend(
                f"{directory}/{path.name}" for path in source_dir.glob("*.md")
            )
    for relative in required:
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


def test_pinned_upstream_skill_source_is_complete():
    status = qpb_skill.inspect_skill()
    assert status.installed is True, status.missing_files
    assert status.version == qpb_skill.QPB_VERSION


def test_official_installer_deploys_skill_to_copilot_layout(tmp_path):
    status = qpb_skill.install_skill(tmp_path)
    destination = tmp_path / ".github" / "skills" / "quality-playbook"
    assert status.installed is True
    assert (destination / "SKILL.md").is_file()
    assert (destination / "quality_gate.py").is_file()
    assert (destination / "bin" / "qpb_validate.py").is_file()
    assert (destination / "LICENSE.txt").is_file()
