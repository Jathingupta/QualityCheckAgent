from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.qpb_skill import qpb_checkout

RUNNER_FLAGS = {
    "copilot": "--copilot",
    "claude": "--claude",
    "codex": "--codex",
    "cursor": "--cursor",
}
PHASES = (
    "Explore",
    "Generate",
    "Code Review",
    "Spec Audit",
    "Reconciliation",
    "Verify",
)
GATE_RESULTS = (
    "RESULT: GATE PASSED",
    "RESULT: GATE PASSED WITH CLEANUP NEEDED",
    "RESULT: GATE PASSED WITH DECISIONS NEEDED",
)


def _run_file(workspace: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Invalid QPB run ID.")
    return workspace / "qpb_runs" / run_id / "run.json"


def load_run(workspace: Path, run_id: str) -> dict[str, Any]:
    path = _run_file(workspace, run_id)
    if not path.is_file():
        raise FileNotFoundError("QPB run not found.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_run(workspace: Path, run_id: str, state: dict[str, Any]) -> None:
    path = _run_file(workspace, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def _copilot_available() -> bool:
    if shutil.which("copilot") is not None:
        return True
    if shutil.which("gh") is None:
        return False
    try:
        result = subprocess.run(
            ["gh", "copilot", "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def runner_availability() -> dict[str, bool]:
    return {
        "copilot": _copilot_available(),
        "claude": shutil.which("claude") is not None,
        "codex": shutil.which("codex") is not None,
        "cursor": shutil.which("cursor") is not None,
    }


def build_runner_command(
    target: Path,
    runner: str,
    model: str | None = None,
    council_roster: str | None = None,
    phases: list[int] | None = None,
    include_iterations: bool = True,
) -> list[str]:
    if runner not in RUNNER_FLAGS:
        raise ValueError(f"Unsupported QPB runner: {runner}")
    runner_script = qpb_checkout() / "bin" / "run_playbook.py"
    if not runner_script.is_file():
        raise RuntimeError(
            "Official QPB Mode-B runner is missing from the pinned submodule. "
            "Run 'git submodule update --init --recursive'."
        )
    selected_phases = phases or [1, 2, 3, 4, 5, 6]
    if (
        not selected_phases
        or any(phase not in range(1, 7) for phase in selected_phases)
        or len(set(selected_phases)) != len(selected_phases)
        or selected_phases != sorted(selected_phases)
    ):
        raise ValueError("QPB phases must be unique, ordered values between 1 and 6.")
    phase_spec = ",".join(str(phase) for phase in selected_phases)
    command = [
        sys.executable,
        str(runner_script),
        str(target),
        RUNNER_FLAGS[runner],
        "--phase-groups",
        phase_spec,
        "--sequential",
    ]
    if include_iterations:
        command.extend([
            "--iterations",
            "gap,unfiltered,parity,adversarial",
        ])
    if model:
        command.extend(["--model", model])
    if council_roster:
        members = [member.strip() for member in council_roster.split(",") if member.strip()]
        if len(members) != 3:
            raise ValueError("QPB Council roster must contain exactly three model identifiers.")
        command.extend(["--council-roster", ",".join(members)])
    return command


def _phase_progress(progress_text: str, return_code: int) -> list[dict[str, Any]]:
    """Read the official QPB checklist, whose separator is an em dash."""
    results = []
    for number, name in enumerate(PHASES, start=1):
        marker_pattern = re.compile(
            rf"(?m)^\\s*-\\s*\\[x\\]\\s*Phase\\s+{number}\\s+[-—–]\\s*"
            rf"{re.escape(name)}(?:\\s*(?:\\([^\\n]*\\))?)?\\s*$",
            re.IGNORECASE,
        )
        matched = marker_pattern.search(progress_text)
        evidence = matched.group(0).strip() if matched else None
        results.append({
            "number": number,
            "name": name,
            "status": "completed" if matched else "pending",
            "evidence": [evidence] if evidence else [],
        })
    if return_code != 0:
        first_pending = next((p for p in results if p["status"] == "pending"), None)
        if first_pending:
            first_pending["status"] = "failed"
    return results


def execute_qpb_run(
    workspace: Path,
    run_id: str,
    runner: str,
    model: str | None = None,
    council_roster: str | None = None,
    phases: list[int] | None = None,
    include_iterations: bool = True,
) -> None:
    state = load_run(workspace, run_id)
    target = Path(state["repository_path"]).resolve()
    expected_root = (workspace / "repositories").resolve()
    if expected_root not in target.parents:
        raise RuntimeError("QPB target path is outside the application workspace.")
    run_dir = _run_file(workspace, run_id).parent
    log_path = run_dir / "runner.log"
    state.update({
        "status": "running",
        "runner": runner,
        "model": model,
        "council_roster": council_roster,
        "include_iterations": include_iterations,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "log_path": str(log_path),
    })
    save_run(workspace, run_id, state)
    timeout_seconds = 6 * 60 * 60
    return_code = -1
    failure = None
    try:
        selected_phases = phases or [1, 2, 3, 4, 5, 6]
        state["requested_phases"] = selected_phases
        save_run(workspace, run_id, state)
        command = build_runner_command(
            target, runner, model, council_roster, selected_phases,
            include_iterations=include_iterations,
        )
        with log_path.open("w", encoding="utf-8") as log:
            log.write("COMMAND: " + subprocess.list2cmdline(command) + "\n\n")
            log.flush()
            completed = subprocess.run(
                command,
                cwd=qpb_checkout(),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return_code = completed.returncode
    except subprocess.TimeoutExpired:
        failure = f"QPB runner exceeded the {timeout_seconds}-second execution limit."
    except Exception as exc:  # Persist the failure for UI recovery.
        failure = f"{type(exc).__name__}: {exc}"

    progress_path = target / "quality" / "PROGRESS.md"
    progress_text = (
        progress_path.read_text(encoding="utf-8", errors="replace")
        if progress_path.is_file() else ""
    )
    gate_path = target / "quality" / "results" / "quality-gate.log"
    gate_text = (
        gate_path.read_text(encoding="utf-8", errors="replace")
        if gate_path.is_file() else ""
    )
    gate_result = next(
        (line.strip() for line in gate_text.splitlines()
         if line.strip().startswith("RESULT: GATE ")),
        None,
    )
    phases = _phase_progress(progress_text, return_code)
    all_phases_complete = all(item["status"] == "completed" for item in phases)
    gate_passed = gate_result is not None and any(
        gate_result.startswith(result) for result in GATE_RESULTS
    )
    success = return_code == 0 and all_phases_complete and gate_passed
    state.update({
        "status": "completed" if success else "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "return_code": return_code,
        "failure": failure,
        "phases": phases,
        "gate_result": gate_result,
        "gate_log_path": str(gate_path) if gate_path.is_file() else None,
        "progress_path": str(progress_path) if progress_path.is_file() else None,
        "log_tail": (
            log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
            if log_path.is_file() else ""
        ),
        "message": (
            "All six phases completed and the official QPB gate reported a passing result."
            if success else
            "QPB execution did not satisfy all six phase checkpoints and the official gate. "
            "Review the runner log and resume or repair the failed phase."
        ),
    })
    save_run(workspace, run_id, state)
