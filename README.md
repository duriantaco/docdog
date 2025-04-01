# DocDog

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview

DocDog is an AI-powered tool that streamlines the documentation process for software projects by automatically generating high-quality README files. It analyzes the project's codebase, including source code, documentation, and configuration files, to extract relevant information and generate a comprehensive README tailored to the project's specifics.

DocDog aims to save developers time and effort by automating the tedious task of writing documentation, while ensuring accuracy and completeness by directly referencing the codebase. It provides a convenient solution for keeping documentation up-to-date as the project evolves.

## Features

- **Code Analysis**: Thoroughly examines the project's codebase, including source code files, documentation, and configuration files.
- **Parallel Processing**: Utilizes parallel processing techniques to efficiently handle large codebases.
- **Template Support**: Allows the use of custom templates for README generation, ensuring consistency with project branding and style guidelines.
- **Automatic README Generation**: Generates a complete README file with sections for overview, installation, usage, API documentation, configuration, examples, troubleshooting, contributing guidelines, and license information.
- **Reasoning Documentation**: Provides transparency by documenting the reasoning behind the generated content, referencing specific code snippets and files that influenced the decisions.

## Installation

```bash
pip install docdog
```

## Quick Start Guide

To generate a README for your project, simply run:

```
docdog
```

This command will analyze your project's codebase and generate a comprehensive README file named `README.md` in the current directory.

## Usage

```
usage: docdog [-h] [-o OUTPUT] [-m MODEL] [--reasoning] [-p PROMPT_TEMPLATE] [--max-iterations MAX_ITERATIONS] [--workers WORKERS] [--cache-size CACHE_SIZE]

AI-powered README generator for software projects

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file for the generated README (default: README.md)
  -m MODEL, --model MODEL
                        Name of the AI model to use for generation (default: claude-v1)
  --reasoning           Include reasoning behind the generated content
  -p PROMPT_TEMPLATE, --prompt-template PROMPT_TEMPLATE
                        Path to a custom prompt template file
  --max-iterations MAX_ITERATIONS
                        Maximum number of iterations for analysis (default: 15)
  --workers WORKERS, -w WORKERS
                        Number of worker threads (default: auto)
  --cache-size CACHE_SIZE
                        Size of the LRU cache (default: 128)
```

## API Documentation

### `docdog.tools.Tools`

The `Tools` class provides utility methods for interacting with the project's files and directories.

- `list_files(directory: str) -> str`: List files in a given directory within the project.
- `read_file(file_path: str) -> str`: Read the content of a file within the project.
- `batch_read_files(file_paths: list) -> str`: Read the contents of multiple files within the project.

### `docdog.chunking.chunk_project`

The `chunk_project` function is responsible for splitting the project's files into smaller chunks for efficient processing.

```python
def chunk_project(project_root, output_dir="chunks", config=None) -> List[str]:
    ...
```

- `project_root` (str): The root directory of the project.
- `output_dir` (str, optional): The directory to store the generated chunks (default: `"chunks"`).
- `config` (dict, optional): A configuration dictionary specifying chunking options.

Returns a list of file paths for the generated chunks.

### `docdog.utils.sanitize_prompt`

The `sanitize_prompt` function is a utility for sanitizing prompts to prevent Unicode obfuscation and prompt injection attacks.

```python
def sanitize_prompt(prompt: str) -> str:
    ...
```

- `prompt` (str): The input prompt to sanitize.

Returns the sanitized prompt as a string.

## Configuration

DocDog can be configured through command-line arguments and environment variables.

### Command-line Arguments

- `--output`: Specify the output file for the generated README (default: `README.md`).
- `--model`: Set the name of the AI model to use for generation (default: `claude-v1`).
- `--reasoning`: Include reasoning behind the generated content in a separate file (`reasoning.md`).
- `--prompt-template`: Provide a custom prompt template file for README generation.
- `--max-iterations`: Set the maximum number of iterations for the analysis phase (default: `15`).
- `--workers`: Specify the number of worker threads for parallel processing (default: automatically determined).
- `--cache-size`: Set the size of the LRU cache used for caching file operations (default: `128`).

### Environment Variables

- `ANTHROPIC_API_KEY`: Set your Anthropic API key for authentication.

## Examples and Use Cases

### Basic Usage

```bash
docdog
```

This command will generate a `README.md` file in the current directory based on the project's codebase.

### Custom Output File

```bash
docdog --output project_readme.md
```

Generate the README and save it to `project_readme.md` instead of the default `README.md`.

### Include Reasoning

```bash
docdog --reasoning
```

In addition to the `README.md` file, this command will generate a `reasoning.md` file documenting the reasoning behind the generated content, referencing specific code snippets and files.

### Custom Prompt Template

```bash
docdog --prompt-template custom_template.txt
```

Use a custom prompt template file (`custom_template.txt`) for README generation instead of the default template.

### Supported Models

At the moment, docdog only supports `claude-3-sonnet-20240229`. 

## Troubleshooting/FAQ

### Missing API Key

If you encounter an error related to a missing API key, ensure that you have set the `ANTHROPIC_API_KEY` environment variable with your valid Anthropic API key.

### Incomplete Documentation Generation

In some cases, DocDog may not be able to generate a complete README due to limitations in analyzing the codebase or encountering unsupported file types. If you encounter an incomplete README, check the log files for more information and consider running DocDog again with different configurations or providing additional context.

## Contributing

Contributions to DocDog are welcome! Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute, including reporting issues, suggesting enhancements, and submitting pull requests.

## License

DocDog is released under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).

---
*Generated by DocDog on 2025-05-05*

---
*Generated by DocDog on 2025-04-01*