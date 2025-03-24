import os
import sys
import argparse
import logging
import anthropic
import datetime
import traceback
from docdog.mcp_tools import MCPTools, tools
from dotenv import load_dotenv
from docdog.chunking import chunk_project

load_dotenv()

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
    parser.add_argument("-m", "--model", default="claude-3-sonnet-20240229", help="Model to use (default: claude-3-sonnet-20240229)")
    parser.add_argument("-p", "--prompt-template", help="Path to custom prompt template file")
    args = parser.parse_args()

    project_root = find_project_root()
    logger.info(f"Project root: {project_root}")

    chunks_dir = os.path.join(project_root, "chunks")
    
    chunk_config = {
        "num_chunks": 5,
        "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".js", ".html", ".css", ".sh"]
    }
    
    logger.info("Chunking project files...")
    chunk_files = chunk_project(project_root, chunks_dir, chunk_config)
    logger.info(f"Created {len(chunk_files)} chunk files in ./chunks directory")

    mcp_tools = MCPTools(project_root)

    if args.prompt_template and os.path.exists(args.prompt_template):
        with open(args.prompt_template, "r") as f:
            initial_prompt = f.read()
    else:
        initial_prompt = """
You are an expert technical documentation specialist. Your task is to generate a professional README.md file for the software project that has been chunked into files. 

## IMPORTANT FIRST STEPS:
1. First, use the list_files tool with "./chunks" directory to find all the chunk files
2. Read each chunk file (they will be named like chunk-0.txt, chunk-1.txt, etc.)
3. Carefully analyze the code and structure in these chunks
4. Only after reading and understanding ALL chunks, generate the complete README

The chunks contain the source code files that have been split up. Each chunk contains multiple files with clear markers showing where each file starts and ends.

Please structure the README with the following sections:

1. **Title and Badges**
   - Use the project name from configuration files (e.g., pyproject.toml, package.json).
   - Include badges for license, version, etc. if information is available.

2. **Overview/Introduction**
   - Provide a concise explanation of what the project does.
   - Explain the problem it solves and why it exists.

3. **Features**
   - List core features as bullet points with brief explanations.

4. **Installation**
   - Provide step-by-step installation instructions.
   - Include prerequisites and dependencies.

5. **Usage**
   - Show how to use the project with examples (CLI commands, code snippets).
   - Include the common use cases and patterns.

6. **API Documentation**
   - Document main classes, functions, or endpoints if the project is a library.

7. **Configuration**
   - Explain configuration options and environment variables if present.

8. **Examples and Use Cases**
   - Provide realistic examples based on the code.

9. **Troubleshooting/FAQ**
   - Address common issues inferred from the code or documentation.

10. **Contributing**
    - Provide basic guidelines for contributors.

11. **License**
    - Specify the license type if found.

Be thorough in your analysis. Generate detailed and accurate documentation based strictly on the information in the chunk files.
"""

    messages = [{"role": "user", "content": initial_prompt}]

    while True:
        try:
            logger.info(f"Sending message to Claude model: {args.model}")
            response = client.messages.create(
                model=args.model,
                messages=messages,
                tools=tools,
                max_tokens=4000
            )
            
            if response.stop_reason == "tool_use":
                tool_calls = [content for content in response.content if content.type == "tool_use"]
                
                assistant_content = []
                for content_item in response.content:
                    if content_item.type == "text":
                        assistant_content.append({"type": "text", "text": content_item.text})
                    elif content_item.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": content_item.id,
                            "name": content_item.name,
                            "input": content_item.input
                        })
                
                messages.append({"role": "assistant", "content": assistant_content})
                
                tool_results_content = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.name
                    tool_input = tool_call.input
                    tool_id = tool_call.id
                    
                    logger.info(f"Claude requested tool: {tool_name} with input: {tool_input}")
                    result = mcp_tools.handle_tool_call(tool_name, tool_input)
                    
                    if not isinstance(result, str):
                        result = str(result)
                    
                    log_preview = result[:100] + "..." if len(result) > 100 else result
                    logger.info(f"Tool {tool_name} returned: {log_preview}")
                    
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id, 
                        "content": result       
                    })
                
                user_message = {
                    "role": "user", 
                    "content": tool_results_content
                }
                messages.append(user_message)
                
            else:
                readme_content = ""
                for content in response.content:
                    if content.type == "text":
                        readme_content += content.text
                logger.info("README content generated by Claude.")
                break
                
        except Exception as e:
            logger.error(f"Error in Claude API communication: {str(e)}")
            traceback.print_exc()
            sys.exit(1)

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    final_content = f"{readme_content}\n\n---\n*Generated by DocDog on {current_date}*"
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(final_content)
    logger.info(f"README written to {args.output}")

if __name__ == "__main__":
    main()