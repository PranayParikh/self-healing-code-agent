# Phase 2.1 — AST-Based Dependency Graph (NetworkX)

Parses a small multi-file Python repository using the `ast` module, extracts structural information from each file (imports, functions, classes, calls), and builds a directed dependency graph showing which files depend on which — using NetworkX.

This is Phase 2.1 of the larger Self-Healing Code Sandbox project. Phase 1 fixed one file at a time; Phase 2.1 lays the groundwork for reasoning about a *whole repository* — a prerequisite for any future multi-file, dependency-aware migration or refactoring logic (Phase 3+).

## How it works

```
sample_repo/*.py
       │
       ▼
┌─────────────────────────────┐
│  ast_explorer.py             │
│  parser(path) →               │
│  ast.parse() + ast.walk()     │
│  extracts per file:           │
│    Imports, Function,         │
│    Class, Calls               │
└──────────────┬────────────────┘
               │  (called once per file)
               ▼
┌─────────────────────────────┐
│  build_graph.py               │
│  Pass 1: add every file        │
│          as a graph node       │
│  Pass 2: for each file's       │
│          imports, add a        │
│          directed edge if      │
│          the import matches    │
│          a known local file    │
└──────────────┬────────────────┘
               │
               ▼
      NetworkX DiGraph
   (nodes = files, edges = "imports")
```

## Design decisions

- **`ast.parse()` + `ast.walk()`** over regex or string matching — code structure needs to be understood grammatically (a function *definition* vs. a function *call* vs. a variable named the same thing are different AST node types), not guessed from text patterns.
- **One `parser(path)` function, called once per file** — returns a structured dictionary rather than printing, so results can be collected and reused. Each category is a list of small dictionaries (e.g. `{"name": ..., "lineno": ..., "args": [...]}`) rather than flat parallel lists, so related details stay bundled together per function/class/import.
- **Imports distinguish `import` vs `from_import`**, and calls distinguish `function_call` vs `method_call` (`ast.Name` vs `ast.Attribute`) — these are genuinely different AST shapes, and collapsing them into one undifferentiated bucket would lose information needed later (e.g. resolving which file a `from X import Y` statement actually depends on).
- **Two-pass graph construction, not one.** Pass 1 adds every file as a node; Pass 2 adds edges. Doing this in a single combined pass risks processing a file's imports before the file it depends on has been added as a node — while NetworkX's `add_edge()` would silently auto-create the missing node anyway, doing it in two explicit passes keeps the logic easier to reason about: by the time edges are added, every node's existence is guaranteed and intentional, not an accidental side effect.
- **Directed graph (`DiGraph`), not undirected.** "A imports B" is not symmetric — B does not import A just because A imports B. A directed edge captures this correctly; an undirected graph would lose the direction of dependency entirely.

## The toy repository

`sample_repo/` is a deliberately hand-written 3-file Python package, designed to have a known, real, non-trivial dependency chain:

- **`basic_test.py`** — defines `calculate_interest()`, `BankAccount`, and `SavingsAccount(BankAccount)` (tests inheritance detection). No local dependencies — only imports `datetime` and `math` (both external, not part of the graph).
- **`report.py`** — imports from `basic_test.py`; defines `print_report()` and `print_growth_report()` (the latter calls a *method* on the object passed in, testing method-call detection separately from direct function calls).
- **`main.py`** — imports from both `basic_test.py` and `report.py`; actually instantiates a `SavingsAccount` and calls both report functions. Verified to run correctly end-to-end (not just parseable — genuinely correct Python).

This gives a real 3-node, 3-edge dependency chain to validate the parser and graph-builder against, with a known ground truth to check output against.

## Results

```
Nodes: ['main.py', 'report.py', 'basic_test.py']
Edges: [('main.py', 'basic_test.py'), ('main.py', 'report.py'), ('report.py', 'basic_test.py')]

Is DAG: True
Processing order (topological sort): ['main.py', 'report.py', 'basic_test.py']
```

The topological sort confirms the graph is a valid DAG (no circular imports) and produces a dependency-respecting order: `main.py` first (nothing depends on it), `basic_test.py` last (everything depends on it, directly or transitively). In a real migration tool, refactoring in *reverse* topological order — `basic_test.py` first, `main.py` last — would be the safer direction: fix low-level dependencies before the code that relies on them.

## A subtlety worth noting

Class instantiation (`SavingsAccount(name, balance)`) is indistinguishable, at the AST level, from a plain function call — both are `ast.Call` nodes wrapping an `ast.Name`. Python doesn't syntactically differentiate "calling a class to create an object" from "calling a function," since both ultimately just invoke a callable. The current parser correctly captures this as a `function_call`, but a more complete implementation would need to check whether the called name resolves to a known class (from the `Class` list) to relabel it as an instantiation. Not required for graph-building (which only cares about imports), but worth knowing as a real limitation of `Calls` data if it's used for anything beyond that.

## Why NetworkX, not Neo4j

The original project roadmap specifies Neo4j for the dependency graph. For this scope — a small, in-memory, single-run analysis — NetworkX is sufficient and considerably simpler: no separate database service to run, no query language to learn, and every operation needed (edge lookup, topological sort, cycle detection) is a single function call on an in-memory graph object.

Neo4j's actual advantages — persistence across runs, Cypher queries for complex multi-hop questions, and handling graphs too large to hold in memory — only pay off at a scale this toy project doesn't reach. Migrating to Neo4j is treated as deliberate future work (**Phase 2.2**, deferred, not abandoned): the natural trigger to revisit it would be extending this to a real, large-scale repository where persistence and query complexity actually matter, rather than building it speculatively now.

## Stack

- Python 3.12 (host)
- `ast` (standard library)
- NetworkX

## Next steps

- **Phase 2.2 (deferred)**: migrate the graph to Neo4j; add hybrid dense-embedding + BM25 search for conceptual (not just structural) code search.
- **Phase 3**: multi-agent orchestration (Architect / Coder / Reviewer agents) via LangGraph, using this dependency graph to plan a safe, dependency-aware modification order across multiple files.