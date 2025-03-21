import os
import fnmatch

class MCPTools:
    def __init__(self, project_root: str):
        """Initialize MCPTools with the project root directory."""
        self.project_root = os.path.abspath(project_root)
        self.ignore_patterns = [
            "**/.git/**", "**/__pycache__/**", "**/venv/**", "**/node_modules/**",
            "**/*.pyc", "**/*.pyo", "**/.env", "**/*.env", "**/.DS_Store",
            "**/*.jpg", "**/*.jpeg", "**/*.png", "**/*.gif", "**/chunk-*.txt"
        ]

    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored based on predefined patterns."""
        rel_path = os.path.relpath(path, self.project_root)
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.ignore_patterns)

    def list_files(self, directory: str) -> list:
        """List files in a directory within the project root."""
        full_dir = os.path.abspath(os.path.join(self.project_root, directory))
        if not full_dir.startswith(self.project_root):
            return ["Error: Directory is outside the repo!"]
        try:
            files = []
            for f in os.listdir(full_dir):
                full_path = os.path.join(full_dir, f)
                if os.path.isfile(full_path) and not self.should_ignore(full_path):
                    files.append(os.path.relpath(full_path, self.project_root))
            return files
        except Exception as e:
            return [f"Error listing files: {str(e)}"]

    def read_file(self, file_path: str) -> str:
        """Read the content of a file within the project root."""
        full_path = os.path.abspath(os.path.join(self.project_root, file_path))
        if not full_path.startswith(self.project_root) or self.should_ignore(full_path):
            return "Error: File is outside the repo or ignored!"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Handle tool calls from Claude by dispatching to the appropriate function."""
        if tool_name == "list_files":
            return self.list_files(tool_input["directory"])
        elif tool_name == "read_file":
            return self.read_file(tool_input["file_path"])
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
    }
]