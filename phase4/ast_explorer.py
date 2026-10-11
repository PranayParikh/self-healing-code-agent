import os
import ast
from collections import defaultdict

def parser(path):
    with open(path) as f:
        source = f.read()

    tree = ast.parse(source)
    empty_dict = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                empty_dict["Imports"].append({
                    "type": "import",
                    "name": alias.name
                })

        if isinstance(node, ast.ImportFrom):
            empty_dict["Imports"].append({
                "type": "from_import",
                "module": node.module,
                "name": [alias.name for alias in node.names]
            })

        if isinstance(node, ast.FunctionDef):
            empty_dict["Function"].append({
                "name": node.name,
                "lineno": node.lineno,
                "args": [arg.arg for arg in node.args.args]
            })

        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
                else:
                    bases.append("unknown")
            empty_dict["Class"].append({
                "name": node.name,
                "lineno": node.lineno,
                "bases": bases
            })

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                empty_dict["Calls"].append({
                    "type": "function_call",
                    "name": node.func.id
                })
            elif isinstance(node.func, ast.Attribute):
                empty_dict["Calls"].append({
                    "type": "method_call",
                    "name": node.func.attr
                })

    return dict(empty_dict)

if __name__ == "__main__":
    for filename in os.listdir("sample_repo"):
        if filename.endswith(".py"):
            full_path = os.path.join("sample_repo", filename)
            info = parser(full_path)
            print(f"\n=== {filename} ===")
            for key, value in info.items():
                print(f"\n{key}:")
                for item in value:
                    print(" ", item)
