from __future__ import annotations

import linecache
import ast
import sys
import threading
import trace
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "open_world_watch"


def executable_lines(path: Path) -> set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    ignored = (ast.Import, ast.ImportFrom)
    return {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt)
        and not isinstance(node, ignored)
        and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    tracer = trace.Trace(count=True, trace=False)

    def run_tests() -> unittest.result.TestResult:
        threading.settrace(tracer.globaltrace)
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)
        try:
            return runner.run(suite)
        finally:
            threading.settrace(None)

    result = tracer.runfunc(run_tests)
    counts = tracer.results().counts

    total = 0
    covered = 0
    for file_path in PACKAGE.glob("*.py"):
        executable = executable_lines(file_path)
        if not executable:
            continue
        total += len(executable)
        filename = str(file_path)
        covered_lines = {line for (count_file, line), count in counts.items() if count_file == filename and count > 0}
        covered += len(executable & covered_lines)
        missed = sorted(executable - covered_lines)
        if missed:
            print(f"{file_path.name}: missed {missed[:12]}{'...' if len(missed) > 12 else ''}")

    percent = (covered / total * 100) if total else 100.0
    print(f"Line coverage: {percent:.2f}% ({covered}/{total})")
    linecache.clearcache()
    return 0 if result.wasSuccessful() and percent >= 90.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
