import docker
import json
import os
import ast
import openai

MAX_RETRIES = 5
IMAGE_NAME = "self-healing-sandbox"
client_llm = openai.OpenAI()  # reads OPENAI_API_KEY from env
docker_client = docker.from_env()


def run_tests_in_sandbox(case_dir):
    """Runs pytest inside a container mounted to case_dir. Returns (passed, report_dict, raw_logs)."""
    container = docker_client.containers.run(
        image=IMAGE_NAME,
        command=[
            "pytest", "test_target.py",
            "--json-report", "--json-report-file=/workspace/report.json",
            "-v"
        ],
        volumes={os.path.abspath(case_dir): {"bind": "/workspace", "mode": "rw"}},
        network_disabled=True,
        mem_limit="256m",
        detach=True,
    )
    try:
        result = container.wait(timeout=30)
        logs = container.logs().decode()
    except Exception as e:
        logs = f"Container timed out or errored: {e}"
        result = {"StatusCode": -1}
    finally:
        container.remove(force=True)

    report_path = os.path.join(case_dir, "report.json")
    report = None
    if os.path.exists(report_path):
        with open(report_path) as f:
            report = json.load(f)
        os.remove(report_path)

    passed = result.get("StatusCode") == 0
    return passed, report, logs


def extract_error_summary(report, raw_logs):
    if report is None:
        return {"error_type": "ContainerError", "message": raw_logs[-1000:]}

    failures = []
    for test in report.get("tests", []):
        if test.get("outcome") == "failed":
            call = test.get("call", {})
            failures.append({
                "test_name": test.get("nodeid"),
                "message": call.get("longrepr", "")[:1500],
            })
    return {"failures": failures}


def call_llm_for_patch(code, test_code, error_summary):
    prompt = f"""You are fixing a Python file so its tests pass.

CURRENT FILE (target.py):
{code}

TEST FILE (test_target.py) — do not modify, this defines the contract:
{test_code}

TEST FAILURE DETAILS:
{json.dumps(error_summary, indent=2)}

Return ONLY the complete corrected content of target.py.
No explanations, no markdown code fences, no commentary — just the raw Python file content."""

    response = client_llm.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def is_valid_python(code):
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def heal_case(case_dir):
    target_path = os.path.join(case_dir, "target.py")
    test_path = os.path.join(case_dir, "test_target.py")

    log = []
    for attempt in range(1, MAX_RETRIES + 1):
        passed, report, raw_logs = run_tests_in_sandbox(case_dir)
        log.append({"attempt": attempt, "passed": passed})

        if passed:
            print(f"  Passed on attempt {attempt}")
            return True, log

        print(f"  Attempt {attempt} failed, generating patch...")
        error_summary = extract_error_summary(report, raw_logs)

        with open(target_path) as f:
            current_code = f.read()
        with open(test_path) as f:
            test_code = f.read()

        fixed_code = call_llm_for_patch(current_code, test_code, error_summary)

        if not is_valid_python(fixed_code):
            print(f"  LLM returned invalid Python, skipping this attempt's write")
            log[-1]["invalid_patch"] = True
            continue

        with open(target_path, "w") as f:
            f.write(fixed_code)
        log[-1]["patched"] = True

    print(f"  Failed after {MAX_RETRIES} attempts")
    return False, log


def main():
    cases_dir = "cases"
    results = {}
    for case_name in sorted(os.listdir(cases_dir)):
        case_path = os.path.join(cases_dir, case_name)
        if not os.path.isdir(case_path):
            continue
        print(f"\n=== Running {case_name} ===")
        passed, log = heal_case(case_path)
        results[case_name] = {"passed": passed, "attempts": log}

    print("\n=== Summary ===")
    for case, r in results.items():
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{case}: {status} ({len(r['attempts'])} attempts)")

    with open("run_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()