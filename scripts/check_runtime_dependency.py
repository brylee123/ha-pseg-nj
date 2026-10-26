"""Ensure the integration resolves its pinned installed package, without vendoring."""

import ast
import json
from importlib.metadata import version
from pathlib import Path

import pseg_mymeter

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/pseg_nj"
manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
assert manifest["requirements"] == ["pseg-nj-mymeter==0.2.0"]
assert version("pseg-nj-mymeter") == "0.2.0"
assert not (component / "_vendor").exists()
for path in component.glob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "_vendor" not in (node.module or "")
assert not Path(pseg_mymeter.__file__).resolve().is_relative_to(component.resolve())
print("Pinned installed PyPI library verified; no vendored imports remain")
