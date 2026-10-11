import ast
import difflib
import json
import os

from bugs import BUGS

BASELINE = "sample_repo"
NO_CONTEXT = os.environ.get("NO_CONTEXT") == "1"
RUN = os.environ.get("RUN", "")
SUFFIX = ("_nocontext" if NO_CONTEXT else "") + (f"_{RUN}" if RUN else "")
RUNS_DIR = "runs" + SUFFIX


def read(path):
    with open(path) as f:
        return f.read().strip()


def numbers(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)}


def attr_names(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def defined_names(source):
    """Names that can legitimately appear after a dot: functions, methods, classes,
    attributes assigned via self.x = ..., and names assigned directly in a class body.
    Plain module-level or local variables are deliberately excluded."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
            names.add(n.attr)
        if isinstance(n, ast.ClassDef):
            for stmt in n.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            names.add(t.id)
    return names


def changed_lines(a, b):
    diff = difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
    return sum(1 for line in diff
               if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))


def analyze():
    results_file = f"bug_results{SUFFIX}.json"
    with open(results_file) as f:
        records = json.load(f)
    if any(r.get("no_context", False) != NO_CONTEXT for r in records):
        raise SystemExit(f"{results_file} does not match the NO_CONTEXT setting")

    bugs = {b["id"]: b for b in BUGS}
    py_files = sorted(n for n in os.listdir(BASELINE) if n.endswith(".py"))

    defined = set()
    for name in py_files:
        defined |= defined_names(read(os.path.join(BASELINE, name)))

    rows = []
    skipped = []
    for r in records:
        if r["status"] != "ok" or r["id"] not in bugs:
            skipped.append((r["id"], r["status"]))
            continue
        broken = {e[0] for e in bugs[r["id"]]["edits"]}
        run_dir = os.path.join(RUNS_DIR, r["id"])

        touched_unbroken = []
        new_numbers = {}
        invented = {}
        restored = True
        lines = 0
        for name in py_files:
            base = read(os.path.join(BASELINE, name))
            fixed = read(os.path.join(run_dir, name))
            if name in broken:
                lines += changed_lines(base, fixed)
                if fixed != base:
                    restored = False
            elif fixed != base:
                touched_unbroken.append(name)
            extra = numbers(fixed) - numbers(base)
            if extra:
                new_numbers[name] = sorted(extra)
            new_attrs = (attr_names(fixed) - attr_names(base)) - defined
            if new_attrs:
                invented[name] = sorted(new_attrs)

        rows.append({
            "id": r["id"],
            "type": r["type"],
            "passed": all(v["passed"] for v in r["results"].values()) and r["final_passed"],
            "attempts": max((v["attempts"] for v in r["results"].values()), default=0),
            "seconds": r["seconds"],
            "restored_exactly": restored,
            "lines_changed_vs_baseline": lines,
            "touched_unbroken_files": touched_unbroken,
            "new_numeric_constants": new_numbers,
            "invented_names": invented,
        })

    n = len(rows)
    if n == 0:
        print("no scored bugs; not scored:", skipped)
        return

    print(f"{'bug':18} {'type':16} pass att  sec  exact  diff  extra-files  new-numbers  invented-names")
    for x in rows:
        print(f"{x['id']:18} {x['type']:16} {str(x['passed']):5} {x['attempts']:3} "
              f"{x['seconds']:5} {str(x['restored_exactly']):6} {x['lines_changed_vs_baseline']:4}  "
              f"{x['touched_unbroken_files']}  {x['new_numeric_constants']}  {x['invented_names']}")

    print(f"\nbugs scored: {n}   not scored: {skipped}")
    for k in (1, 2, 3, 5):
        hit = sum(1 for x in rows if x["passed"] and x["attempts"] <= k)
        print(f"Pass@{k}: {hit}/{n}")
    print("restored exactly:", sum(x["restored_exactly"] for x in rows), "/", n)
    print("touched an unbroken file:", sum(bool(x["touched_unbroken_files"]) for x in rows), "/", n)
    print("introduced new numeric constants:", sum(bool(x["new_numeric_constants"]) for x in rows), "/", n)
    print("invented attribute names:", sum(bool(x["invented_names"]) for x in rows), "/", n)
    print("mean seconds:", round(sum(x["seconds"] for x in rows) / n, 2))

    metrics_file = f"metrics{SUFFIX}.json"
    with open(metrics_file, "w") as f:
        json.dump(rows, f, indent=2)
    print("wrote", metrics_file)


if __name__ == "__main__":
    analyze()