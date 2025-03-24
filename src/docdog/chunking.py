import os
import fnmatch
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

try:
    from pykomodo.multi_dirs_chunker import ParallelChunker
    PYKOMODO_AVAILABLE = True
    logger.info("PyKomodo is available and will be used for chunking")
except ImportError:
    PYKOMODO_AVAILABLE = False
    logger.warning("PyKomodo not found. Will use built-in chunking logic")

    ## tiktoken will be the fallback assuming pykomodo has some bugs 
    try:
        import tiktoken
    except ImportError:
        logger.warning("tiktoken not installed. Token counting may be inaccurate")
        tiktoken = None

def count_tokens(file_path):
    """Count the number of tokens in a file using tiktoken or word count as fallback."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if tiktoken:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(content))
        else:
            return len(content.split())
    except Exception as e:
        logger.warning(f"Error counting tokens in {file_path}: {str(e)}")
        return 0

def write_chunk(i, chunk_files_list, output_dir, project_root):
    """Write a chunk file containing contents from multiple source files."""
    chunk_path = os.path.join(output_dir, f"chunk-{i}.txt")
    
    with open(chunk_path, 'w', encoding='utf-8') as chunk_file:
        chunk_file.write(f"================================================================================\n")
        chunk_file.write(f"CHUNK {i + 1} OF {len(chunk_files_list)}\n")
        chunk_file.write(f"================================================================================\n\n")
        
        for file_path in chunk_files_list:
            rel_path = os.path.relpath(file_path, project_root)
            chunk_file.write(f"========================================\n")
            chunk_file.write(f"File: {rel_path}\n")
            chunk_file.write(f"========================================\n")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                chunk_file.write(content)
            except Exception as e:
                chunk_file.write(f"[Error reading file: {str(e)}]\n")
            chunk_file.write("\n\n")
    
    return chunk_path

def fallback_chunk_project(project_root, output_dir="chunks", config=None):
    """
    Internal fallback chunking implementation when PyKomodo is not available.
    
    Args:
        project_root: Root directory of the project to chunk
        output_dir: Directory where chunk files will be written
        config: Configuration dictionary with options like num_chunks and allowed_extensions
        
    Returns:
        List of paths to the created chunk files
    """
    if config is None:
        config = {
            "num_chunks": 5,
            "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml"]
        }
    
    num_chunks = config.get("num_chunks", 5)
    allowed_extensions = config.get("allowed_extensions", [".py", ".md", ".txt", ".json", ".toml"])
    
    ignore_patterns = [
        "**/chunks/**",
        "**/.git/**",
        "**/__pycache__/**",
        "**/venv/**",
        "**/*.pyc",
        "**/*.pyo",
        "**/.env",
        "**/*.env",
        "**/node_modules/**",
        "**/.DS_Store",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.png",
        "**/*.gif",
    ]
    
    def collect_files():
        """Collect all files that match the allowed extensions and don't match ignore patterns."""
        all_files = []
        for root, _, files in os.walk(project_root):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)
                if any(fnmatch.fnmatch(rel_path, pattern) for pattern in ignore_patterns):
                    continue
                if any(file.endswith(ext) for ext in allowed_extensions):
                    all_files.append(full_path)
        return all_files
    
    logger.info(f"Collecting files from {project_root}...")
    all_files = collect_files()
    logger.info(f"Found {len(all_files)} files to process")
    
    if not all_files:
        logger.warning("No files found to chunk")
        return []
    
    logger.info("Counting tokens in files...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        token_counts = list(executor.map(count_tokens, all_files))
    
    file_token_pairs = [(file, count) for file, count in zip(all_files, token_counts) if count > 0]
    file_token_pairs.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Distributing {len(file_token_pairs)} files into {num_chunks} chunks")
    chunks = [[] for _ in range(num_chunks)]
    chunk_totals = [0] * num_chunks
    
    for file, tokens in file_token_pairs:
        min_chunk = min(range(num_chunks), key=lambda i: chunk_totals[i])
        chunks[min_chunk].append(file)
        chunk_totals[min_chunk] += tokens
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Writing {num_chunks} chunk files to {output_dir}")
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        futures = [executor.submit(write_chunk, i, chunk_files_list, output_dir, project_root) 
                  for i, chunk_files_list in enumerate(chunks) if chunk_files_list]
        chunk_files = [future.result() for future in futures]
    
    for i, total in enumerate(chunk_totals):
        logger.info(f"Chunk {i+1}: {total} tokens, {len(chunks[i])} files")
    
    return chunk_files

def chunk_project(project_root, output_dir="chunks", config=None):
    """
    Split a project into multiple chunks for processing by LLMs.
    Uses PyKomodo if available, otherwise falls back to built-in chunking.
    
    Args:
        project_root: Root directory of the project to chunk
        output_dir: Directory where chunk files will be written
        config: Configuration dictionary with options like num_chunks and allowed_extensions
        
    Returns:
        List of paths to the created chunk files
    """
    if config is None:
        config = {
            "num_chunks": 5,
            "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml"]
        }
    
    num_chunks = config.get("num_chunks", 5)
    allowed_extensions = config.get("allowed_extensions", [".py", ".md", ".txt", ".json", ".toml"])
    
    os.makedirs(output_dir, exist_ok=True)
    
    if PYKOMODO_AVAILABLE:
        try:
            logger.info("Using PyKomodo for chunking...")
            
            exclude_patterns = []
            for ext in set([".jpg", ".jpeg", ".png", ".gif", ".pyc", ".pyo", ".env"]):
                exclude_patterns.append(f"**/*{ext}")
            
            ignore_patterns = [
                "**/chunks/**",
                "**/.git/**",
                "**/__pycache__/**",
                "**/venv/**",
                "**/node_modules/**",
                "**/.DS_Store",
            ]
            
            chunker = ParallelChunker(
                equal_chunks=num_chunks,
                output_dir=output_dir,
                user_ignore=ignore_patterns,
                user_unignore=[f"*{ext}" for ext in allowed_extensions]
            )
            
            chunker.process_directory(project_root)
            
            chunk_files = [os.path.join(output_dir, f"chunk-{i}.txt") for i in range(num_chunks)]
            existing_chunks = [f for f in chunk_files if os.path.exists(f)]
            
            logger.info(f"PyKomodo created {len(existing_chunks)} chunk files")
            
            return existing_chunks
        
        except Exception as e:
            logger.error(f"Error using PyKomodo: {str(e)}")
            logger.info("Falling back to built-in chunking...")
    
    return fallback_chunk_project(project_root, output_dir, config)    