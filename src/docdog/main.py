import os
import sys
import argparse
import logging
import anthropic
import datetime
from docdog.mcp_tools import MCPTools, tools

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("docdog_complete_log.txt", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    logger.error("ANTHROPIC_API_KEY not found in environment variables.")
    sys.exit(1)
client = anthropic.Anthropic(api_key=api_key)

def find_project_root():
    """Find the project root by looking for common project markers."""
    markers = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json']
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prev_dir = None
    while current_dir != prev_dir:
        for marker in markers:
            if os.path.exists(os.path.join(current_dir, marker)):
                return current_dir
        prev_dir = current_dir
        current_dir = os.path.dirname(current_dir)
    return os.path.dirname(os.path.abspath(__file__))

def main():
    parser = argparse.ArgumentParser(description="DocDog - AI Document & Code Summarizer")
    parser.add_argument("-o", "--output", default="README.md", help="Output file (default: README.md)")
    parser.add_argument("-m", "--model", default="claude-3-opus-20240229", help="Anthropic model to use (default: claude-3-opus-20240229)")
    parser.add_argument("-p", "--prompt-template", help="Path to custom prompt template file")
    args = parser.parse_args()

    project_root = find_project_root()
    logger.info(f"Project root: {project_root}")

    mcp_tools = MCPTools(project_root)

    if args.prompt_template and os.path.exists(args.prompt_template):
        with open(args.prompt_template, "r") as f:
            initial_prompt = f.read()
    else:
        initial_prompt = """
You are an expert technical documentation specialist. Your task is to generate a professional README.md file for the software project in the current directory. You can use the provided tools to list files and read their contents. Focus on source code files (e.g., .py, .js, .cpp), documentation (e.g., .md, .txt), and configuration files (e.g., .json, .toml) to understand the project's purpose, features, and usage.

Please structure the README with the following sections:

### 1. Title and Badges
- Use the project name if available (e.g., from pyproject.toml or package.json).
- Include relevant badges if information is available (e.g., build status, version, license).

### 2. Overview/Introduction
- Provide a concise (2-3 paragraphs) explanation of what the project does.
- Explain the problem it solves and why it exists.

### 3. Features
- List core features as bullet points with brief explanations.

### 4. Installation
- Provide step-by-step installation instructions.
- Include prerequisites and dependencies (e.g., from requirements.txt or package.json).

### 5. Usage
- Show how to use the project with examples (e.g., CLI commands, code snippets).

### 6. API Documentation (if applicable)
- Document main classes, functions, or endpoints if the project is a library.

### 7. Configuration
- Explain configuration options and environment variables if present.

### 8. Examples and Use Cases
- Provide realistic examples based on the code.

### 9. Troubleshooting/FAQ
- Address common issues inferred from the code or documentation.

### 10. Contributing
- Provide basic guidelines for contributors.

### 11. License
- Specify the license type if found (e.g., in LICENSE file).

Once you have gathered enough information, generate the complete README content in Markdown format and provide it in your final response. Do not invent features or details not evident from the files.
"""

    messages = [{"role": "user", "content": initial_prompt}]

    while True:
        response = client.messages.create(
            model=args.model,
            messages=messages,
            tools=tools,
            max_tokens=4000
        )

        if response.stop_reason == "tool_use":
            tool_calls = [content for content in response.content if content.type == "tool_use"]
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                tool_id = tool_call.id

                logger.info(f"Claude requested tool: {tool_name} with input: {tool_input}")
                result = mcp_tools.handle_tool_call(tool_name, tool_input)

                tool_results.append({
                    "tool_call_id": tool_id,
                    "result": result
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            readme_content = ""
            for content in response.content:
                if content.type == "text":
                    readme_content += content.text
            logger.info("README content generated by Claude.")
            break

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    final_content = f"{readme_content}\n\n---\n*Generated by DocDog on {current_date}*"
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(final_content)
    logger.info(f"README written to {args.output}")

if __name__ == "__main__":
    main()