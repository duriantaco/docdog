import os
import sys
import argparse
import logging
import anthropic
import datetime
import traceback
import shutil
import threading
from docdog.mcp_tools import MCPTools, tools
from dotenv import load_dotenv
from docdog.chunking import chunk_project
from docdog.utils.sanitize_prompt import sanitize_prompt
from colorama import init

load_dotenv()
init(autoreset=True)

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

def get_user_confirmation(timeout=10):
    """Ask user to confirm chunking and proceed with a timeout."""
    response = [None]
    def ask():
        try:
            user_input = input(f"Chunking complete. {len(chunk_files)} chunks created. Is this correct? (y/n, default y after {timeout}s): ")
            response[0] = user_input.lower().strip()
        except Exception:
            pass

    thread = threading.Thread(target=ask)
    thread.start()
    thread.join(timeout)
    if response[0] is None:
        logger.info("No response received. Proceeding automatically.")
        return True
    elif response[0] in ['y', 'yes']:
        return True
    elif response[0] in ['n', 'no']:
        logger.info("User chose not to proceed.")
        return False
    else:
        logger.info("Invalid response. Proceeding automatically.")
        return True

def main():
    parser = argparse.ArgumentParser(description="DocDog - AI Document & Code Summarizer")
    parser.add_argument("-o", "--output", default="README.md")
    parser.add_argument("-m", "--model", default="claude-3-sonnet-20240229")
    parser.add_argument("--reasoning", action="store_true")
    parser.add_argument("-p", "--prompt-template")
    parser.add_argument("--max-iterations", type=int, default=15)
    parser.add_argument("--workers", "-w", type=int, default=None, 
                        help="Number of worker threads (default: auto)")
    parser.add_argument("--cache-size", type=int, default=128, 
                    help="Size of the LRU cache (default: 128)")
    args = parser.parse_args()

    project_root = find_project_root()
    logger.info(f"Project root: {project_root}")

    chunks_dir = os.path.join(project_root, "chunks")
    
    chunk_config = {
        "num_chunks": 5,
        "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".js", ".html", ".css", ".sh"]
    }
    
    logger.info("Chunking project files...")
    global chunk_files  
    chunk_files = chunk_project(project_root, chunks_dir, chunk_config)
    logger.info(f"Created {len(chunk_files)} chunk files in ./chunks directory")

    if not get_user_confirmation():
        sys.exit(0)

    estimated_time_per_chunk = 5 
    total_estimated_time = len(chunk_files) * estimated_time_per_chunk
    minutes = total_estimated_time // 60
    seconds = total_estimated_time % 60
    logger.info(f"Estimated time for summarization: approximately {minutes} minutes and {seconds} seconds")

    mcp_tools = MCPTools(project_root=project_root, max_workers=args.workers, cache_size=args.cache_size)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(script_dir, "templates")

    if args.prompt_template and os.path.exists(args.prompt_template):
        with open(args.prompt_template, "r") as f:
            initial_prompt = f.read()
        initial_prompt = sanitize_prompt(initial_prompt)
    else:
        default_initial_prompt_path = os.path.join(templates_dir, "initial_prompt.txt")
        if os.path.exists(default_initial_prompt_path):
            with open(default_initial_prompt_path, "r") as f:
                initial_prompt = f.read()
            initial_prompt = sanitize_prompt(initial_prompt)
        else:
            logger.error(f"Default initial prompt template not found at {default_initial_prompt_path}")
            sys.exit(1)

    if args.reasoning:
        reasoning_instructions_path = os.path.join(templates_dir, "reasoning_instructions.txt")
        if os.path.exists(reasoning_instructions_path):
            with open(reasoning_instructions_path, "r") as f:
                reasoning_instructions = f.read()
            initial_prompt += "\n" + reasoning_instructions
        else:
            logger.error(f"Reasoning instructions template not found at {reasoning_instructions_path}")
            sys.exit(1)

    messages = [{"role": "user", "content": sanitize_prompt(initial_prompt)}]
    
    logger.info("===== PHASE 1: Project Analysis =====")
    analyzed_chunks = set()
    max_analysis_iterations = args.max_iterations
    analysis_iteration = 0
    
    expected_chunks = []
    try:
        if os.path.exists(chunks_dir):
            expected_chunks = [f for f in os.listdir(chunks_dir) if f.startswith("chunk-") and f.endswith(".txt")]
    except Exception as e:
        logger.error(f"Error listing chunk files: {str(e)}")
    
    logger.info(f"Found {len(expected_chunks)} chunk files to analyze")
    
    while len(analyzed_chunks) < len(expected_chunks) and analysis_iteration < max_analysis_iterations:
        try:
            logger.info(f"Analysis iteration {analysis_iteration+1}/{max_analysis_iterations}")
            response = client.messages.create(
                model=args.model,
                messages=messages,
                tools=tools,
                max_tokens=4000
            )
            
            assistant_content = []
            for content in response.content:
                if content.type == "text":
                    assistant_content.append({"type": "text", "text": content.text})
                elif content.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": content.id,
                        "name": content.name,
                        "input": content.input
                    })
            
            messages.append({"role": "assistant", "content": assistant_content})
            
            tool_calls = [c for c in response.content if c.type == "tool_use"]
            if tool_calls:
                tool_results_content = []
                for tool_call in tool_calls:
                    tool_name = tool_call.name
                    tool_input = tool_call.input
                    tool_id = tool_call.id
                    
                    if tool_name == "read_file" and "file_path" in tool_input:
                        file_path = tool_input["file_path"]
                        chunk_name = os.path.basename(file_path)
                        if chunk_name in expected_chunks:
                            analyzed_chunks.add(chunk_name)
                            logger.info(f"Analyzed chunk: {chunk_name} ({len(analyzed_chunks)}/{len(expected_chunks)})")
                    elif tool_name == "batch_read_files" and "file_paths" in tool_input:
                        for file_path in tool_input["file_paths"]:
                            chunk_name = os.path.basename(file_path)
                            if chunk_name in expected_chunks:
                                analyzed_chunks.add(chunk_name)
                                logger.info(f"Analyzed chunk: {chunk_name} ({len(analyzed_chunks)}/{len(expected_chunks)})")
                    
                    logger.info(f"Claude requested tool: {tool_name} with input: {tool_input}")
                    result = mcp_tools.handle_tool_call(tool_name, tool_input)
                    log_preview = result[:100] + "..." if len(result) > 100 else result
                    logger.info(f"Tool {tool_name} returned: {log_preview}")
                    
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })
                
                messages.append({"role": "user", "content": tool_results_content})
                        
            analysis_iteration += 1
            
            for content in response.content:
                if content.type == "text" and "Final README:" in content.text:
                    logger.info("Claude prematurely generated a README during analysis. Continuing to ensure all chunks are analyzed.")
        
        except Exception as e:
            logger.error(f"Error in analysis phase: {str(e)}")
            traceback.print_exc()
            break
    
    if len(analyzed_chunks) < len(expected_chunks):
        logger.warning(f"Analysis incomplete: Only {len(analyzed_chunks)}/{len(expected_chunks)} chunks were analyzed")
        missing_chunks = set(expected_chunks) - analyzed_chunks
        logger.warning(f"Missing chunks: {', '.join(missing_chunks)}")
    else:
        logger.info(f"Successfully analyzed all {len(expected_chunks)} chunks")
    
    logger.info("===== PHASE 2: README Generation =====")
    
    generation_prompt = (
        "Now that you have analyzed all available chunks, please generate the complete README.md file "
        "based on the code you've examined. Follow the structure specified in the initial instructions. "
        "Your response should start with 'Final README:' followed by the complete README content."
    )
    
    if len(analyzed_chunks) < len(expected_chunks):
        generation_prompt += f"\n\nNote: You've only been able to analyze {len(analyzed_chunks)} out of {len(expected_chunks)} chunks. Please generate the best README possible with the information you have."
    
    messages.append({"role": "user", "content": generation_prompt})
    
    readme_content = None
    reasoning_content = None
    try:
        logger.info("Requesting README generation from Claude")
        response = client.messages.create(
            model=args.model,
            messages=messages,
            max_tokens=4000
        )
        
        full_text = "".join([c.text for c in response.content if c.type == "text"])
        
        if "Final README:" in full_text:
            parts = full_text.split("Final README:", 1)
            if len(parts) > 1:
                readme_and_reasoning = parts[1].strip()
                if args.reasoning and "Reasoning:" in readme_and_reasoning:
                    readme_content, reasoning_content = readme_and_reasoning.split("Reasoning:", 1)
                    readme_content = readme_content.strip()
                    reasoning_content = reasoning_content.strip()
                else:
                    readme_content = readme_and_reasoning
            else:
                readme_content = full_text.strip()
        else:
            readme_content = full_text.strip()
        
        if readme_content:
            logger.info("README content successfully generated")
        else:
            logger.warning("No README content found in the response")
    
    except Exception as e:
        logger.error(f"Error in README generation: {str(e)}")
        traceback.print_exc()
    
    if readme_content and readme_content.strip():
        logger.info("===== PHASE 3: README Validation =====")
        
        messages.append({
            "role": "assistant", 
            "content": [{"type": "text", "text": full_text}]
        })
        
        validation_prompt_path = os.path.join(templates_dir, "validation_prompt.txt")
        if os.path.exists(validation_prompt_path):
            with open(validation_prompt_path, "r") as f:
                validation_prompt = f.read()
        else:
            logger.error(f"Validation prompt template not found at {validation_prompt_path}")
            sys.exit(1)
        
        messages.append({"role": "user", "content": validation_prompt})
        
        try:
            logger.info("Requesting README validation from Claude")
            response = client.messages.create(
                model=args.model,
                messages=messages,
                max_tokens=4000
            )
            
            validation_text = "".join([c.text for c in response.content if c.type == "text"])
            
            if "Improved README:" in validation_text:
                logger.info("README improvements suggested - using improved version")
                improved_parts = validation_text.split("Improved README:", 1)
                if len(improved_parts) > 1:
                    improved_content = improved_parts[1].strip()
                    if args.reasoning and "Reasoning:" in improved_content:
                        readme_content, reasoning_content = improved_content.split("Reasoning:", 1)
                        readme_content = readme_content.strip()
                        reasoning_content = reasoning_content.strip()
                    else:
                        readme_content = improved_content
            elif "README validation passed" in validation_text:
                logger.info("README validation passed - no changes needed")
            else:
                logger.info("README validation complete but unclear result - using original README")
        
        except Exception as e:
            logger.warning(f"Error in README validation: {str(e)}")
            logger.warning("Proceeding with unvalidated README")
    
    if not readme_content or readme_content.strip() == "":
        logger.error("Failed to generate README content")
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        readme_content = f"""# Project Documentation

DocDog attempted to generate documentation but was unable to produce meaningful content.
Please check the logs for details or try running DocDog again.

Analysis stats:
- Chunks analyzed: {len(analyzed_chunks)}/{len(expected_chunks)}
- Analysis iterations: {analysis_iteration}/{max_analysis_iterations}
"""
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    final_readme_content = f"{readme_content}\n\n---\n*Generated by DocDog on {current_date}*"
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(final_readme_content)
    logger.info(f"README written to {args.output}")
    
    if args.reasoning and reasoning_content:
        final_reasoning_content = f"# Reasoning Behind README Generation\n\n{reasoning_content}\n\n---\n*Generated by DocDog on {current_date}*"
        with open("reasoning.md", "w", encoding="utf-8") as f:
            f.write(final_reasoning_content)
        logger.info("Reasoning written to reasoning.md")
    
    if os.path.exists(chunks_dir):
        try:
            shutil.rmtree(chunks_dir)
            logger.info(f"Deleted chunk files in {chunks_dir}")
        except Exception as e:
            logger.warning(f"Failed to delete chunk files: {str(e)}")
    
    logger.info("===== DocDog Execution Summary =====")
    logger.info(f"Chunks analyzed: {len(analyzed_chunks)}/{len(expected_chunks)}")
    logger.info(f"Analysis iterations used: {analysis_iteration}/{max_analysis_iterations}")
    logger.info(f"README file written to: {args.output}")
    if args.reasoning:
        logger.info("Reasoning file written to: reasoning.md")
    logger.info("DocDog execution completed")

if __name__ == "__main__":
    main()