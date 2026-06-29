import pytest

from repo_index_mcp.chunking import LineChunker
from repo_index_mcp.parsers import parse_symbols

pytest.importorskip("tree_sitter_language_pack")


@pytest.mark.parametrize(
    ("path", "content", "symbol"),
    [
        ("app.ts", "export function retryRequest() { return true; }\n", "retryRequest"),
        ("app.ts", "export const retryRequest = () => true;\n", "retryRequest"),
        ("app.tsx", "export function RetryButton() { return <button />; }\n", "RetryButton"),
        ("app.go", "package main\nfunc RetryRequest() bool { return true }\n", "RetryRequest"),
        ("App.java", "class RetryService { void retryRequest() {} }\n", "RetryService"),
        ("app.rs", "fn retry_request() -> bool { true }\n", "retry_request"),
        ("app.cpp", "int retry_request() { return 1; }\n", "retry_request"),
        ("app.cpp", "Result retry_request() { return Result{}; }\n", "retry_request"),
        ("schema.sql", "CREATE TABLE retry_events (id INT);\n", "retry_events"),
    ],
)
def test_tree_sitter_symbols_are_parser_backed(path: str, content: str, symbol: str) -> None:
    chunks = LineChunker().chunk_file(
        repo_id="repo",
        repo_path="/repo",
        path=path,
        content=content,
    )

    parser_symbols = [chunk for chunk in chunks if chunk.symbol_confidence == "parser"]

    assert symbol in {chunk.symbol_name for chunk in parser_symbols}


@pytest.mark.parametrize(
    ("language", "path", "content", "symbol"),
    [
        (
            "typescript",
            "app.ts",
            "export function retryRequest() { return true; }\n",
            "retryRequest",
        ),
        (
            "go",
            "app.go",
            "package main\nfunc RetryRequest() bool { return true }\n",
            "RetryRequest",
        ),
        ("java", "App.java", "class RetryService { void retryRequest() {} }\n", "RetryService"),
        ("rust", "app.rs", "fn retry_request() -> bool { true }\n", "retry_request"),
        ("cpp", "app.cpp", "int retry_request() { return 1; }\n", "retry_request"),
        ("sql", "schema.sql", "CREATE TABLE retry_events (id INT);\n", "retry_events"),
    ],
)
def test_parse_symbols(language: str, path: str, content: str, symbol: str) -> None:
    symbols = parse_symbols(language=language, path=path, content=content)

    assert symbol in {item.name for item in symbols}


def test_same_line_class_and_method_symbols_are_preserved() -> None:
    chunks = LineChunker().chunk_file(
        repo_id="repo",
        repo_path="/repo",
        path="App.java",
        content="class RetryService { void retryRequest() {} }\n",
    )

    parser_symbols = [chunk.symbol_name for chunk in chunks if chunk.symbol_confidence == "parser"]

    assert "RetryService" in parser_symbols
    assert "retryRequest" in parser_symbols


def test_parser_failure_falls_back_to_line_chunk() -> None:
    chunks = LineChunker().chunk_file(
        repo_id="repo",
        repo_path="/repo",
        path="broken.ts",
        content="export function {\n",
    )

    assert chunks
    assert chunks[0].path == "broken.ts"
