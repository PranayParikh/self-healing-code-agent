# Phase 3 — Multi-File Healing Orchestrator (LangGraph)
 
Combines the earlier phases into one system. Phase 1 healed a single file in a Docker sandbox. Phase 2.1 built a dependency graph of a repository. Phase 3 uses that graph to heal several files in dependency order, inside a single LangGraph state machine, and finishes with a whole-repo test run.
 
## Architecture
 
```
START
  │
  ▼
┌───────────┐  file queued    ┌──────────┐   failed, retries left   ┌─────────┐
│ architect │ ──────────────▶ │  tester  │ ───────────────────────▶ │  coder  │
└───────────┘                 └──────────┘                          └────┬────┘
  ▲   │ no files left              │                                    │
  │   ▼                            │ passed, or out of retries          │
  │ ┌─────────────┐                │                                    │
  │ │ final_check │                │          (patched file re-tested)  │
  │ └──────┬──────┘                │◀───────────────────────────────────┘
  │        ▼                       │
  │       END                      │
  └────────────────────────────────┘
          (next file)
```
 
- **Architect** (no LLM call): builds the dependency graph with the Phase 2.1 parser, reverses the topological sort so dependencies are healed first, and keeps only files that have a matching `test_<name>.py`. Skipped files are recorded with a reason. Each time it runs, it records the finished file's outcome, loads the next file and its test, and loads the source of the files it imports as read-only context.
- **Tester**: writes the current code to disk and runs only that file's test in the Docker sandbox (network disabled, memory capped).
- **Coder**: asks the LLM for a patch, strips markdown fences, and writes the result only if it parses.
- **Final check**: after the last file, runs every test in the folder once and reports one pass/fail result.
The Architect is deterministic. The ordering comes from a graph algorithm, so an LLM call there would add nothing.
 
## Run it
 
```bash
cd phase3
python3 orchestrator.py        # Docker Desktop must be running
```
 
The script uses relative paths, so run it from `phase3/`.
 
## What went wrong, and what each fix taught
 
The toy repo has three files: `basic_test.py` (account classes), `report.py` (imports from it), and `main.py` (entry point, no test, so it is skipped). Bugs were planted one at a time, and every result was checked by reading the diff, not just the pass/fail flag.
 
| Run | Planted bug | Setup | Attempts (`report.py`) | What the diff showed |
|---|---|---|---|---|
| 1 | `calculate_growth()` replaced with `principal` | whole-folder tests, no dependency context | 2 (and 5 failed attempts on `basic_test.py`) | `report.py` hardcoded `principal * 1.05`; an unrelated function was added to the correct `basic_test.py` |
| 2 | same | per-file tests, no dependency context | 4 | hardcoded a 5% rate, with a comment admitting the assumption |
| 3 | same | per-file tests + dependency context | 1 | restored the call to `calculate_growth()` |
| 4, 5 | `account.balance` in `print_report` (crash) | with context | 1 each | correct fix; `print_growth_report` was also rewritten with a helper variable, which nobody asked for. Both runs produced identical files |
| 6 | closing quote deleted from an f-string (syntax error) | with context + fallback scan | 1 | exact original line restored |
| 7 | `MAX_RETRIES = 0`, `principal` bug | forced failure | 0 | file reported `passed: False`, final check reported 3 of 4 tests passing |
 
### Findings
 
1. **Whole-folder pass/fail leaked failures across files.** While healing `basic_test.py`, `report.py` was still broken, so the whole run was red. The Coder spent five attempts on a bug that wasn't in its file. Fix: run only the matching test for each file.
2. **Tests can't catch scope creep.** In run 1 the Coder added `print_growth_report` to a file that was already correct, and the suite stayed green. In runs 4 and 5 it refactored an unrelated function. Both are cases for a Reviewer step that checks the diff's scope.
3. **Passing is not the same as correct.** The hardcoded rates in runs 1 and 2 satisfied the test, but would silently go wrong if `RATE` ever changed. The Coder couldn't see `basic_test.py`, so it had to reverse-engineer the formula from the expected string.
4. **Dependency context changed the fix.** After the Architect passed the Coder the source of the files it imports (with rules to call them and not copy their logic), the correct fix appeared in run 3. This is the first place the Phase 2.1 graph changes what the Coder produces, not just the order of work.
5. **Planning crashed on a file that doesn't parse.** The Architect parses every file to find imports, so a syntax error in `report.py` stopped the run before anything was healed. A naive `try/except` would have dropped the dependency edge and removed the context fix. Instead, `build_graph.py` falls back to a regex scan of import lines when `ast.parse` fails. The motivating case is a Python 2→3 migration, where files don't parse under Python 3's `ast`. That case is untested here.
## Limitations
 
- **Small sample.** The runs above are one toy repo and a handful of bugs. Output was close to deterministic (runs 4 and 5 were byte-identical), so repeating a bug adds little evidence. Context is shown to help in run 3; that it generalizes is not shown.
- **No control run for the crash bug.** Run 4 and 5 were correct, but they were not tested without dependency context, so the context is not proven to be why.
- **The fallback is a heuristic.** The regex can match an `import` line inside a docstring and ignores anything unusual.
- **Attempt count is not a quality signal.** A fix on attempt 4 can be wrong, and one on attempt 1 can be right. Results record pass/fail and attempts only.
- **`main.py` is not healed.** It has no test, so it is skipped and reported. A smoke test would be the natural way to cover it.
- **The final check adds little in this repo.** Each file's test already covers its own behavior, so cross-file regressions are unlikely here. It matters more when earlier files' tests import later ones. It also surfaces any file that ran out of retries.
- **Patched files lose their trailing newline,** a side effect of `.strip()` on the LLM output.
## Stack
 
Python 3.12 (host), LangGraph, NetworkX, Docker SDK, OpenAI API (`gpt-4o`), pytest + pytest-json-report.
 
## Next steps
 
- Phase 4: LangSmith tracing, Pass@k metrics from a larger set of planted bugs, more test repositories, and a demo recording.
- Optional: a Reviewer node that rejects patches whose diff touches code outside the failing function.
- Deferred, not dropped: Phase 2.2 (Neo4j and hybrid search).
 