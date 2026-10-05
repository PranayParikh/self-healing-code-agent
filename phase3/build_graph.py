import os
import networkx as nx
from ast_explorer import parser
import re

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)

def fallback_parser(path):
    """Text-based import scan for files that don't parse."""
    with open(path) as f:
        source = f.read()
    imports = []
    for m in IMPORT_RE.finditer(source):
        if m.group(1):
            imports.append({"type": "from_import", "module": m.group(1), "name": []})
        else:
            imports.append({"type": "import", "name": m.group(2)})
    return {"Imports": imports}

def build_graph(folder):
    graph = nx.DiGraph()
    all_info = {}

    for filename in os.listdir(folder):
        if filename.endswith(".py") and not filename.startswith("test_"):
            full_path = os.path.join(folder, filename)
            graph.add_node(filename)
            try:
                all_info[filename] = parser(full_path)
            except SyntaxError:
                print(f"  warning: {filename} does not parse; using text-based import scan")
                all_info[filename] = fallback_parser(full_path)

    for filename, info in all_info.items():
        imports = info.get("Imports", [])
        for imp in imports:
            module = imp.get("module")
            if module is None:
                continue
            target_filename = module + ".py"
            if target_filename in graph.nodes():
                graph.add_edge(filename, target_filename)

    return graph


if __name__ == "__main__":
    graph = build_graph("sample_repo")

    print("Nodes:", list(graph.nodes()))
    print("Edges:", list(graph.edges()))
    print("Processing order:", list(nx.topological_sort(graph)))
    print("Is DAG:", nx.is_directed_acyclic_graph(graph))
