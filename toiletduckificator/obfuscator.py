from __future__ import annotations

import ast
import symtable
from dataclasses import dataclass
from pathlib import Path
import re
from typing import TypeAlias

from .name_generator import generate_identifier

VARIABLE_NAME_LENGTH = 16
FUNCTION_NAME_LENGTH = 24
BUILTIN_ALIAS_LENGTH = 24
MODULE_NAME_LENGTH = 8
ENTRYPOINT_FILE_NAMES = {"main.py", "start.py", "app.py"}


SCOPE_NODE_TYPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)

FunctionLikeNode: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef
ComprehensionNode: TypeAlias = ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp


@dataclass(slots=True)
class ObfuscationResult:
    source_path: Path
    output_path: Path
    changed: bool


class ObfuscatorError(Exception):
    """Raised when the input cannot be obfuscated."""


@dataclass(slots=True)
class ScopeInfo:
    table: symtable.SymbolTable
    rename_map: dict[str, str]
    parent: "ScopeInfo | None"


def _module_name_from_relative_path(relative_path: Path) -> str | None:
    parts = list(relative_path.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _resolve_import_from_module(module: str | None, level: int, current_module: str | None) -> str | None:
    if level == 0:
        return module
    if current_module is None:
        return module

    package_parts = current_module.split(".")[:-1]
    ancestor_count = len(package_parts) - (level - 1)
    if ancestor_count < 0:
        return module

    ancestor_parts = package_parts[:ancestor_count]
    if module is None:
        return ".".join(ancestor_parts) if ancestor_parts else None
    return ".".join(ancestor_parts + module.split("."))


def _absolute_to_relative_import(module: str, current_module: str) -> tuple[int, str | None]:
    package_parts = current_module.split(".")[:-1]
    target_parts = module.split(".")

    common_length = 0
    max_common = min(len(package_parts), len(target_parts))
    while common_length < max_common and package_parts[common_length] == target_parts[common_length]:
        common_length += 1

    if common_length == 0:
        return 0, module

    level = len(package_parts) - common_length + 1
    suffix = target_parts[common_length:]
    return level, ".".join(suffix) if suffix else None


def _build_folder_layout(
    py_files: list[Path],
    source_root: Path,
) -> tuple[dict[Path, Path], dict[str, str]]:
    used_names: set[str] = set()
    directory_name_map: dict[Path, str] = {}
    relative_output_paths: dict[Path, Path] = {}
    module_name_map: dict[str, str] = {}

    all_directories = sorted(
        {
            directory
            for py_file in py_files
            for directory in py_file.relative_to(source_root).parents
            if directory != Path(".")
        },
        key=lambda path: (len(path.parts), path.parts),
    )

    for directory in all_directories:
        directory_name_map[directory] = generate_identifier(used_names, length=MODULE_NAME_LENGTH)

    for py_file in py_files:
        relative_path = py_file.relative_to(source_root)

        output_parts: list[str] = []
        for depth, part in enumerate(relative_path.parts[:-1], start=1):
            original_directory = Path(*relative_path.parts[:depth])
            output_parts.append(directory_name_map[original_directory])

        if relative_path.name == "__init__.py" or relative_path.name in ENTRYPOINT_FILE_NAMES:
            output_file_name = relative_path.name
        else:
            output_file_name = f"{generate_identifier(used_names, length=MODULE_NAME_LENGTH)}.py"

        output_relative_path = Path(*output_parts, output_file_name)

        relative_output_paths[relative_path] = output_relative_path

        original_module_name = _module_name_from_relative_path(relative_path)
        output_module_name = _module_name_from_relative_path(output_relative_path)
        if original_module_name and output_module_name:
            module_name_map[original_module_name] = output_module_name

    return relative_output_paths, module_name_map


def _scope_kind(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return "function"
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return "function"
    raise TypeError(f"Unsupported scope node: {type(node)!r}")


def _scope_name(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Lambda):
        return "lambda"
    if isinstance(node, ast.ListComp):
        return "listcomp"
    if isinstance(node, ast.SetComp):
        return "setcomp"
    if isinstance(node, ast.DictComp):
        return "dictcomp"
    if isinstance(node, ast.GeneratorExp):
        return "genexpr"
    raise TypeError(f"Unsupported scope node: {type(node)!r}")


def _is_function_symbol(symbol: symtable.Symbol) -> bool:
    if not symbol.is_namespace():
        return False
    return all(namespace.get_type() == "function" for namespace in symbol.get_namespaces())


def _should_rename(table: symtable.SymbolTable, symbol: symtable.Symbol, name: str) -> bool:
    if not name.isidentifier():
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    if symbol.is_imported():
        return False
    if symbol.is_namespace() and not _is_function_symbol(symbol):
        return False
    if symbol.is_global() and not symbol.is_declared_global() and not symbol.is_local():
        return False
    if symbol.is_parameter():
        return True
    if symbol.is_local() and _is_function_symbol(symbol):
        return table.get_type() != "class"
    return symbol.is_local()


def _build_scope_table_map(
    tree: ast.AST,
    root_table: symtable.SymbolTable,
) -> dict[int, symtable.SymbolTable]:
    scope_map: dict[int, symtable.SymbolTable] = {id(tree): root_table}
    used_children: dict[int, set[int]] = {}

    def bind_scope(node: ast.AST, current_table: symtable.SymbolTable) -> symtable.SymbolTable | None:
        if not isinstance(node, SCOPE_NODE_TYPES):
            return None

        child_tables = current_table.get_children()
        used = used_children.setdefault(id(current_table), set())

        for index, child in enumerate(child_tables):
            if index in used:
                continue
            same_kind = child.get_type() == _scope_kind(node)
            same_name = child.get_name() == _scope_name(node)
            same_line = child.get_lineno() == getattr(node, "lineno", child.get_lineno())
            if same_kind and same_name and same_line:
                used.add(index)
                scope_map[id(node)] = child
                return child
        return None

    def walk(node: ast.AST, current_table: symtable.SymbolTable) -> None:
        next_table = bind_scope(node, current_table) or current_table
        for child in ast.iter_child_nodes(node):
            walk(child, next_table)

    for child in ast.iter_child_nodes(tree):
        walk(child, root_table)

    return scope_map


class VariableObfuscator(ast.NodeTransformer):
    def __init__(
        self,
        root_table: symtable.SymbolTable,
        scope_map: dict[int, symtable.SymbolTable],
    ) -> None:
        self.scope_map = scope_map
        self.used_names: set[str] = set()
        self.scope_stack: list[ScopeInfo] = [ScopeInfo(root_table, self._make_rename_map(root_table), None)]

    @property
    def current_scope(self) -> ScopeInfo:
        return self.scope_stack[-1]

    def _make_rename_map(self, table: symtable.SymbolTable) -> dict[str, str]:
        rename_map: dict[str, str] = {}
        for name in table.get_identifiers():
            symbol = table.lookup(name)
            if _should_rename(table, symbol, name):
                length = FUNCTION_NAME_LENGTH if _is_function_symbol(symbol) else VARIABLE_NAME_LENGTH
                rename_map[name] = generate_identifier(self.used_names, length=length)
        return rename_map

    def _lookup_module_mapping(self, name: str) -> str | None:
        return self.scope_stack[0].rename_map.get(name)

    def _lookup_enclosing_mapping(self, name: str, scope: ScopeInfo | None) -> str | None:
        current = scope
        while current is not None:
            if name in current.rename_map:
                return current.rename_map[name]
            current = current.parent
        return None

    def _resolve_name(self, name: str) -> str | None:
        scope = self.current_scope
        table = scope.table

        if table.get_type() == "module":
            return scope.rename_map.get(name)

        if name not in table.get_identifiers():
            return None

        symbol = table.lookup(name)
        if symbol.is_parameter() or symbol.is_local():
            return scope.rename_map.get(name)
        if symbol.is_nonlocal() or symbol.is_free():
            return self._lookup_enclosing_mapping(name, scope.parent)
        if symbol.is_declared_global() or symbol.is_global():
            return self._lookup_module_mapping(name)
        return None

    def _with_new_scope(self, node: ast.AST) -> ScopeInfo:
        table = self.scope_map[id(node)]
        scope = ScopeInfo(table, self._make_rename_map(table), self.current_scope)
        self.scope_stack.append(scope)
        return scope

    def _exit_scope(self) -> None:
        self.scope_stack.pop()

    def _visit_function_scope(self, node: FunctionLikeNode) -> FunctionLikeNode:
        node.name = self.current_scope.rename_map.get(node.name, node.name)
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        if node.returns:
            node.returns = self.visit(node.returns)
        for type_param in getattr(node, "type_params", []):
            self.visit(type_param)
        self._with_new_scope(node)
        node.args = self.visit(node.args)
        node.body = [self.visit(item) for item in node.body]
        self._exit_scope()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._visit_function_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._visit_function_scope(node)

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        self._with_new_scope(node)
        node.args = self.visit(node.args)
        node.body = self.visit(node.body)
        self._exit_scope()
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.bases = [self.visit(base) for base in node.bases]
        node.keywords = [self.visit(keyword_node) for keyword_node in node.keywords]
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        self._with_new_scope(node)
        node.body = [self.visit(item) for item in node.body]
        self._exit_scope()
        return node

    def visit_ListComp(self, node: ast.ListComp) -> ast.AST:
        return self._visit_comprehension_scope(node)

    def visit_SetComp(self, node: ast.SetComp) -> ast.AST:
        return self._visit_comprehension_scope(node)

    def visit_DictComp(self, node: ast.DictComp) -> ast.AST:
        return self._visit_comprehension_scope(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ast.AST:
        return self._visit_comprehension_scope(node)

    def _visit_comprehension_scope(self, node: ComprehensionNode) -> ComprehensionNode:
        generators = node.generators
        if not generators:
            return node

        generators[0].iter = self.visit(generators[0].iter)

        has_own_scope = id(node) in self.scope_map
        if has_own_scope:
            self._with_new_scope(node)
        generators[0].target = self.visit(generators[0].target)
        generators[0].ifs = [self.visit(item) for item in generators[0].ifs]

        for generator in generators[1:]:
            generator.iter = self.visit(generator.iter)
            generator.target = self.visit(generator.target)
            generator.ifs = [self.visit(item) for item in generator.ifs]

        if isinstance(node, ast.DictComp):
            node.key = self.visit(node.key)
            node.value = self.visit(node.value)
        else:
            node.elt = self.visit(node.elt)

        if has_own_scope:
            self._exit_scope()
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        replacement = self.current_scope.rename_map.get(node.arg)
        if replacement:
            node.arg = replacement
        if node.annotation:
            node.annotation = self.visit(node.annotation)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        replacement = self._resolve_name(node.id)
        if replacement:
            node.id = replacement
        return node

    def visit_Global(self, node: ast.Global) -> ast.AST:
        node.names = [self._lookup_module_mapping(name) or name for name in node.names]
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.AST:
        node.names = [self._lookup_enclosing_mapping(name, self.current_scope.parent) or name for name in node.names]
        return node


class LiteralObfuscator(ast.NodeTransformer):
    """Hide simple literals behind byte-based expressions."""

    def __init__(self) -> None:
        self._string_context: list[bool] = [False]

    def _push_string_context(self, enabled: bool) -> None:
        self._string_context.append(enabled)

    def _pop_string_context(self) -> None:
        self._string_context.pop()

    @property
    def _allow_string_obfuscation(self) -> bool:
        return self._string_context[-1]

    def _build_int_expression(self, value: int) -> ast.AST:
        if value == 0:
            payload = b"\x00"
            signed = False
        else:
            signed = value < 0
            length = max(1, (value.bit_length() + 8) // 8) if signed else max(1, (value.bit_length() + 7) // 8)
            payload = value.to_bytes(length, "big", signed=signed)

        return ast.Call(
            func=ast.Attribute(value=ast.Name(id="int", ctx=ast.Load()), attr="from_bytes", ctx=ast.Load()),
            args=[ast.Constant(value=payload), ast.Constant(value="big")],
            keywords=[ast.keyword(arg="signed", value=ast.Constant(value=signed))],
        )

    def _build_string_expression(self, value: str) -> ast.AST:
        payload = value.encode("utf-8")
        return ast.Call(
            func=ast.Attribute(value=ast.Constant(value=payload), attr="decode", ctx=ast.Load()),
            args=[],
            keywords=[],
        )

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        self._push_string_context(False)
        node.values = [self.visit(item) for item in node.values]
        self._pop_string_context()
        return node

    def visit_FormattedValue(self, node: ast.FormattedValue) -> ast.AST:
        self._push_string_context(False)
        node.value = self.visit(node.value)
        self._pop_string_context()
        if node.format_spec:
            node.format_spec = self.visit(node.format_spec)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool) or node.value is None or node.value is Ellipsis:
            return node
        if isinstance(node.value, int):
            return ast.copy_location(self._build_int_expression(node.value), node)
        if isinstance(node.value, str) and self._allow_string_obfuscation:
            return ast.copy_location(self._build_string_expression(node.value), node)
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        self._push_string_context(True)
        node.keys = [self.visit(item) if item is not None else None for item in node.keys]
        node.values = [self.visit(item) for item in node.values]
        self._pop_string_context()
        return node

    def visit_List(self, node: ast.List) -> ast.AST:
        self._push_string_context(True)
        node.elts = [self.visit(item) for item in node.elts]
        self._pop_string_context()
        return node

    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        self._push_string_context(True)
        node.elts = [self.visit(item) for item in node.elts]
        self._pop_string_context()
        return node

    def visit_Set(self, node: ast.Set) -> ast.AST:
        self._push_string_context(True)
        node.elts = [self.visit(item) for item in node.elts]
        self._pop_string_context()
        return node


class ModuleImportObfuscator(ast.NodeTransformer):
    """Rewrite local imports after folder-level module renaming."""

    def __init__(self, module_name_map: dict[str, str], current_module: str | None) -> None:
        self.module_name_map = module_name_map
        self.current_module = current_module

    def visit_Import(self, node: ast.Import) -> ast.AST:
        for alias in node.names:
            alias.name = self.module_name_map.get(alias.name, alias.name)
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST:
        absolute_module = _resolve_import_from_module(node.module, node.level, self.current_module)
        remapped_module = self.module_name_map.get(absolute_module) if absolute_module else None

        if remapped_module:
            if node.level > 0 and self.current_module is not None:
                node.level, node.module = _absolute_to_relative_import(remapped_module, self.current_module)
            else:
                node.level = 0
                node.module = remapped_module

        package_module = absolute_module
        for alias in node.names:
            if package_module is None:
                continue
            imported_module = f"{package_module}.{alias.name}"
            remapped_import = self.module_name_map.get(imported_module)
            if remapped_import:
                alias.name = remapped_import.rsplit(".", 1)[-1]

        return node

class BuiltinAliasObfuscator(ast.NodeTransformer):
    """Replace obvious builtin calls with obfuscated aliases."""

    CANDIDATES = {
        "dict",
        "enumerate",
        "len",
        "list",
        "max",
        "object",
        "print",
        "round",
        "set",
        "sum",
        "tuple",
    }

    def __init__(self) -> None:
        self.used_names: set[str] = set()
        self.aliases: dict[str, str] = {}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.CANDIDATES:
            alias = self.aliases.setdefault(
                node.id,
                generate_identifier(self.used_names, length=BUILTIN_ALIAS_LENGTH),
            )
            node.id = alias
        return node

    def build_alias_assignments(self) -> list[ast.Assign]:
        assignments: list[ast.Assign] = []
        for builtin_name, alias in sorted(self.aliases.items(), key=lambda item: item[1]):
            assignments.append(
                ast.Assign(
                    targets=[ast.Name(id=alias, ctx=ast.Store())],
                    value=ast.Name(id=builtin_name, ctx=ast.Load()),
                )
            )
        return assignments


_SIMPLE_BLOCK_PATTERNS = (
    re.compile(r"(?m)^(\s*def [^\n]+:\n)(\s+)(return [^\n]+)$"),
    re.compile(r"(?m)^(\s*def [^\n]+:\n)(\s+)(pass)$"),
    re.compile(r"(?m)^(\s*if [^\n]+:\n)(\s+)(return [^\n]+)$"),
    re.compile(r"(?m)^(\s*if [^\n]+:\n)(\s+)(pass)$"),
    re.compile(r"(?m)^(\s*for [^\n]+:\n)(\s+)(pass)$"),
)


def _minify_generated_source(source: str) -> str:
    compact = re.sub(r"\n{3,}", "\n\n", source).strip() + "\n"

    previous = None
    while previous != compact:
        previous = compact
        for pattern in _SIMPLE_BLOCK_PATTERNS:
            compact = pattern.sub(lambda match: f"{match.group(1).rstrip()} {match.group(3)}", compact)

    return compact


def obfuscate_source(
    source: str,
    filename: str = "<memory>",
    *,
    current_module: str | None = None,
    module_name_map: dict[str, str] | None = None,
) -> str:
    try:
        tree = ast.parse(source, filename=filename)
        symbol_table = symtable.symtable(source, filename, "exec")
    except SyntaxError as error:
        raise ObfuscatorError(str(error)) from error

    scope_map = _build_scope_table_map(tree, symbol_table)
    renamed = VariableObfuscator(symbol_table, scope_map).visit(tree)
    transformed = LiteralObfuscator().visit(renamed)
    if module_name_map:
        transformed = ModuleImportObfuscator(module_name_map, current_module).visit(transformed)
    builtin_aliaser = BuiltinAliasObfuscator()
    transformed = builtin_aliaser.visit(transformed)
    if isinstance(transformed, ast.Module):
        transformed.body = builtin_aliaser.build_alias_assignments() + transformed.body
    ast.fix_missing_locations(transformed)
    return _minify_generated_source(ast.unparse(transformed))


def _destination_for_file(path: Path, output_root: Path) -> Path:
    if output_root.suffix == ".py":
        return output_root
    return output_root / path.name


def obfuscate_path(path: str | Path, output_path: str | Path | None = None) -> list[ObfuscationResult]:
    source_path = Path(path).resolve()
    if not source_path.exists():
        raise ObfuscatorError(f"Path does not exist: {source_path}")

    if output_path is None:
        if source_path.is_file():
            output_root = source_path.with_name(f"{source_path.stem}.duck.py")
        else:
            output_root = source_path.with_name(f"{source_path.name}_duckified")
    else:
        output_root = Path(output_path).resolve()

    if source_path.is_file():
        if source_path.suffix != ".py":
            raise ObfuscatorError("Only .py files are supported.")
        output_root.parent.mkdir(parents=True, exist_ok=True)
        return [_obfuscate_single_file(source_path, output_root)]

    output_root.mkdir(parents=True, exist_ok=True)
    results: list[ObfuscationResult] = []
    py_files = sorted(source_path.rglob("*.py"))
    relative_output_paths, module_name_map = _build_folder_layout(py_files, source_path)

    for py_file in py_files:
        relative_path = py_file.relative_to(source_path)
        destination = output_root / relative_output_paths[relative_path]
        destination.parent.mkdir(parents=True, exist_ok=True)
        current_module = _module_name_from_relative_path(relative_path)
        results.append(
            _obfuscate_single_file(
                py_file,
                destination,
                current_module=current_module,
                module_name_map=module_name_map,
            )
        )
    return results


def _obfuscate_single_file(
    source_path: Path,
    output_path: Path,
    *,
    current_module: str | None = None,
    module_name_map: dict[str, str] | None = None,
) -> ObfuscationResult:
    original = source_path.read_text(encoding="utf-8")
    obfuscated = obfuscate_source(
        original,
        filename=str(source_path),
        current_module=current_module,
        module_name_map=module_name_map,
    )
    output_path.write_text(obfuscated, encoding="utf-8")
    return ObfuscationResult(source_path=source_path, output_path=output_path, changed=original != obfuscated)
