import json
import os
import shutil
import time

from bugs import BUGS
from heal import run_tests_in_sandbox
from orchestrator import run_graph

BASELINE = "sample_repo"
NO_CONTEXT = os.environ.get("NO_CONTEXT") == "1"
RUN = os.environ.get("RUN", "")
SUFFIX = ("_nocontext" if NO_CONTEXT else "") + (f"_{RUN}" if RUN else "")
RUNS_DIR = "runs" + SUFFIX


def apply_bug(repo_dir, bug):
    for file, find, replace in bug["edits"]:
        path = os.path.join(repo_dir, file)
        with open(path) as f:
            text = f.read()
        if text.count(find) != 1:
            raise ValueError(f"{bug['id']}: expected 1 match for {find!r} in {file}, found {text.count(find)}")
        with open(path, "w") as f:
            f.write(text.replace(find, replace))


def run_one(bug):
    repo_dir = os.path.join(RUNS_DIR, bug["id"])
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    shutil.copytree(BASELINE, repo_dir, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))

    record = {"id": bug["id"], "type": bug["type"], "no_context": NO_CONTEXT, "run": RUN}
    try:
        apply_bug(repo_dir, bug)
        still_passes, _, _ = run_tests_in_sandbox(repo_dir)
        if still_passes:
            record["status"] = "inert"          # the bug broke no test
            return record
        start = time.time()
        final = run_graph(repo_dir)
        record["seconds"] = round(time.time() - start, 2)
        record["status"] = "ok"
        record["results"] = final["result"]
        record["final_passed"] = final["final_passed"]
    except Exception as e:
        record["status"] = "error"
        record["error"] = str(e)
    return record


def main():
    ok, _, _ = run_tests_in_sandbox(BASELINE)
    if not ok:
        raise SystemExit("baseline sample_repo fails its own tests; fix that first")
    os.makedirs(RUNS_DIR, exist_ok=True)

    results = []
    for bug in BUGS:
        print(f"running {bug['id']} ...")
        record = run_one(bug)
        print("  ->", record["status"], record.get("results", ""))
        results.append(record)

    out_file = f"bug_results{SUFFIX}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"wrote {out_file}")


if __name__ == "__main__":
    main()