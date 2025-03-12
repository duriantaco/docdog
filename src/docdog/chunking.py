import os
import fnmatch
import tiktoken
from concurrent.futures import ThreadPoolExecutor

def count_tokens(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))
    except Exception:
        return 0

## checking if this is the most efficient way
def write_chunk(i, chunk_files_list, output_dir, project_root):
    chunk_path = os.path.join(output_dir, f"chunk-{i}.txt")
    with open(chunk_path, 'w', encoding='utf-8') as chunk_file:
        for file_path in chunk_files_list:
            rel_path = os.path.relpath(file_path, project_root)
            chunk_file.write(f"========================================\n")
            chunk_file.write(f"File: {rel_path}\n")
            chunk_file.write(f"========================================\n")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            chunk_file.write(content)
            chunk_file.write("\n\n")
    return chunk_path

def chunk_project(project_root, output_dir="chunks", config=None):
    if config is None:
        config = {
            "num_chunks": 5,
            "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml"]
        }
    
    num_chunks = config.get("num_chunks", 5)
    allowed_extensions = config.get("allowed_extensions", [".py", ".md", ".txt", ".json", ".toml"])
    
    ## prob gotta add more here to ignore more files. especially the big ones ... 
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
        "**/chunk-*.txt"
    ]
    
    def collect_files():
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
    
    all_files = collect_files()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        token_counts = list(executor.map(count_tokens, all_files))
    
    file_token_pairs = [(file, count) for file, count in zip(all_files, token_counts) if count > 0]
    file_token_pairs.sort(key=lambda x: x[1], reverse=True)
    
    chunks = [[] for _ in range(num_chunks)]
    chunk_totals = [0] * num_chunks
    
    for file, tokens in file_token_pairs:
        min_chunk = min(range(num_chunks), key=lambda i: chunk_totals[i])
        chunks[min_chunk].append(file)
        chunk_totals[min_chunk] += tokens
    
    os.makedirs(output_dir, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        futures = [executor.submit(write_chunk, i, chunk_files_list, output_dir, project_root) for i, chunk_files_list in enumerate(chunks) if chunk_files_list]
        chunk_files = [future.result() for future in futures]
    
    return chunk_files