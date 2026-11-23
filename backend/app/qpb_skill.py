from __future__ import annotations

import hashlib
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

QPB_VERSION = "1.6.1"
QPB_COMMIT = "ee60d579ecf43ee000039736e4bb1edbabe0201a"
SKILL_RELATIVE = Path("plugins/quality-playbook/skills/quality-playbook")
PHASE_FILES = tuple(f"phase_prompts/phase{number}.md" for number in range(1, 7))
REQUIRED_FILES = (
    "SKILL.md",
    "scripts/qpb_validate.py",
    "scripts/quality_gate.py",
    "scripts/validate_phase_artifacts.py",
    "references/phase1_exploration_guide.md",
    "references/phase2_generation_guide.md",
    "references/review_protocols.md",
    "references/spec_audit.md",
    "references/requirements_pipeline.md",
    *PHASE_FILES,
    "phase_prompts/phase6_auditor.md",
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

def skill_source() -> Path:
    return project_root() / "vendor" / "quality-playbook" / SKILL_RELATIVE

def _manifest(root: Path) -> tuple[list[str], str | None]:
    import re
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    skill_md = root / "SKILL.md"
    version = None
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        match = re.search(r"(?m)^\s*version:\s*['\"]?([0-9]+\.[0-9]+\.[0-9]+)", text)
        version = match.group(1) if match else None
    return missing, version

def inspect_skill(install_path: Path | None = None) -> SkillStatus:
    source = skill_source()
    target = install_path or source
    if not target.is_dir():
        return SkillStatus(False, None, str(source), str(target), list(REQUIRED_FILES),
                           "Pinned Quality Playbook source is not available. Initialize the Git submodule.")
    missing, version = _manifest(target)
    ok = not missing and version == QPB_VERSION
    message = ("Official QPB skill assets are present and version-checked."
               if ok else "Skill installation is incomplete or has an unexpected version.")
    return SkillStatus(ok, version, str(source), str(target), missing, message)

def install_skill(target_repository: Path) -> SkillStatus:
    source = skill_source()
    source_status = inspect_skill(source)
    if not source_status.installed:
        raise RuntimeError(
            "Pinned Quality Playbook skill source is incomplete: "
            + ", ".join(source_status.missing_files[:8])
        )
    destination = target_repository / ".github" / "skills" / "quality-playbook"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        current = inspect_skill(destination)
        if current.installed:
            return current
        raise RuntimeError(
            f"Refusing to overwrite an existing incomplete skill installation at {destination}"
        )
    shutil.copytree(source, destination)
    status = inspect_skill(destination)
    if not status.installed:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError("Installed skill failed post-install validation.")
    return status

def phase_prompt(target_repository: Path, phase: int) -> str:
    if phase not in range(1, 7):
        raise ValueError("Phase must be between 1 and 6.")
    installed = target_repository / ".github" / "skills" / "quality-playbook"
    status = inspect_skill(installed)
    if not status.installed:
        raise RuntimeError("Quality Playbook skill is not installed correctly.")
    return (installed / f"phase_prompts/phase{phase}.md").read_text(encoding="utf-8")

def skill_fingerprint(root: Path | None = None) -> str:
    root = root or skill_source()
    digest = hashlib.sha256()
    for relative in REQUIRED_FILES:
        path = root / relative
        if path.is_file():
            digest.update(relative.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()

def status_dict(status: SkillStatus) -> dict:
    return asdict(status)
