<p align="center">
  <img src="assets/DOCDOG.png" alt="DOCDOG Logo" width="300">
</p>

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://github.com/duriantaco/docdog/blob/main/License) [![Version](https://img.shields.io/badge/version-0.0.2-blue.svg)](https://github.com/duriantaco/docdog/releases)


## Overview

DocDog is an AI-powered tool that automatically generates comprehensive README documentation for software projects. By analyzing the project's source code, configuration files, and existing documentation, DocDog can create a well-structured README file covering installation, usage, API documentation, examples, and more.

The tool aims to streamline the documentation process for developers, saving time and effort while ensuring accurate and up-to-date documentation that reflects the project's current state. With DocDog, you can focus on writing code while keeping your project's documentation in sync.

## Features

- **Automatic README Generation**: DocDog analyzes your project's codebase, configuration files, and existing documentation to generate a comprehensive README file.
- **Structured Documentation**: The generated README follows a standardized structure, including sections for installation, usage, API documentation, examples, troubleshooting, and more.
- **Code Analysis**: DocDog examines your code to extract relevant information, such as function signatures, docstrings, and code comments, to include in the documentation.
- **Configuration Options**: Customize the documentation generation process by specifying configuration options, such as allowed file extensions, output directory, and more.
- **Parallel Processing**: Leverage parallel processing for efficient chunking and analysis of large codebases.
- **Template Support**: Use built-in or custom templates to control the structure and formatting of the generated README.
- **Reasoning Documentation**: Optionally include the reasoning behind the generated content in a separate file (`reasoning.md`) for transparency and understanding the AI's decision-making process.

## Installation

```bash
# Clone the repository
git clone https://github.com/duriantaco/docdog.git
cd docdog

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install DocDog
pip install .
```

## Quick Start Guide

To generate a README for your project, navigate to your project's root directory and run:

```bash
docdog
```

This will analyze your project's files and generate a `README.md` file in the current directory.

## Usage

```
usage: docdog [-h] [-o OUTPUT] [-m MODEL] [--reasoning] [-p PROMPT_TEMPLATE] [--max-iterations MAX_ITERATIONS] [--workers WORKERS] [--cache-size CACHE_SIZE]

DocDog - AI Document & Code Summarizer

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file path for the generated README (default: README.md)
  -m MODEL, --model MODEL
                        AI model to use for documentation generation (default: gpt-4o-mini)
  --reasoning           Include reasoning behind the generated content
  -p PROMPT_TEMPLATE, --prompt-template PROMPT_TEMPLATE
                        Path to a custom prompt template file
  --max-iterations MAX_ITERATIONS
                        Maximum number of iterations for the AI model (default: 15)
  --workers WORKERS, -w WORKERS
                        Number of worker threads (default: auto)
  --cache-size CACHE_SIZE
                        Size of the LRU cache (default: 128)
```

## API Documentation

### MCPTools

The `MCPTools` class provides a set of tools for interacting with the project's codebase, such as listing files, reading file contents, and batch reading multiple files. The class supports caching for improved performance and parallel processing for batch operations.

#### `__init__(project_root, max_workers=None, cache_size=128)`

Initializes the `MCPTools` instance.

- `project_root` (str): The root directory of the project.
- `max_workers` (int, optional): The maximum number of worker threads for parallel processing. If `None`, the number of workers is determined automatically.
- `cache_size` (int, optional): The size of the LRU cache for caching file reads and listings. Default is 128.

#### `list_files(directory)`

Lists files in the specified directory within the project root, excluding ignored patterns.

- `directory` (str): The directory path relative to the project root.
- Returns: A string containing the list of files, with one file path per line.

#### `read_file(file_path)`

Reads the content of a file within the project root.

- `file_path` (str): The file path relative to the project root.
- Returns: A string containing the file content. For Python files, it includes the content, docstrings, and comments.

#### `batch_read_files(file_paths)`

Reads the contents of multiple files within the project root in parallel.

- `file_paths` (list): A list of file paths relative to the project root.
- Returns: A JSON string containing a list of dictionaries, where each dictionary represents a file with its content or error message.

#### `handle_tool_call(tool_name, tool_input)`

Handles tool calls from the AI assistant, dispatching to the appropriate tool based on the `tool_name`.

- `tool_name` (str): The name of the tool to execute.
- `tool_input` (dict): The input parameters for the tool.
- Returns: The result of the tool execution.

### Chunking

The `chunking` module provides functionality for splitting the project's files into chunks for efficient processing by the AI assistant.

#### `chunk_project(project_root, output_dir="chunks", config=None)`

Chunks the project's files into smaller files, splitting them based on token count or in parallel.

- `project_root` (str): The root directory of the project.
- `output_dir` (str, optional): The directory to store the chunked files. Default is "chunks".
- `config` (dict, optional): A configuration dictionary containing chunking options. If `None`, default options are used.
- Returns: A list of file paths for the created chunk files.

### Other Modules

- `sanitize_prompt`: A utility function for sanitizing prompts to prevent Unicode obfuscation and prompt injection attacks.
- `templates`: Contains template files for the initial prompt, validation prompt, and reasoning instructions.

## Configuration

DocDog can be configured using environment variables, command-line arguments, and a configuration file.

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key. Required for DocDog to function.

### Command-line Arguments

- `--output`: Specify the output file path for the generated README (default: `README.md`).
- `--model`: Set the AI model to use for documentation generation (default: `gpt-4o-mini`).
- `--reasoning`: Include the reasoning behind the generated content in a separate file (`reasoning.md`).
- `--prompt-template`: Path to a custom prompt template file.
- `--max-iterations`: Set the maximum number of iterations for the AI model (default: 15).
- `--workers`: Specify the number of worker threads for parallel processing (default: auto-detected).
- `--cache-size`: Set the size of the LRU cache for caching file reads and listings (default: 128).

### Configuration File

DocDog supports a configuration file (`config.json`) for additional settings. The default configuration is:

```json
{
    "num_chunks": 5,
    "model": "gpt-4o-mini",
    "max_tokens": 5000,
    "temperature": 0.7,
    "verbose": false,
    "allowed_extensions": [
        ".txt", ".md", ".py", ".pdf", ".sh", ".json", ".yaml", ".ipynb",
        ".js", ".tsx", ".ts", "jsx", ".html", ".css", ".csv", ".xml",
        ".yml", ".sql", ".java", ".php", ".rb", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".go", ".rs", ".swift", ".kt", ".m", ".pl",
        ".r", ".lua", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".psd1",
        ".ps1xml", ".pssc", ".psc1", ".pssc", ".pss1", ".pssm", ".pssc", ".pss"
    ]
}
```

You can create a `config.json` file in your project's root directory to override these settings.

## Examples and Use Cases

### Basic Usage

```bash
docdog
```

This will generate a `README.md` file in the current directory, analyzing all files in the project with the default configuration.

### Specifying an Output File

```bash
docdog --output docs/PROJECT_README.md
```

This will generate the README file as `docs/PROJECT_README.md` instead of the default `README.md`.

### Including Reasoning

```bash
docdog --reasoning
```

This will generate a `reasoning.md` file alongside the `README.md`, explaining the reasoning behind the generated content.

### Using a Custom Prompt Template

```bash
docdog --prompt-template custom_prompt.txt
```

This will use the `custom_prompt.txt` file as the prompt template for the AI model, allowing you to customize the structure and content of the generated README.

### Adjusting Configuration

You can create a `config.json` file in your project's root directory to adjust settings like the number of chunks, AI model, temperature, and allowed file extensions.

```json
{
    "num_chunks": 10,
    "model": "gpt-4",
    "max_tokens": 6000,
    "temperature": 0.8,
    "allowed_extensions": [".py", ".md", ".txt", ".js"]
}
```

This configuration will create 10 chunks, use the `gpt-4` model with a temperature of 0.8, limit the token count to 6000, and only analyze Python, Markdown, text, and JavaScript files.

## Troubleshooting/FAQ

### Error: `ANTHROPIC_API_KEY not found in environment variables`

Make sure you have set the `ANTHROPIC_API_KEY` environment variable with your valid Anthropic API key. You can set it temporarily in your shell session or add it to your shell configuration file (e.g., `.bashrc`, `.zshrc`).

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

### Incomplete or Missing Information

If the generated README is missing important information or sections, it's likely due to the tool being unable to find relevant information in your project's files. Double-check that your source code and configuration files are up-to-date and well-documented (e.g., using docstrings, comments, and descriptive variable/function names).

### Unsatisfactory README Quality

If the generated README quality is not satisfactory, you can try the following:

- Increase the `max_iterations` option to allow the AI model more iterations for refining the output.
- Use a more capable AI model (e.g., `gpt-4`) by setting the `--model` option.
- Adjust the `temperature` setting in the `config.json` file to control the randomness and creativity of the generated text.
- Provide a custom prompt template with more specific instructions tailored to your project.

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request on the [GitHub repository](https://github.com/duriantaco/docdog). See the [CONTRIBUTING.md](CONTRIBUTING.md) file for more details.

## License

DocDog is released under the [Apache 2.0 License](https://github.com/duriantaco/docdog/blob/main/License).

---

*Generated by DocDog on 2025-03-25*

---
*Generated by DocDog on 2025-03-25*