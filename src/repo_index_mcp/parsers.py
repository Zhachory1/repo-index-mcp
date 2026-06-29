from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TREE_SITTER_LANGUAGE_BY_REPO_LANGUAGE = {
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "java": "java",
    "rust": "rust",
    "cpp": "cpp",
    "c": "c",
    "sql": "sql",
}

TREE_SITTER_LANGUAGE_BY_PATH_SUFFIX = {
    ".tsx": "tsx",
    ".jsx": "javascript",
}

SYMBOL_KIND_BY_NODE = {
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    "method_declaration": "method",
    "method_definition": "method",
    "constructor_declaration": "method",
    "variable_declarator": "function",
    "class_declaration": "class",
    "class_specifier": "class",
    "interface_declaration": "interface",
    "interface_item": "interface",
    "struct_item": "struct",
    "struct_specifier": "struct",
    "enum_item": "enum",
    "enum_declaration": "enum",
    "enum_specifier": "enum",
    "type_alias_declaration": "type",
    "type_declaration": "type",
    "trait_item": "interface",
    "create_table": "table",
    "create_view": "view",
    "create_function": "function",
    "create_procedure": "function",
}

NAME_NODE_KINDS = {
    "identifier",
    "field_identifier",
    "type_identifier",
    "property_identifier",
    "shorthand_property_identifier",
    "object_reference",
}

SKIP_NAMES = {
    "function",
    "class",
    "interface",
    "type",
    "func",
    "fn",
    "struct",
    "enum",
    "create",
    "table",
    "view",
}

FUNCTION_VALUE_NODE_KINDS = {
    "arrow_function",
    "function_expression",
    "function",
}


@dataclass(frozen=True)
class ParsedSymbol:
    name: str
    kind: str
    start_line: int
    end_line: int
    symbol_line: int


def parser_language_for(*, repo_language: str, path: str) -> str | None:
    for suffix, parser_language in TREE_SITTER_LANGUAGE_BY_PATH_SUFFIX.items():
        if path.endswith(suffix):
            return parser_language
    return TREE_SITTER_LANGUAGE_BY_REPO_LANGUAGE.get(repo_language)


def parse_symbols(*, language: str, path: str, content: str) -> list[ParsedSymbol]:
    parser_language = parser_language_for(repo_language=language, path=path)
    if parser_language is None:
        return []

    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(parser_language)
        source = content.encode("utf-8")
        try:
            tree = parser.parse(source)
        except TypeError:
            tree = parser.parse(content)
        root = node_attr(tree, "root_node")
    except Exception:
        return []

    symbols: list[ParsedSymbol] = []
    seen: set[tuple[str, int, int]] = set()
    for node in walk(root):
        kind = symbol_kind(node)
        if kind is None:
            continue
        name = symbol_name(node, source)
        if not name:
            continue
        start_line = point_row(node_attr(node, "start_position", "start_point")) + 1
        end_line = max(start_line, point_row(node_attr(node, "end_position", "end_point")) + 1)
        key = (name, start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        symbols.append(
            ParsedSymbol(
                name=name,
                kind=kind,
                start_line=start_line,
                end_line=end_line,
                symbol_line=start_line,
            )
        )
    symbols.sort(key=lambda item: (item.start_line, item.name))
    return symbols


def symbol_kind(node: Any) -> str | None:
    kind = node_kind(node)
    if kind == "variable_declarator" and not has_function_value(node):
        return None
    return SYMBOL_KIND_BY_NODE.get(kind)


def has_function_value(node: Any) -> bool:
    return any(node_kind(child) in FUNCTION_VALUE_NODE_KINDS for child in walk(node))


def walk(node: Any):  # type: ignore[no-untyped-def]
    yield node
    for index in range(child_count(node)):
        child = node_child(node, index)
        if child is not None:
            yield from walk(child)


def symbol_name(node: Any, source: bytes) -> str | None:
    by_field = call_node_method(node, "child_by_field_name", "name")
    if by_field is not None:
        name = node_text(by_field, source)
        if valid_name(name):
            return clean_name(name)

    special = special_name_node(node)
    if special is not None:
        name = node_text(special, source)
        if valid_name(name):
            return clean_name(name)

    candidate = first_name_node(node, source)
    if candidate is None:
        return None
    name = node_text(candidate, source)
    return clean_name(name) if valid_name(name) else None


def special_name_node(node: Any) -> Any | None:
    kind = node_kind(node)
    if kind == "function_definition":
        declarator = first_descendant_of_kind(node, {"function_declarator"})
        if declarator is not None:
            return first_descendant_of_kind(declarator, NAME_NODE_KINDS)
    if kind == "variable_declarator":
        return first_direct_child_of_kind(node, NAME_NODE_KINDS)
    return None


def first_name_node(node: Any, source: bytes) -> Any | None:
    for child in walk(node):
        if node_kind(child) not in NAME_NODE_KINDS:
            continue
        text = node_text(child, source)
        if valid_name(text):
            return child
    return None


def first_descendant_of_kind(node: Any, kinds: set[str]) -> Any | None:
    for child in walk(node):
        if child is not node and node_kind(child) in kinds:
            return child
    return None


def first_direct_child_of_kind(node: Any, kinds: set[str]) -> Any | None:
    for index in range(child_count(node)):
        child = node_child(node, index)
        if child is not None and node_kind(child) in kinds:
            return child
    return None


def node_text(node: Any, source: bytes) -> str:
    start = int(node_attr(node, "start_byte"))
    end = int(node_attr(node, "end_byte"))
    return source[start:end].decode("utf-8", errors="ignore")


def node_kind(node: Any) -> str:
    value = getattr(node, "type", None)
    if value is not None:
        return value
    return str(node_attr(node, "kind"))


def child_count(node: Any) -> int:
    return int(node_attr(node, "child_count"))


def node_child(node: Any, index: int) -> Any | None:
    return call_node_method(node, "child", index)


def node_attr(node: Any, *names: str) -> Any:
    for name in names:
        value = getattr(node, name, None)
        if value is None:
            continue
        return value() if callable(value) else value
    raise AttributeError(f"node has none of: {', '.join(names)}")


def call_node_method(node: Any, name: str, *args: Any) -> Any | None:
    method = getattr(node, name, None)
    if method is None:
        return None
    return method(*args)


def point_row(point: Any) -> int:
    row = getattr(point, "row", None)
    if row is not None:
        return int(row)
    return int(point[0])


def valid_name(name: str) -> bool:
    stripped = clean_name(name)
    if not stripped or stripped.lower() in SKIP_NAMES:
        return False
    return not any(character.isspace() for character in stripped)


def clean_name(name: str) -> str:
    return name.strip().strip('`"[]')
