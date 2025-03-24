import os
import fnmatch
import ast
import json

class MCPTools:
    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self.ignore_patterns = [
            "**/.git/**", "**/__pycache__/**", "**/venv/**", "**/node_modules/**",
            "**/*.pyc", "**/*.pyo", "**/.env", "**/*.env", "**/.DS_Store",
            "**/*.jpg", "**/*.jpeg", "**/*.png", "**/*.gif"
        ]

    def should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, self.project_root)
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.ignore_patterns)

    def list_files(self, directory: str) -> str:

      
        full_dir = os.path.abspath(os.path.join(self.project_root, directory))
        if not full_dir.startswith(self.project_root):
            return "Error: Directory is outside the repo!"
        try:

            print(f"DEBUG: list_files: project_root = {self.project_root}")
            print(f"DEBUG: list_files: requested directory = {directory}")
            print(f"DEBUG: list_files: full_dir = {full_dir}")
            print(f"DEBUG: list_files: directory exists? {os.path.exists(full_dir)}")
            if os.path.exists(full_dir):
                print(f"DEBUG: list_files: contents = {os.listdir(full_dir)}")
        

            files = []
            for f in os.listdir(full_dir):
                full_path = os.path.join(full_dir, f)
                if os.path.isfile(full_path) and not self.should_ignore(full_path):
                    files.append(os.path.relpath(full_path, self.project_root))
            return "\n".join(files) if files else "No files found."
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def read_file(self, file_path: str) -> str:
        full_path = os.path.join(self.project_root, file_path)
        if self.should_ignore(full_path):
            return "Error: File ignored!"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if file_path.endswith('.py'):
                tree = ast.parse(content)
                docstrings = [node.body[0].value.s for node in ast.walk(tree) 
                            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) 
                            and node.body and isinstance(node.body[0], ast.Expr) 
                            and isinstance(node.body[0].value, ast.Str)]
                comments = [line.strip() for line in content.split('\n') if line.strip().startswith('#')]
                return f"Content:\n{content}\n\nDocstrings:\n{docstrings}\n\nComments:\n{comments}"
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
        
    def batch_read_files(self, file_paths: list) -> str:
        results = []
        for file_path in file_paths:
            content = self.read_file(file_path)
            if "Error" in content:
                results.append({"file": file_path, "error": content})
            else:
                results.append({"file": file_path, "content": content})
        return json.dumps(results, indent=2)

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "list_files":
            return self.list_files(tool_input["directory"])
        elif tool_name == "read_file":
            return self.read_file(tool_input["file_path"])
        elif tool_name == "batch_read_files":
            return self.batch_read_files(tool_input["file_paths"])
        else:
            return f"Unknown tool: {tool_name}"

tools = [
    {
        "name": "list_files",
        "description": "List files in a directory within the current repo.",
        "input_schema": {
            "type": "object",
            "properties": {"directory": {"type": "string", "description": "Directory path relative to repo root"}},
            "required": ["directory"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file’s content within the current repo.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "File path relative to repo root"}},
            "required": ["file_path"]
        }
    },
    {
    "name": "batch_read_files",
    "description": "Read multiple files’ contents within the repo.",
    "input_schema": {
        "type": "object",
        "properties": {"file_paths": {"type": "array", "items": {"type": "string"}}},
        "required": ["file_paths"]
    }
  }
]