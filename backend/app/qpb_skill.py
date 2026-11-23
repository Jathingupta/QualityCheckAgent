from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

QPB_VERSION = "1.6.1"
QPB_COMMIT = "ee60d579ecf43ee000039736e4bb1edbabe0201a"
SKILL_RELATIVE = Path("plugins/quality-playbook/skills/quality-playbook")
PHASE_FILES = tuple(f"phase_prompts/phase{number}.md" for number in range(1, 7))
INSTALLED_REQUIRED_FILES = (
    "SKILL.md", "LICENSE.txt", "quality_gate.py", "skill-template.gitignore",
    "ai_context/TOOLKIT.md",
    "agents/quality-playbook.agent.md",
    "agents/quality-playbook-claude.agent.md",
    "agents/calibration_orchestrator.md",
    "bin/_purpose.py", "bin/citation_verifier.py", "bin/qpb_validate.py",
    "bin/validate_phase_artifacts.py", "bin/reference_docs_ingest.py",
    "bin/doc_classification.py", "bin/benchmark_lib.py",
    "bin/quality_playbook.py", "bin/council_semantic_check.py",
    "bin/role_map.py", "bin/persona_apply.py", "bin/qpb_phase.py",
    "bin/run_state_lib.py", "bin/qpb_config.py",
    "references/phase1_exploration_guide.md",
    "references/phase2_generation_guide.md", "references/review_protocols.md",
    "references/spec_audit.md", "references/requirements_pipeline.md",
    *PHASE_FILES, "phase_prompts/phase6_auditor.md",
)

@dataclass
class SkillStatus:
    installed: bool
    version: str | None
    source: str | None
    install_path: str | None
    missing_files: list[str]
    message: str

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def qpb_checkout() -> Path:
    return project_root() / "vendor" / "quality-playbook"

def skill_source() -> Path:
    return qpb_checkout() / SKILL_RELATIVE

def _version(root: Path) -> str | None:
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return None
    match = re.search(
        r"(?m)^\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
        skill_md.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else None

def inspect_skill(install_path: Path | None = None) -> SkillStatus:
    if install_path is None:
        root = skill_source()
        source_files = (
            "SKILL.md", "skill-template.gitignore", "ai_context/TOOLKIT.md",
            "agents/quality-playbook.agent.md",
            "agents/quality-playbook-claude.agent.md",
            "agents/calibration_orchestrator.md",
            "scripts/install_skill.py", "scripts/quality_gate.py",
            "scripts/qpb_validate.py", "scripts/citation_verifier.py",
            "scripts/_purpose.py", "scripts/benchmark_lib.py",
            "scripts/reference_docs_ingest.py", "scripts/doc_classification.py",
            "scripts/quality_playbook.py", "scripts/council_semantic_check.py",
            "scripts/role_map.py", "scripts/persona_apply.py",
            "scripts/qpb_phase.py", "scripts/run_state_lib.py",
            "scripts/qpb_config.py", *PHASE_FILES,
            "phase_prompts/phase6_auditor.md",
            "references/phase1_exploration_guide.md",
            "references/phase2_generation_guide.md",
            "references/review_protocols.md", "references/spec_audit.md",
            "references/requirements_pipeline.md",
        )
        missing = [name for name in source_files if not (root / name).is_file()]
        if not (qpb_checkout() / "LICENSE.txt").is_file():
            missing.append("LICENSE.txt")
        version = _version(root)
        ok = not missing and version == QPB_VERSION
        return SkillStatus(
            ok, version, str(root), None, missing,
            "Pinned upstream QPB skill source is available."
            if ok else "Pinned QPB submodule is missing required skill assets.",
        )

    root = install_path
    missing = [name for name in INSTALLED_REQUIRED_FILES if not (root / name).is_file()]
    version = _version(root)
    ok = not missing and version == QPB_VERSION
    return SkillStatus(
        ok, version, str(skill_source()), str(root), missing,
        "Official QPB skill installation is complete and version-checked."
        if ok else "Skill installation is incomplete or has an unexpected version.",
    )

def install_skill(target_repository: Path) -> SkillStatus:
    source_status = inspect_skill()
    if not source_status.installed:
        raise RuntimeError(
            "Pinned Quality Playbook source is incomplete: "
            + ", ".join(source_status.missing_files[:10])
            + ". Run 'git submodule update --init --recursive' in the application checkout."
        )
    installer = skill_source() / "scripts" / "install_skill.py"
    destination = target_repository / ".github" / "skills" / "quality-playbook"
    if destination.exists():
        current = inspect_skill(destination)
        if current.installed:
            return current
        raise RuntimeError(
            f"Refusing to overwrite an existing incomplete skill installation at {destination}"
        )
    command = [
        sys.executable, str(installer), "--into", str(target_repository),
        "--ai-tool", "copilot", "--source", str(qpb_checkout()), "--verbose",
    ]
    result = subprocess.run(
        command, cwd=target_repository, capture_output=True, text=True,
        timeout=120, check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Official QPB installer failed (exit {result.returncode}). "
            f"stdout: {result.stdout[-2500:]} stderr: {result.stderr[-2500:]}"
        )
    license_source = qpb_checkout() / "LICENSE.txt"
    if not license_source.is_file():
        raise RuntimeError("Pinned QPB checkout is missing LICENSE.txt.")
    shutil.copy2(license_source, destination / "LICENSE.txt")
    status = inspect_skill(destination)
    if not status.installed:
        raise RuntimeError(
            "Official installer returned success but the installed bundle failed "
            "post-install validation: " + ", ".join(status.missing_files[:10])
        )
    return status

def phase_prompt(target_repository: Path, phase: int) -> str:
    if phase not in range(1, 7):
        raise ValueError("Phase must be between 1 and 6.")
    installed = target_repository / ".github" / "skills" / "quality-playbook"
    if not inspect_skill(installed).installed:
        raise RuntimeError("Quality Playbook skill is not installed correctly.")
    return (installed / f"phase_prompts/phase{phase}.md").read_text(encoding="utf-8")

def skill_fingerprint(root: Path | None = None) -> str:
    root = root or skill_source()
    if (root / "scripts").is_dir():
        files = (
            "SKILL.md", "scripts/quality_gate.py", "scripts/qpb_validate.py",
            "scripts/install_skill.py", *PHASE_FILES, "phase_prompts/phase6_auditor.md",
        )
    else:
        files = (
            "SKILL.md", "quality_gate.py", "bin/qpb_validate.py",
            "bin/validate_phase_artifacts.py", *PHASE_FILES,
            "phase_prompts/phase6_auditor.md",
        )
    digest = hashlib.sha256()
    for relative in files:
        path = root / relative
        if path.is_file():
            digest.update(relative.encode())
            digest.update(path.read_bytes())
    license_path = (
        qpb_checkout() / "LICENSE.txt"
        if (root / "scripts").is_dir()
        else root / "LICENSE.txt"
    )
    if license_path.is_file():
        digest.update(b"LICENSE.txt")
        digest.update(license_path.read_bytes())
    return digest.hexdigest()

def status_dict(status: SkillStatus) -> dict:
    return asdict(status)
