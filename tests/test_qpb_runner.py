from pathlib import Path

import pytest

from app import qpb_runner, qpb_skill


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


def test_build_runner_command_uses_official_six_phase_mode_b(monkeypatch, tmp_path):
    checkout = tmp_path / "qpb"
    runner = checkout / "bin" / "run_playbook.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# upstream runner placeholder", encoding="utf-8")
    monkeypatch.setattr(qpb_runner, "qpb_checkout", lambda: checkout)

    command = qpb_runner.build_runner_command(
        tmp_path / "target",
        "copilot",
        model="gpt-5.5",
        council_roster="claude-opus-4.7,gpt-5.5,claude-sonnet-4.6",
    )

    assert str(runner) in command
    assert "--copilot" in command
    assert command[command.index("--phase") + 1] == "1,2,3,4,5,6"
    assert "--sequential" in command
    assert command[command.index("--model") + 1] == "gpt-5.5"
    assert command[command.index("--council-roster") + 1].count(",") == 2


def test_build_runner_command_requires_three_council_members(monkeypatch, tmp_path):
    runner = tmp_path / "bin" / "run_playbook.py"
    runner.parent.mkdir()
    runner.write_text("", encoding="utf-8")
    monkeypatch.setattr(qpb_runner, "qpb_checkout", lambda: tmp_path)

    with pytest.raises(ValueError, match="exactly three"):
        qpb_runner.build_runner_command(
            tmp_path / "target", "copilot", council_roster="gpt-5.5"
        )


def test_phase_progress_requires_exact_completed_checkpoints():
    progress = (
        "- [x] Phase 1 - Explore\n"
        "- [x] Phase 2 - Generate\n"
        "- [ ] Phase 3 - Code Review\n"
    )
    phases = qpb_runner._phase_progress(progress, return_code=1)

    assert phases[0]["status"] == "completed"
    assert phases[1]["status"] == "completed"
    assert phases[2]["status"] == "failed"
    assert phases[3]["status"] == "pending"


def test_run_file_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="Invalid QPB run ID"):
        qpb_runner._run_file(tmp_path, "../outside")
