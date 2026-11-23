import subprocess
import sys

import pytest
from app import qpb_runner


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

def test_build_runner_command_can_resume_from_phase_three(monkeypatch, tmp_path):
    runner = tmp_path / "bin" / "run_playbook.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("", encoding="utf-8")
    monkeypatch.setattr(qpb_runner, "qpb_checkout", lambda: tmp_path)

    command = qpb_runner.build_runner_command(
        tmp_path / "target", "copilot", phases=[3, 4, 5, 6]
    )

    assert command[command.index("--phase") + 1] == "3,4,5,6"


def test_build_runner_command_rejects_out_of_order_phases(monkeypatch, tmp_path):
    runner = tmp_path / "bin" / "run_playbook.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("", encoding="utf-8")
    monkeypatch.setattr(qpb_runner, "qpb_checkout", lambda: tmp_path)

    with pytest.raises(ValueError, match="unique, ordered"):
        qpb_runner.build_runner_command(
            tmp_path / "target", "copilot", phases=[4, 3, 5, 6]
        )


def test_pinned_qpb_runner_cli_supports_application_flags():
    checkout = qpb_runner.qpb_checkout()
    runner = checkout / "bin" / "run_playbook.py"
    assert runner.is_file(), "QPB submodule must be initialized in CI"

    result = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=checkout,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for flag in ("--copilot", "--phase", "--sequential", "--model", "--council-roster"):
        assert flag in result.stdout


def test_copilot_availability_requires_standalone_or_legacy_extension(monkeypatch):
    monkeypatch.setattr(
        qpb_runner.shutil,
        "which",
        lambda name: "/usr/bin/copilot" if name == "copilot" else None,
    )
    assert qpb_runner._copilot_available() is True

    monkeypatch.setattr(
        qpb_runner.shutil,
        "which",
        lambda name: "/usr/bin/gh" if name == "gh" else None,
    )
    monkeypatch.setattr(
        qpb_runner.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 1})(),
    )
    assert qpb_runner._copilot_available() is False
