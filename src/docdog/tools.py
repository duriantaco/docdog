import os
import fnmatch
import ast
import json
import concurrent.futures
from typing import Optional
from functools import lru_cache

class Tools:
    def __init__(self, project_root: str, max_workers: Optional[int] = None, cache_size: int = 128):
        self.project_root = os.path.abspath(project_root)
        self.max_workers = max_workers 
        self.cache_size = cache_size 
        self.ignore_patterns = [
            "**/.git/**", "**/__pycache__/**", "**/venv/**", "**/node_modules/**",
            "**/*.pyc", "**/*.pyo", "**/.env", "**/*.env", "**/.DS_Store",
            "**/*.jpg", "**/*.jpeg", "**/*.png", "**/*.gif"
        ]
        self._cached_read_file = lru_cache(maxsize=self.cache_size)(self._read_file_impl)
        self._cached_list_files = lru_cache(maxsize=self.cache_size)(self._list_files_impl)


    def should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, self.project_root)
        
        if rel_path.startswith(".git") or "/.git/" in rel_path:
            return True
        if rel_path.startswith("__pycache__") or "/__pycache__/" in rel_path:
            return True
        if rel_path.startswith("venv") or "/venv/" in rel_path:
            return True
        if rel_path.startswith("node_modules") or "/node_modules/" in rel_path:
            return True
        
        for ext in [".pyc", ".pyo", ".env", ".jpg", ".jpeg", ".png", ".gif", ".DS_Store"]:
            if rel_path.endswith(ext):
                return True
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
                
        return False

    def list_files(self, directory: str) -> str:
        """List files with LRU caching."""
        return self._cached_list_files(directory)
        
    def _list_files_impl(self, directory: str) -> str:
        """Implementation of list_files that will be cached."""
        full_dir = os.path.abspath(os.path.join(self.project_root, directory))
        if not full_dir.startswith(self.project_root):
            return "Error: Directory is outside the repo!"
        try:
            if os.path.exists(full_dir):
                files = []
                for f in os.listdir(full_dir):
                    full_path = os.path.join(full_dir, f)
                    if os.path.isfile(full_path) and not self.should_ignore(full_path):
                        files.append(os.path.relpath(full_path, self.project_root))
                return "\n".join(files) if files else "No files found."
            else:
                return "Directory does not exist."
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def read_file(self, file_path: str) -> str:
        """Read file with LRU caching."""
        return self._cached_read_file(file_path)
        
    def _read_file_impl(self, file_path: str) -> str:
        """Implementation of read_file that will be cached."""
        full_path = os.path.join(self.project_root, file_path)
        if self.should_ignore(full_path):
            return "Error: File ignored!"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if file_path.endswith('.py'):
                tree = ast.parse(content)
                docstrings = []
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.body:
                        first_node = node.body[0]
                        if isinstance(first_node, ast.Expr) and hasattr(first_node.value, 's'):
                            docstrings.append(first_node.value.s)
                
                comments = [line.strip() for line in content.split('\n') if line.strip().startswith('#')]
                return f"Content:\n{content}\n\nDocstrings:\n{docstrings}\n\nComments:\n{comments}"
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
        
    def batch_read_files(self, file_paths: list) -> str:
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.read_file, file_path) for file_path in file_paths]
            for future, file_path in zip(futures, file_paths):
                try:
                    content = future.result()
                    if "Error" in content:
                        results.append({"file": file_path, "error": content})
                    else:
                        results.append({"file": file_path, "content": content})
                except Exception as exc:
                    results.append({"file": file_path, "error": f"Exception: {str(exc)}"})
        return json.dumps(results, indent=2)

    def clear_caches(self):
        """Clear all LRU caches."""
        self._cached_read_file.cache_clear()
        self._cached_list_files.cache_clear()

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "list_files":
            return self.list_files(tool_input["directory"])
        elif tool_name == "read_file":
            return self.read_file(tool_input["file_path"])
        elif tool_name == "batch_read_files":
            return self.batch_read_files(tool_input["file_paths"])
        else:
            return f"Unknown tool: {tool_name}"

use_tools = [
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
        "description": "Read a file's content within the current repo.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "File path relative to repo root"}},
            "required": ["file_path"]
        }
    },
    {
    "name": "batch_read_files",
    "description": "Read multiple files' contents within the repo.",
    "input_schema": {
        "type": "object",
        "properties": {"file_paths": {"type": "array", "items": {"type": "string"}}},
        "required": ["file_paths"]
    }
  }
]