import os
import sys
import argparse
import logging
import anthropic
import threading
from docdog.tools import Tools, use_tools
from dotenv import load_dotenv
from docdog.chunking import chunk_project
from docdog.utils.sanitize_prompt import sanitize_prompt
from colorama import init
from docdog.p1_analysis_helper import analyze_project
from docdog.p2_readme_generator import generate_readme
from docdog.p3_validate_readme import validate_readme
from docdog.p4_save_readme import save_readme_files
from docdog.find_proj_root import find_project_root

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

    doc_tools = Tools(project_root=project_root, max_workers=args.workers, cache_size=args.cache_size)

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
    
    expected_chunks = []
    try:
        if os.path.exists(chunks_dir):
            expected_chunks = [f for f in os.listdir(chunks_dir) if f.startswith("chunk-") and f.endswith(".txt")]
    except Exception as e:
        logger.error(f"Error listing chunk files: {str(e)}")
    
    logger.info(f"Found {len(expected_chunks)} chunk files to analyze")
    
    logger.info("===== PHASE 1: Project Analysis =====")
    messages, analyzed_chunks, analysis_iteration = analyze_project(
        client=client,
        model=args.model,
        messages=messages,
        tools=use_tools,
        doc_tools=doc_tools,
        expected_chunks=expected_chunks,
        max_iterations=args.max_iterations
    )
    
    logger.info("===== PHASE 2: README Generation =====")
    readme_content, reasoning_content, full_text = generate_readme(
        client=client, 
        model=args.model, 
        messages=messages, 
        analyzed_chunks=analyzed_chunks, 
        expected_chunks=expected_chunks
    )
    
    if readme_content and readme_content.strip():
        logger.info("===== PHASE 3: README Validation =====")
        readme_content, reasoning_content = validate_readme(
            client=client,
            model=args.model,
            messages=messages,
            full_text=full_text,
            readme_content=readme_content,
            reasoning_content=reasoning_content,
            templates_dir=templates_dir
        )
    
        logger.info("===== PHASE 4: README Output =====")
    save_readme_files(
    args=args,
    readme_content=readme_content,
    reasoning_content=reasoning_content,
    analyzed_chunks=analyzed_chunks,
    expected_chunks=expected_chunks,
    analysis_iteration=analysis_iteration
)
    logger.info("DocDog execution completed")

if __name__ == "__main__":
    main()