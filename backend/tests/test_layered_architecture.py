from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
SQLALCHEMY_STATEMENTS = {"select", "delete", "update"}


def _python_files(directory: Path, *, excluded_names: set[str] | None = None) -> list[Path]:
    excluded = excluded_names or set()
    return sorted(path for path in directory.rglob("*.py") if path.name not in excluded)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_parts(path: Path) -> list[str]:
    parts = list(path.relative_to(BACKEND_ROOT).with_suffix("").parts)
    return parts if path.name == "__init__.py" else parts[:-1]


def _import_targets(path: Path, tree: ast.Module) -> Iterable[tuple[str, int]]:
    package_parts = _module_parts(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                keep = max(0, len(package_parts) - node.level + 1)
                base_parts = package_parts[:keep]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base = ".".join(base_parts)
            else:
                base = node.module or ""
            if base:
                yield base, node.lineno
            for alias in node.names:
                if alias.name != "*":
                    yield ".".join(part for part in (base, alias.name) if part), node.lineno


def _import_aliases(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                aliases[local_name] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def _resolved_name(node: ast.expr, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _resolved_name(node.value, aliases)
        return f"{owner}.{node.attr}" if owner else None
    return None


def _is_module(target: str, forbidden: str) -> bool:
    return target == forbidden or target.startswith(f"{forbidden}.")


def _location(path: Path, line: int, message: str) -> str:
    return f"{path.relative_to(BACKEND_ROOT)}:{line}: {message}"


def test_api_controllers_do_not_access_persistence_directly() -> None:
    forbidden_modules = ("sqlalchemy", "app.db.models", "app.db.session", "app.repositories")
    violations: list[str] = []
    files = _python_files(APP_ROOT / "api", excluded_names={"__init__.py", "error_handlers.py"})

    for path in files:
        tree = _parse(path)
        for target, line in _import_targets(path, tree):
            if any(_is_module(target, forbidden) for forbidden in forbidden_modules):
                violations.append(_location(path, line, f"controller imports forbidden module {target!r}"))

    assert not violations, "Controller persistence boundary violations:\n" + "\n".join(violations)


def test_services_do_not_depend_on_fastapi_or_build_sql_statements() -> None:
    violations: set[str] = set()

    for path in _python_files(APP_ROOT / "services"):
        tree = _parse(path)
        for target, line in _import_targets(path, tree):
            if _is_module(target, "fastapi") or target.rsplit(".", 1)[-1] == "HTTPException":
                violations.add(_location(path, line, f"service imports HTTP concern {target!r}"))
            if _is_module(target, "app.db.session"):
                violations.add(_location(path, line, f"service imports database session {target!r}"))
            if _is_module(target, "sqlalchemy") and target.rsplit(".", 1)[-1] in SQLALCHEMY_STATEMENTS:
                violations.add(_location(path, line, f"service imports SQL statement builder {target!r}"))

        aliases = _import_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = _resolved_name(node.func, aliases)
            if (
                target
                and _is_module(target, "sqlalchemy")
                and target.rsplit(".", 1)[-1] in SQLALCHEMY_STATEMENTS
            ):
                violations.add(_location(path, node.lineno, f"service calls SQL statement builder {target!r}"))

    assert not violations, "Service boundary violations:\n" + "\n".join(sorted(violations))


def test_repositories_do_not_depend_on_http_or_control_transactions() -> None:
    violations: list[str] = []

    for path in _python_files(APP_ROOT / "repositories"):
        tree = _parse(path)
        for target, line in _import_targets(path, tree):
            if _is_module(target, "fastapi") or target.rsplit(".", 1)[-1] == "HTTPException":
                violations.append(_location(path, line, f"repository imports HTTP concern {target!r}"))

        for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            methods = (
                node
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            for method in methods:
                for node in ast.walk(method):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"commit", "rollback"}
                    ):
                        violations.append(
                            _location(
                                path,
                                node.lineno,
                                f"repository method {class_node.name}.{method.name} controls the transaction",
                            )
                        )

    assert not violations, "Repository boundary violations:\n" + "\n".join(violations)
