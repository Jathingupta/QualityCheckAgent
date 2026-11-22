import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cs",
    ".php", ".rb", ".sql", ".yaml", ".yml", ".toml", ".json", ".md",
    ".html", ".css", ".sh", ".ps1", ".xml",
}
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".next", ".nuxt", "coverage", ".pytest_cache",
}
SKIP_FILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "uv.lock", "pipfile.lock", "cargo.lock", "composer.lock",
    "gemfile.lock", "go.sum",
}
SECRET_HINTS = (".env", "secret", "credential", "private", "id_rsa")
MAX_FILE_BYTES = 64 * 1024
MAX_FILE_CHARS = 6000


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
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--no-tags", clone_url, str(destination)],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Git clone failed: {result.stderr[-1000:]}")
    return name


def _file_priority(path: Path, relative: str) -> tuple[int, int, str]:
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    if name in {"main.py", "app.py", "server.py", "index.ts", "index.js", "main.ts", "main.go"}:
        priority = 0
    elif any(part in {"src", "app", "lib", "core", "api", "services"} for part in parts):
        priority = 1
    elif any(part in {"tests", "test"} for part in parts) or name.startswith("test_"):
        priority = 2
    elif name in {"readme.md", "pyproject.toml", "package.json", "requirements.txt", "go.mod"}:
        priority = 3
    else:
        priority = 4
    return priority, len(path.parts), relative.lower()


def _numbered_excerpt(content: str, limit: int = MAX_FILE_CHARS) -> str:
    """Add original 1-based line numbers and explicitly mark incomplete excerpts."""
    lines = content.splitlines()
    numbered = []
    used = 0
    for line_number, line in enumerate(lines, start=1):
        rendered = f"{line_number:>5} | {line}"
        remaining = limit - used
        if len(rendered) + 1 > remaining:
            if remaining > 24:
                numbered.append(
                    f"{line_number:>5} | [LINE TRUNCATED: source line exceeds excerpt budget]"
                )
            numbered.append(
                f"       | [FILE EXCERPT TRUNCATED; source continues after line "
                f"{line_number - 1}]"
            )
            break
        numbered.append(rendered)
        used += len(rendered) + 1
    else:
        return "\n".join(numbered)
    return "\n".join(numbered)


def read_repository_context(root: Path, max_files: int, max_chars: int) -> tuple[str, list[str]]:
    candidates = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name.lower() in SKIP_FILES or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if any(hint in relative.lower() for hint in SECRET_HINTS):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        candidates.append((path, relative))

    candidates.sort(key=lambda item: _file_priority(item[0], item[1]))
    chunks, included, used = [], [], 0
    for path, relative in candidates:
        if len(included) >= max_files:
            break
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not content.strip() or "\x00" in content:
            continue
        excerpt = _numbered_excerpt(content)
        block = f"\n--- FILE: {relative} ---\n{excerpt}\n"
        if used + len(block) > max_chars:
            continue
        chunks.append(block)
        included.append(relative)
        used += len(block)
    return "\n".join(chunks), included
