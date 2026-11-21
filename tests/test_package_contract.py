"""Guard documentation and signature coverage without importing CLI entry points."""

import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "pypodcastde"


class PackageContractTests(unittest.TestCase):
    """Check every package module, including private and nested definitions."""

    def test_docstrings_and_annotations(self) -> None:
        """Require nonempty docstrings and annotated parameters and returns."""
        for path in sorted(PACKAGE.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                with self.subTest(file=path.name, definition=getattr(node, "name", "<module>")):
                    self.assertTrue((ast.get_docstring(node) or "").strip(), "missing docstring")
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, "missing return annotation")
                        args = node.args
                        positional = args.posonlyargs + args.args
                        if positional and positional[0].arg in {"self", "cls"}:
                            positional = positional[1:]
                        for param in [*positional, *args.kwonlyargs, args.vararg, args.kwarg]:
                            if param is not None:
                                self.assertIsNotNone(
                                    param.annotation, f"untyped parameter: {param.arg}"
                                )
