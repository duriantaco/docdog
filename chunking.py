import ast

def chunk_code(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
            tree = ast.parse(file_content, filename=file_path)

        chunks = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                chunk_code = ast.get_source_segment(file_content, node)
                chunks.append({
                    "name": node.name,
                    "type": "function" if isinstance(node, ast.FunctionDef) else "class",
                    "code": chunk_code
                })
        return chunks
    except Exception as e:
        print(f"[ERROR] Failed to parse {file_path}: {e}")
        return []