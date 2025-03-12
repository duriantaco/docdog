import os
import sys
import argparse
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
import datetime
from jinja2 import Template
import re
import hashlib
import time
import concurrent.futures
from typing import Dict, Any
from docdog.chunking import chunk_project
from docdog.summary_cache import batch_summarize_chunks

memory_cache = {}

LOG_FILE = "docdog_complete_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    sys.exit(1)
client = OpenAI(api_key=api_key)

## https://platform.openai.com/docs/guides/prompt-engineering
## gonna attach this here for reference
DEFAULT_PROMPT_TEMPLATE = """
# README Generation Instructions

You are an expert technical documentation specialist with extensive experience developing clear, comprehensive README files for software projects. Your task is to analyze the provided code summaries and generate a professional, well-structured README.md file.

## Input Context
- **Project Name**: {{ project_name }}
- **Project Summaries**: Code and file summaries from the project's codebase
- **Build System**: {{ build_system }}
- **Installation Command**: {{ installation_command }}
- **Primary Dependencies**: {{ dependencies }}

## README Structure and Guidelines

### 1. Title and Badges
- Clear project title (use {{ project_name }} if provided)
- Include relevant badges if information is available (build status, version, license)
- Keep this section minimal and focused

### 2. Overview/Introduction
- Provide a concise (2-3 paragraphs) explanation of what the project does
- Explain the problem it solves and why it exists
- Highlight key differentiators or unique aspects
- Infer the project's purpose from code structure, file names, and summaries
- DO NOT invent capabilities that aren't evident from the provided summaries

### 3. Features
- List core features as bullet points with brief explanations
- Group related features under subheadings for larger projects
- Prioritize features that are clearly documented in the code summaries
- For each feature, briefly explain the benefit to the user
- If a feature's implementation seems incomplete, note it as "in development"

### 4. Installation
- Provide step-by-step installation instructions
- Use the {{ installation_command }} if provided
- Include prerequisites (e.g., Python version, system dependencies)
- List all required dependencies
- For Python projects, include pip/poetry commands
- For Node.js projects, include npm/yarn commands
- For compiled languages, include compilation instructions
- Include both basic and advanced installation options if detected

### 5. Usage
- Start with the most common/basic use case
- Provide concrete code examples extracted from the summaries
- Structure examples from simple to complex
- Include explanation before and after each code block
- For CLI tools, show command-line usage with all major options
- For libraries, show import and basic API usage
- For applications, explain key workflows

### 6. API Documentation
- Only include if the project is a library or has a public API
- Document main classes, functions, or endpoints
- Include parameter details, return types, and examples
- Organize by logical groupings (not alphabetically)
- Link to more comprehensive documentation if such references exist in summaries

### 7. Configuration
- Detail configuration options and customizations
- Show example configuration files when available
- Explain environment variables
- Provide sensible defaults and recommendations
- If configuration seems complex, create a table for clarity

### 8. Examples and Use Cases
- Provide a minimum of 3 realistic examples showing actual implementation
- Examples should cover common use cases or scenarios based off the code 
- Include a short string of comments in code examples to enhance understanding
- Show expected output where appropriate
- If the project is complex, consider a step-by-step tutorial

### 9. Troubleshooting/FAQ
- Address common issues that might be apparent from the code
- Include solutions to these potential problems
- If error handling is mentioned in summaries, extract into useful tips

### 10. Contributing
- Basic guidelines for contributors
- Link to CONTRIBUTING.md if it exists
- Instructions for development setup
- Code style/formatting requirements if evident from code

### 11. License
- Specify the license type
- Link to full license text
- If no license is found, recommend choosing one

## Formatting Guidelines

1. Use proper Markdown syntax and hierarchical structure
2. Use headings (# for main sections, ## for subsections, ### for minor sections)
3. Use code blocks with syntax highlighting for all code examples:
   ```python
   # Example Python code
   def example_function():
       return "This is an example"

- Use tables for structured information (options, parameters, etc.)
- Use bullet points for lists of features, steps, or requirements
- Include a table of contents for longer READMEs
- Use bold and italics for emphasis, not ALL CAPS
- Use horizontal rules (---) to separate major sections if the README is long

### Handling Incomplete Information
When information is unclear or missing, indicate very clearly when you're making an 
assumption: "Based on the code structure, this appears to be...". BE VERY EXTREMELY CLEAR ON THIS!

**DO NOT** invent specific functionality or features. You should only stick to what is given in the code. I repeat, DO NOT invent anything.
- For critical missing information, suggest what should be added: "Developers should document the authentication process here"
- Prioritize accuracy over completeness

## Final Deliverable Requirements: 
- Produce a comprehensive README.md in proper Markdown format
- Balance between thoroughness and readability
- Adapt content based on project type:
- Libraries need more API documentation
- CLI tools need more command options
- Web applications need more setup/deployment details
- Optimize for both new users (getting started) and experienced users (reference)

The guide must serve as a useful tool for other developers to understand and use the project effectively. 
Remember, the README is often the first point of contact for new users, so make it count! 
If the user can't understand your project from the README, you've failed.

{{ summaries_text }}
"""

## using the markers as a reference to find the "root" of the project. going to assume this is standard practice
## for most projects
def find_project_root():
    ROOT_MARKERS = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json']
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prev_dir = None
    while current_dir != prev_dir:
        for marker in ROOT_MARKERS:
            if os.path.exists(os.path.join(current_dir, marker)):
                return current_dir
        prev_dir = current_dir
        current_dir = os.path.dirname(current_dir)
    return os.path.dirname(os.path.abspath(__file__))

def summarize_chunk(chunk_text):
    prompt = f"Summarize this text:\n\n{chunk_text}\n\nSummary:"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Summary failed, fuck it."

def process_chunk_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    summary = summarize_chunk(content)
    return {'file': file_path, 'summary': summary}

def extract_project_info():
    """Extract project information from pyproject.toml"""
    project_info = {
        "name": "docdog",
        "build_system": "setuptools",
        "dependencies": []
    }
    
    try:
        project_root = find_project_root()
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        
        if os.path.exists(pyproject_path):
            with open(pyproject_path, 'r') as f:
                content = f.read()
                
            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            if name_match:
                project_info["name"] = name_match.group(1)
            
            if "poetry" in content:
                project_info["build_system"] = "poetry"
            elif "setuptools" in content:
                project_info["build_system"] = "setuptools"
                
            deps_match = re.findall(r'dependencies\s*=\s*$$ ([\s\S]*?) $$', content)
            if deps_match:
                deps_text = deps_match[0]
                deps = re.findall(r'"([^"]+)"', deps_text)
                project_info["dependencies"] = deps
    except Exception as e:
        logger.error(f"Error extracting project info: {str(e)}")
    
    return project_info

def extract_structured_info(all_summaries):
    """Convert raw summaries into structured information"""
    structured_info = ""
    
    commands = extract_command_patterns()
    if commands:
        structured_info += "## Commands\n"
        for cmd, desc in commands.items():
            structured_info += f"- `{cmd}`: {desc}\n"
        structured_info += "\n"
    
    functions = []
    classes = []
    
    for summary in all_summaries:
        fn_matches = re.findall(r'def\s+(\w+)\s*$$ ([^)]*) $$', summary.get('summary', ''))
        for name, params in fn_matches:
            functions.append({
                "name": name,
                "params": params,
                "description": extract_description(summary.get('summary', ''), name)
            })
        
        class_matches = re.findall(r'class\s+(\w+)', summary.get('summary', ''))
        for name in class_matches:
            classes.append({
                "name": name,
                "description": extract_description(summary.get('summary', ''), name)
            })
    
    if functions:
        structured_info += "## Functions\n"
        for fn in functions:
            structured_info += f"- `{fn['name']}({fn['params']})`: {fn['description']}\n"
        structured_info += "\n"
    
    if classes:
        structured_info += "## Classes\n"
        for cls in classes:
            structured_info += f"- `{cls['name']}`: {cls['description']}\n"
        structured_info += "\n"
    
    structured_info += "## Raw Summaries\n"
    for data in all_summaries:
        structured_info += f"### {os.path.basename(data['file'])}\n"
        structured_info += f"{data['summary']}\n\n"
    
    return structured_info

def extract_command_patterns():
    """Extract command patterns from argparse in main.py"""
    commands = {}
    
    try:
        commands["docdog"] = "Generate documentation for a project"
        commands["docdog -o OUTPUT"] = "Specify output file"
        commands["docdog -t TITLE"] = "Set project title"
        commands["docdog -m MODEL"] = "Specify OpenAI model"
        commands["docdog --test-chunks"] = "Test chunking without generating documentation"
    except Exception as e:
        logger.error(f"Error extracting commands: {str(e)}")
    
    return commands

def extract_description(text, identifier):
    """Extract a description for a function or class from text"""
    pattern = f"{identifier}[:\s]+(.*?)(?:\n\n|\Z)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return "No description available"

def generate_readme_content(all_summaries, model, template_str, project_title=None):
    project_info = extract_project_info()
    structured_summaries = extract_structured_info(all_summaries)
    template_variables = {
        "project_name": project_title or project_info.get("name", "DocDog"),
        "build_system": project_info.get("build_system", "setuptools"),
        "installation_command": f"pip install {project_info.get('name', 'docdog')}",
        "dependencies": project_info.get("dependencies", []),
        "summaries_text": structured_summaries,
    }
    template = Template(template_str)
    prompt = template.render(**template_variables)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating README: {str(e)}")
        return f"# README.md\n\nError generating documentation: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="DocDog - AI Document & Code Summarizer")
    parser.add_argument("files", nargs="*", help="Files to process. If none, processes all files in the current directory.")
    parser.add_argument("-o", "--output", default="README.md", help="Output file (default: README.md)")
    parser.add_argument("-t", "--title", help="Project title")
    parser.add_argument("-m", "--model", default="gpt-3.5-turbo", help="OpenAI model to use (default: gpt-3.5-turbo)")
    parser.add_argument("-p", "--prompt-template", help="Path to custom prompt template file")
    parser.add_argument("-c", "--config", default="config.json", help="Config file path (default: config.json)")
    parser.add_argument("--test-chunks", action="store_true", help="Only perform chunking without summarization")
    args = parser.parse_args()
    default_config = {
        "num_chunks": 5,
        "model": "gpt-4o-mini",
        "max_tokens": 1500,
        "temperature": 0.7,
        "allowed_extensions": [".txt", ".md", ".py", ".json", ".toml"]
    }
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = default_config
    config['model'] = args.model or config.get('model', default_config['model'])
    config['num_chunks'] = config.get('num_chunks', default_config['num_chunks'])
    config['prompt_template'] = args.prompt_template or config.get('prompt_template', None)
    
    chunk_files = chunk_project(find_project_root(), output_dir="chunks", config=config)
    all_summaries = batch_summarize_chunks(chunk_files, client, config['model'], verbose=True)

    if args.test_chunks:
            return

    chunk_contents = {}
    for chunk_path in args.files:
        try:
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_contents[chunk_path] = f.read()
        except Exception as e:
            logger.error(f"Error reading {chunk_path}: {str(e)}")
            chunk_contents[chunk_path] = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(summarize_chunk_with_retry, chunk_path, chunk_contents[chunk_path], client, config['model'])
            for chunk_path in args.files if chunk_contents[chunk_path] is not None
        ]
        all_summaries = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    if config['prompt_template'] and os.path.exists(config['prompt_template']):
        with open(config['prompt_template'], "r") as f:
            template_str = f.read()
    else:
        template_str = DEFAULT_PROMPT_TEMPLATE
    
    if all_summaries:
        ai_content = generate_readme_content(all_summaries, config['model'], template_str, args.title)
    else:
        ai_content = "# README.md\n\nNo fucking files processed."
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    template = Template("""
{{ ai_content }}

---
*Generated by DocDog on {{ current_date }}*
""")
    final_content = template.render(ai_content=ai_content, current_date=current_date)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(final_content)

if __name__ == "__main__":
    main()

class SummaryCache:
    def __init__(self, cache_dir=".summary_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def _get_cache_key(self, content: str, model: str) -> str:
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return f"{model}_{content_hash}"
    
    def _get_cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, key)
    
    def get(self, content: str, model: str) -> str:
        key = self._get_cache_key(content, model)
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        return None
    
    def set(self, content: str, model: str, summary: str) -> None:
        key = self._get_cache_key(content, model)
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(summary)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

summary_cache = SummaryCache()

def summarize_chunk_with_retry(chunk_path: str, content: str, client, model: str = "gpt-3.5-turbo", 
                               max_retries: int = 3, backoff_factor: float = 1.5) -> Dict[str, Any]:
    if content is None:
        return {'file': chunk_path, 'summary': "Error reading file", 'error': True}
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    cache_key = f"{model}_{content_hash}"
    if cache_key in memory_cache:
        logger.info(f"Memory cache hit for {os.path.basename(chunk_path)}")
        return {'file': chunk_path, 'summary': memory_cache[cache_key], 'cached': True}
    cached_summary = summary_cache.get(content, model)
    if cached_summary:
        memory_cache[cache_key] = cached_summary
        logger.info(f"File cache hit for {os.path.basename(chunk_path)}")
        return {'file': chunk_path, 'summary': cached_summary, 'cached': True}
    retry_count = 0
    wait_time = 1.0
    while retry_count < max_retries:
        try:
            prompt = f"Summarize this text:\n\n{content}\n\nSummary:"
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            summary = response.choices[0].message.content.strip()
            logger.info(f"Successfully summarized {os.path.basename(chunk_path)}")
            memory_cache[cache_key] = summary
            summary_cache.set(content, model, summary)
            return {'file': chunk_path, 'summary': summary, 'cached': False}
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"API error on attempt {retry_count}: {str(e)}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                wait_time *= backoff_factor
            else:
                logger.error(f"Failed to summarize {chunk_path} after {max_retries} attempts: {str(e)}")
                return {'file': chunk_path, 'summary': f"Summary generation failed: {str(e)}", 'error': True}
  