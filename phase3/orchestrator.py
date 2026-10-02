import os
from typing import TypedDict
from langgraph.graph import START, END, StateGraph
from heal import run_tests_in_sandbox, extract_error_summary, call_llm_for_patch, clean_llm_output, is_valid_python

class AgentState(TypedDict):
    filename: str
    current_code: str
    test_code: str
    last_error: str
    attempt: int
    passed: bool

SAMPLE_REPO_DIR = "sample_repo"
MAX_RETRIES = 5

def tester_node(state: AgentState) -> AgentState:
    target_path = os.path.join(SAMPLE_REPO_DIR, state["filename"])

    with open(target_path, "w") as f:
        f.write(state["current_code"])

    passed, report, raw_logs = run_tests_in_sandbox(SAMPLE_REPO_DIR)

    if passed:
        state["passed"] = True
    else:
        state["passed"] = False
        error_summary = extract_error_summary(report, raw_logs)
        state["last_error"] = str(error_summary)

    return state

def coder_node(state: AgentState) -> AgentState:
    fixed_code = call_llm_for_patch(
        state["current_code"],
        state["test_code"],
        state["last_error"]
    )
    fixed_code = clean_llm_output(fixed_code)

    if is_valid_python(fixed_code):
        state["current_code"] = fixed_code

    state["attempt"] += 1
    return state

def should_continue(state: AgentState) -> str:
    if state["passed"]:
        return "end"
    elif state["attempt"] < MAX_RETRIES:
        return "continue"
    else:
        return "end"

graph = StateGraph(AgentState)
graph.add_node("tester", tester_node)
graph.add_node("coder", coder_node)
graph.add_edge(START, "tester")
graph.add_conditional_edges(
    "tester",
    should_continue,
    {
        "end": END,
        "continue": "coder"
    }
)
graph.add_edge("coder", "tester")

graph_app = graph.compile()

if __name__ == "__main__":
    filename = "basic_test.py"
    code_path = os.path.join(SAMPLE_REPO_DIR, filename)
    test_path = os.path.join(SAMPLE_REPO_DIR, "test_basic_test.py")

    with open(code_path) as f:
        current_code = f.read()
    with open(test_path) as f:
        test_code = f.read()

    initial_state = {
        "filename": filename,
        "current_code": current_code,
        "test_code": test_code,
        "last_error": "",
        "attempt": 0,
        "passed": False
    }

    final_state = graph_app.invoke(initial_state)

    print("\n=== Final result ===")
    print("Passed:", final_state["passed"])
    print("Attempts used:", final_state["attempt"])
