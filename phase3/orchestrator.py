import os
from typing import TypedDict, List
from langgraph.graph import START, END, StateGraph
from heal import run_tests_in_sandbox, extract_error_summary, call_llm_for_patch, clean_llm_output, is_valid_python
import networkx as nx
from build_graph import build_graph

class AgentState(TypedDict):
    filename: str
    current_code: str
    test_code: str
    last_error: str
    attempt: int
    passed: bool
    plan: List[str]
    current_index: int
    result: dict[str,dict]
    skipped: dict[str,str]

SAMPLE_REPO_DIR = "sample_repo"
MAX_RETRIES = 5

import networkx as nx
from build_graph import build_graph

def architect_node(state: AgentState) -> AgentState:
    # First run: no plan yet, so build one
    if not state["plan"]:
        graph = build_graph(SAMPLE_REPO_DIR)
        order = list(reversed(list(nx.topological_sort(graph))))  # dependencies first

        plan = []
        skipped = {}
        for filename in order:
            test_file = "test_" + filename
            if os.path.exists(os.path.join(SAMPLE_REPO_DIR, test_file)):
                plan.append(filename)
            else:
                skipped[filename] = "no matching test file"

        state["plan"] = plan
        state["skipped"] = skipped

    # Later runs: a file just finished, so record its outcome before resetting
    else:
        results = dict(state["result"])
        results[state["filename"]] = {
            "passed": state["passed"],
            "attempts": state["attempt"],
        }
        state["result"] = results

    state["current_index"] += 1

    # If a file is left, load it and reset the per-file fields
    if state["current_index"] < len(state["plan"]):
        filename = state["plan"][state["current_index"]]
        with open(os.path.join(SAMPLE_REPO_DIR, filename)) as f:
            state["current_code"] = f.read()
        with open(os.path.join(SAMPLE_REPO_DIR, "test_" + filename)) as f:
            state["test_code"] = f.read()
        state["filename"] = filename
        state["attempt"] = 0
        state["passed"] = False
        state["last_error"] = ""

    return state

def tester_node(state: AgentState) -> AgentState:
    target_path = os.path.join(SAMPLE_REPO_DIR, state["filename"])

    with open(target_path, "w") as f:
        f.write(state["current_code"])

    passed, report, raw_logs = run_tests_in_sandbox(SAMPLE_REPO_DIR, "test_" + state["filename"])

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
        return "next_file"
    elif state["attempt"] < MAX_RETRIES:
        return "continue"
    else:
        return "next_file"

def architect_router(state: AgentState) -> str:
    if state["current_index"] < len(state["plan"]):
        return "test"
    return "end"

graph = StateGraph(AgentState)
graph.add_node("architect", architect_node)
graph.add_node("tester", tester_node)
graph.add_node("coder", coder_node)


graph.add_edge(START, "architect")
graph.add_conditional_edges(
    "architect",
    architect_router,
    {
        "end": END,
        "test": "tester"
    }
)
graph.add_conditional_edges(
    "tester",
    should_continue,
    {
        "next_file": "architect",
        "continue": "coder"
    }
)
graph.add_edge("coder", "tester")

graph_app = graph.compile()

if __name__ == "__main__":

    initial_state = {
        "filename": "",
        "current_code": "",
        "test_code": "",
        "last_error": "",
        "attempt": 0,
        "passed": False,
        "plan": [],
        "result": {},
        "skipped": {},
        "current_index": -1
    }

    final_state = graph_app.invoke(initial_state, config={"recursion_limit": 50})

    print("\n=== Final result ===")
    print("Plan:", final_state["plan"])
    print("Results:", final_state["result"])
    print("Skipped:", final_state["skipped"])