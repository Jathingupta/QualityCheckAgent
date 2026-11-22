from pathlib import Path

from app.analyzer import split_context
from app.repository import read_repository_context


def test_split_context_keeps_file_boundaries():
    context = "".join(
        f"\n--- FILE: src/file_{i}.py ---\n" + ("x" * 1800)
        for i in range(8)
    )
    batches = split_context(context, max_chars=4000)

    assert len(batches) > 1
    assert all(len(batch) <= 4000 for batch in batches)
    assert sum(batch.count("--- FILE:") for batch in batches) == 8


def test_repository_context_skips_lockfiles_and_large_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    return True\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text('{"lock": true}', encoding="utf-8")
    (tmp_path / "src" / "generated.py").write_text("x" * 70000, encoding="utf-8")

    context, included = read_repository_context(tmp_path, max_files=10, max_chars=10000)

    assert included == ["src/main.py"]
    assert "package-lock.json" not in context
    assert "generated.py" not in context
