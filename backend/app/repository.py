import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cs", ".php", ".rb", ".sql", ".yaml", ".yml", ".toml", ".json", ".md", ".html", ".css", ".sh", ".ps1", ".xml"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
SECRET_HINTS = (".env", "secret", "credential", "private", "id_rsa")


def validate_github_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Only public GitHub HTTPS repository URLs are supported.")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts[:2]):
        raise ValueError("URL must look like https://github.com/owner/repository")
    owner, repo = parts[:2]
    repo = repo.removesuffix(".git")
    return f"https://github.com/{owner}/{repo}.git", f"{owner}/{repo}"


def clone_repository(url: str, destination: Path, timeout: int) -> str:
    clone_url, name = validate_github_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    result = subprocess.run(["git", "clone", "--depth", "1", "--no-tags", clone_url, str(destination)], capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"Git clone failed: {result.stderr[-1000:]}")
    return name


def read_repository_context(root: Path, max_files: int, max_chars: int) -> tuple[str, list[str]]:
    candidates = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if any(hint in relative.lower() for hint in SECRET_HINTS):
            continue
        candidates.append(path)
    candidates.sort(key=lambda p: (0 if p.name.lower() in {"readme.md", "pyproject.toml", "package.json", "requirements.txt"} else 1, len(p.parts), str(p).lower()))
    chunks, included, used = [], [], 0
    for path in candidates[:max_files * 3]:
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "\x00" in content:
            continue
        block = f"\n--- FILE: {path.relative_to(root).as_posix()} ---\n{content[:8000]}\n"
        if used + len(block) > max_chars or len(included) >= max_files:
            break
        chunks.append(block)
        included.append(path.relative_to(root).as_posix())
        used += len(block)
    return "\n".join(chunks), included
