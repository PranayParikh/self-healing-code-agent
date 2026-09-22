import os
import networkx as nx
from ast_explorer import parser

def build_graph(folder):
    graph = nx.DiGraph()
    all_info = {}

    for filename in os.listdir(folder):
        if filename.endswith(".py"):
            full_path = os.path.join(folder, filename)
            graph.add_node(filename)
            all_info[filename] = parser(full_path)

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
