# Language support

| Language / file type | Support |
| --- | --- |
| Python | stdlib AST parser-backed function/class/method symbol chunks. |
| JavaScript / TypeScript / TSX / JSX | Tree-sitter parser-backed functions/classes/interfaces/types plus line windows. |
| Go | Tree-sitter parser-backed functions/methods/types plus line windows. |
| Java | Tree-sitter parser-backed classes/interfaces/methods/enums plus line windows. |
| Rust | Tree-sitter parser-backed functions/structs/enums/traits plus line windows. |
| C / C++ | Tree-sitter parser-backed functions/classes/structs/enums plus line windows. |
| SQL | Tree-sitter parser-backed table/view/function/procedure symbols plus line windows. |
| C# / Ruby / shell and others | Regex-backed symbol hints plus line-window chunks. |
| Markdown / JSON / YAML / TOML | Line-window chunks. |
| Lockfiles, generated/vendor dirs, binaries, large blobs | Skipped by default. |
| Dirty working tree | Reported in status/results, not indexed. |

Quality varies by language. Add pilot misses to the golden eval set before changing ranking or parsers.
