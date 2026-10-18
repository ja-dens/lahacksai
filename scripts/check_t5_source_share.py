"""Report source composition for information only; no language quota is enforced."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_lines(path):
    text = path.read_text()
    skipped = set()
    if path.suffix == '.py':
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    if isinstance(body[0].value.value, str):
                        skipped.update(range(body[0].lineno, body[0].end_lineno + 1))
    else:
        # Jac module docstrings in this harness use a single-line triple quote.
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith(('"""', "'''")):
                skipped.add(number)
    return sum(1 for number, line in enumerate(text.splitlines(), 1)
               if number not in skipped and line.strip() and not line.lstrip().startswith('#'))


def main():
    counts = {'jac': 0, 'python': 0}
    files = {}
    for path in sorted((ROOT / 'src').rglob('*')):
        if path.suffix in ('.jac', '.py') and not any(p in ('.jac', '__pycache__') for p in path.parts):
            count = source_lines(path)
            counts['jac' if path.suffix == '.jac' else 'python'] += count
            files[str(path.relative_to(ROOT))] = count
    total = sum(counts.values())
    percent = 100 * counts['jac'] / total if total else 0
    print(json.dumps({'scope': 'all src/ harness source, including mocks', 'files': files,
                      'jac_lines': counts['jac'], 'total_source_lines': total,
                      'jac_percent': round(percent, 1), 'enforced': False,
                      'excluded': 'tests, checks, scripts, docs, fixtures, dependencies, generated caches'}, indent=2))


if __name__ == '__main__':
    main()
