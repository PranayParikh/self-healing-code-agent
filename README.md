# Self-Healing Code Sandbox — Phase 1

A minimal autonomous debugging loop: given a broken Python file and its test suite, the system runs the tests inside an isolated Docker container, and if they fail, feeds the structured error back to an LLM to generate a fix — repeating until the tests pass or a retry limit is hit.

This is Phase 1 of a larger planned system (AST-based repo-wide migration, multi-agent orchestration via LangGraph, observability/evals). Phase 1 focuses on proving the core self-healing loop works reliably across varied bug types, with real sandboxing safety.

## How it works

```
 broken target.py + test_target.py
              │
              ▼
   ┌─────────────────────────┐
   │  Docker sandbox (isolated,│
   │  network disabled,        │
   │  memory-capped)           │
   │  runs: pytest --json-report
   └─────────────┬─────────────┘
                 │
        pass? ───┼─── fail?
         │                 │
         ▼                 ▼
      done            structured error
                       summary extracted
                              │
                              ▼
                    LLM generates a fix
                    (full corrected file,
                     no markdown fences)
                              │
                              ▼
                 ast.parse() validity check
                              │
                    valid?           invalid?
                       │                 │
                       ▼                 ▼
              overwrite target.py   skip write,
              and retry              retry
                                   (up to MAX_RETRIES)
```

## Architecture decisions

- **Isolated execution**: containers run with `network_disabled=True` and a 256MB memory cap. LLM-generated code is never trusted to run on the host.
- **Structured failure data, not raw stdout**: uses `pytest-json-report` inside the container instead of regex-parsing pytest's text output, which is fragile and breaks across pytest versions.
- **Validation before trust**: every LLM response is checked with `ast.parse()` before it's allowed to overwrite the target file. If the LLM returns malformed output, the original file is left untouched and the loop retries.
- **Full attempt logging**: every run writes `run_results.json`, recording pass/fail and patch validity per attempt — the seed data for later Pass@k metrics.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install docker openai

docker build -t self-healing-sandbox .
export OPENAI_API_KEY=your_key_here   # or add to ~/.zshrc
```

## Usage

```bash
python heal.py
```

Runs the loop against every case folder in `cases/`, printing live pass/fail status per attempt and writing a final summary to `run_results.json`.

To re-run against the original broken files:
```bash
git checkout <original-commit-hash> -- cases/
```

## Test cases

Four hand-written bug categories, chosen to exercise different failure modes rather than one hardcoded bug:

| Case | Bug type | Failure signature |
|---|---|---|
| `case1_syntax` | Python 2 → 3 syntax (`print` statement) | `SyntaxError` at parse time |
| `case2_type` | Type mismatch (int + str) | `TypeError` at runtime |
| `case3_logic` | Off-by-one / wrong comparison operator | `AssertionError`, no crash — wrong output |
| `case4_import` | Typo'd module import | `ModuleNotFoundError` |
| `case5_hard` | Two interacting bugs: mismatched variable (sum over unfiltered list, divide by filtered length) + incomplete conditional logic (discount only converted to a fraction in one branch, then applied as subtraction instead of multiplication) | Some tests pass, others fail — no crash, partial correctness |

## Results

```
case1_syntax: PASS (1 attempt)
case2_type:   PASS (1 attempt)
case3_logic:  PASS (1 attempt)
case4_import: PASS (1 attempt)
case5_hard:   PASS (2 attempts)
```

## A real bug found and fixed

Initial runs showed `case1_syntax` failing all 5 retry attempts. Inspecting `run_results.json` showed every attempt flagged `invalid_patch: true` — the LLM's fixes were being rejected by the `ast.parse()` safety check on every single try, meaning the original broken file was never actually overwritten.

Root cause: despite an explicit instruction not to, the model was wrapping its response in markdown code fences (` ```python ... ``` `), which `ast.parse()` correctly rejected as invalid Python syntax.

Fix: added a `clean_llm_output()` step that strips leading/trailing markdown fences before validation:

```python
def clean_llm_output(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
```

After the fix, all four cases passed, most in a single attempt.

This is a good illustration of why the `ast.parse()` validation guard matters: it silently protected the original file from being overwritten with garbage across five failed attempts, rather than corrupting it — the failure was loud and diagnosable from the logs instead of a silent bad state.

## A second example: genuine iterative debugging

`case5_hard` was designed with two independent bugs in the same file (a mismatched-variable bug and an incompletely-handled conditional), specifically to see whether the loop could handle a fix that doesn't succeed on the first try for real logical reasons, not just a formatting issue.

The attempt log shows exactly that:
```json
"case5_hard": {
    "passed": true,
    "attempts": [
        { "attempt": 1, "passed": false, "patched": true },
        { "attempt": 2, "passed": true }
    ]
}
```

Attempt 1 produced a syntactically valid patch that ran successfully but only fixed one of the two bugs — some tests still failed. The failure summary from that attempt was fed back in, and attempt 2 produced a fully correct fix. This is the loop doing what it's meant to do: using concrete test feedback to converge on a correct solution across multiple genuine iterations, rather than getting it right by luck on the first pass.

## Stack

- Python 3.11 (sandbox) / 3.12 (host)
- Docker SDK for Python
- `pytest` + `pytest-json-report`
- OpenAI API (`gpt-4o`)

## Next steps (Phase 2+)

- AST parsing across a multi-file repository (dependency graph via `ast` / `tree-sitter`)
- Multi-agent orchestration (Architect / Coder / Reviewer) via LangGraph
- Observability (LangSmith tracing) and Pass@k evaluation across a larger, harder case set
