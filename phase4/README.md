# Phase 4 — Tracing, a Bug Catalog, and a Controlled Experiment

Phase 3 built a LangGraph system that heals several files in dependency order. Phase 4 measures it. It adds LangSmith tracing, replaces hand-testing with an automated catalog of planted bugs, and runs a control experiment to test one claim from Phase 3: that giving the Coder the source of a file's dependencies is what makes its fixes correct.

## What was added

- **Tracing (LangSmith).** Set through environment variables, with the OpenAI client wrapped so each model call appears as its own run with the prompt, reply, and token count.
- **`repo_dir` in the graph state.** The orchestrator no longer reads a fixed folder. `run_graph(repo_dir)` takes the folder as an argument, so a runner can point it at any copy.
- **`bugs.py`.** Each bug is a record: an id, a type, and a list of exact find/replace edits. A bug with edits in two files gives a multi-file case.
- **`run_bugs.py`.** For each bug it copies the baseline repo into a throwaway folder, applies the edits, runs the healing graph, and records the outcome. It refuses to start if the baseline fails its own tests, errors if a find string doesn't match exactly once, and marks a bug `inert` if it breaks no test (so it can't be counted as a free fix).
- **`analyze.py`.** Scores each run: Pass@k, whether the broken files were restored exactly, whether any unbroken file changed, new numeric constants, and invented attribute names. Results files carry a `no_context` label, and the scorer refuses a file that doesn't match the mode, which was added after a mislabeled file mixed two conditions once.

## Where the time and tokens go (one traced run)

| Step | Time |
|---|---|
| `coder` (one model call) | 1.58s |
| `tester`, three visits | 0.40s, 0.29s, 0.52s |
| `final_check` | 0.23s |
| Whole run | 3.13s |

The model call is the largest single cost, and a sandbox run takes about 0.2 to 0.5s. One Coder call used 729 tokens (`gpt-4o`). A retry therefore costs roughly one model call plus one sandbox run. This is one run, so treat it as a rough figure.

## The experiment

Seven bugs in the toy repo: four in `basic_test.py` (no dependencies), two in `report.py` (which imports from `basic_test.py`), and one touching both. Types: wrong output, crash, syntax error, wrong attribute, multi-file.

Each bug was run in two conditions:

- **With context:** the Coder's prompt includes the source of the files the current file imports.
- **Control:** that section is removed. The prompt's two rules (don't copy dependency logic, don't hardcode values) stay in, so the control isolates the dependency source and nothing else.

| Condition | Runs | Pass@1 per run | Bugs that failed |
|---|---|---|---|
| With dependency source | 3 | 7/7, 7/7, 7/7 | none |
| Control | 3 scored | 4/7, 4/7, 4/7 | `report_principal`, `report_attr`, `two_files` |

A fourth control run, whose results file was overwritten by mistake, also printed 4/7 with the same failures. It is not scored here.

Detailed scoring exists for one run per condition:

| | With context | Control |
|---|---|---|
| Pass@1 / Pass@5 | 7/7 / 7/7 | 4/7 / 4/7 |
| Restored the original exactly | 5/7 | 2/7 |
| Touched an unbroken file | 0/7 | 0/7 |
| New numeric constants | 0/7 | 0/7 |
| Invented attribute names | 0/7 | 3/7 |
| Mean seconds per bug | 2.53 | 5.16 |

For the other repeat runs, only pass/fail and attempts per file were recorded.

### Findings

1. **Removing the dependency source dropped Pass@1 from 7/7 to 4/7, and it did so every time.** All three failing bugs are in `report.py`, the only file with a dependency. The four `basic_test.py` bugs passed in every run of both conditions, as they should, since their prompts are identical.
2. **More attempts did not help.** In the control, Pass@5 equals Pass@1. Each failing run used all 5 attempts and still failed. The Coder was missing information, and repeating the same guess doesn't supply it.
3. **The failures are invented identifiers.** The final code in the failing control runs used attributes that exist nowhere in the repo: `rate_of_interest`, `interest_rate`, `balance`, `get_balance`. The specific wrong name changes between runs, but the pattern doesn't: the Coder can't look up the real name (`principal`, or the method `calculate_growth()`), so it makes one up. In one run it also broke a working line, passing an argument to a method that takes none.
4. **Failure is expensive.** Failing runs took 8 to 10 seconds against about 2 to 3 for the others, because every retry is a model call plus a sandbox run.
5. **Test results alone could not show this.** The Phase 3 hardcoded-rate fixes also passed their tests. Reading diffs and adding an automated check for invented names is what made the difference visible.

## Lessons from building the measurements

- **The first version of the invented-name check missed a case.** It treated every name defined anywhere in the repo as legitimate, including a plain module variable named `balance` in `main.py`, so `account.balance()` wasn't flagged. It now counts only names that can actually follow a dot (methods, classes, attributes set on `self`, and class-level names). After the fix it flagged all three control failures and none of the with-context runs. A detector should be tested against a case it should catch.
- **A mislabeled results file mixed two conditions once,** which produced a table that looked plausible and was wrong. The `no_context` label and the scorer's refusal came from that.

## Limitations

- **Small catalog, one repo.** Seven bugs on a three-file toy repo, three of them in the single file with a dependency. The with-context side never failed, so the catalog can't show where the system is weak. Harder bugs would.
- **Zero variation across runs.** Identical results across three runs shows the effect is stable. It also means this catalog is not sensitive to model variance.
- **The control removes only the dependency source.** The prompt's rules stayed, so this doesn't show that the rules don't matter.
- **The invented-name check is a screen.** It looks at attribute names only. It would flag a legitimate new library method and miss other kinds of invention, so every flag needs a manual read.
- **Final state only.** The failing runs were scored on the code after the fifth attempt. I suspect each retry builds on the previous broken attempt, so errors compound, but that is untested. Saving the code after every attempt would check it, and a rollback to the best version so far is the natural fix to try.
- **Observed and not fixed:** one run's JSON report was missing, so the Coder received the raw log tail labeled `ContainerError`. Error text is also encoded twice before reaching the model, which turns line breaks into `\n`. Patched files lose their trailing newline from `.strip()`.
- **The baseline is not the original hand-written code.** `basic_test.py` carries `RATE = 5.0` and `/ 100`, the equivalent form the Coder wrote in the first Phase 3 healing test.
- **Prompt size grows with dependencies.** The full source of each dependency goes into every prompt. That's fine here, but on a larger repo it would need signatures or the imported names only.

## Run it

```bash
cd phase4
python3 run_bugs.py                       
NO_CONTEXT=1 python3 run_bugs.py          
python3 analyze.py                        
NO_CONTEXT=1 python3 analyze.py
```

`RUN=2` (or any tag) writes to separate results files and run folders, so repeats don't overwrite each other. Docker Desktop must be running, and the OpenAI and LangSmith keys must be set in the environment.

## Stack

Python 3.12 (host), LangGraph, LangSmith, NetworkX, Docker SDK, OpenAI API (`gpt-4o`), pytest and pytest-json-report.

## Next steps

- Harder bugs, especially two bugs in one dependent file and bugs that need both a dependency and a formula change.
- Record the code after each attempt, to test the compounding hypothesis, and try rolling back to the best version so far.
- A Reviewer check that rejects patches changing code outside the failing function.
- Deferred, not dropped: Phase 2.2 (Neo4j and hybrid search).