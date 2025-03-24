import os
import logging
import shutil
from pykomodo.multi_dirs_chunker import ParallelChunker
from pykomodo.token_chunker import TokenBasedChunker

logger = logging.getLogger(__name__)
PYKOMODO_AVAILABLE = True  

def chunk_project(project_root, output_dir="chunks", config=None):
    if config is None:
        config = {
            "max_tokens_per_chunk": 100000,  
            "allowed_extensions": [".py", ".md", ".txt", ".json", ".toml"]
        }
    
    max_tokens_per_chunk = config.get("max_tokens_per_chunk", 100000)
    allowed_extensions = config.get("allowed_extensions", [".py", ".md", ".txt", ".json", ".toml"])
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if PYKOMODO_AVAILABLE:
        ignore_patterns = [
            "**/chunks/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/node_modules/**",
            "**/.DS_Store",
            "**/*.jpg",
            "**/*.jpeg",
            "**/*.png",
            "**/*.gif",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.env"
        ]
        
        try:
            logger.info("Using TokenBasedChunker...")
            
            temp_dir = os.path.join(output_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            analyzer = TokenBasedChunker(
                equal_chunks=1, 
                output_dir=temp_dir,
                user_ignore=ignore_patterns,
                user_unignore=[f"*{ext}" for ext in allowed_extensions],
                verbose=True
            )
            
            analyzer.process_directory(project_root)
            
            total_tokens = 0
            for path, content_bytes, _ in analyzer.loaded_files:
                try:
                    text = content_bytes.decode("utf-8", errors="replace")
                    total_tokens += analyzer.count_tokens(text)
                except:
                    pass
            
            num_chunks = max(1, (total_tokens + max_tokens_per_chunk - 1) // max_tokens_per_chunk)
            logger.info(f"Estimated {total_tokens} total tokens across all files")
            logger.info(f"Creating {num_chunks} chunks with approximately {max_tokens_per_chunk} tokens each")
            
            shutil.rmtree(temp_dir)
            
            chunker = TokenBasedChunker(
                equal_chunks=num_chunks,
                output_dir=output_dir,
                user_ignore=ignore_patterns,
                user_unignore=[f"*{ext}" for ext in allowed_extensions],
                verbose=True
            )
            
            chunker.process_directory(project_root)
            
            chunk_files = [f for f in os.listdir(output_dir) if f.startswith("chunk-") and f.endswith(".txt")]
            chunk_files = [os.path.join(output_dir, f) for f in chunk_files]
            chunk_files.sort()
            
            logger.info(f"Created {len(chunk_files)} chunk files")
            return chunk_files
            
        except Exception as e:
            logger.error(f"TokenBasedChunker approach failed: {str(e)}")
            logger.info("Falling back to ParallelChunker...")
            
            try:
                chunker = ParallelChunker(
                    equal_chunks=5,  
                    output_dir=output_dir,
                    user_ignore=ignore_patterns,
                    user_unignore=[f"*{ext}" for ext in allowed_extensions]
                )
                
                chunker.process_directory(project_root)
                
                chunk_files = [f for f in os.listdir(output_dir) if f.startswith("chunk-") and f.endswith(".txt")]
                chunk_files = [os.path.join(output_dir, f) for f in chunk_files]
                chunk_files.sort()
                
                logger.info(f"ParallelChunker created {len(chunk_files)} chunk files")
                return chunk_files
            
            except Exception as e:
                logger.error(f"ParallelChunker also failed: {str(e)}")
                return []
    
    return []