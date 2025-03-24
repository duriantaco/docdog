import os
import hashlib
import time
import logging
from typing import List, Dict, Any
import tiktoken

logger = logging.getLogger(__name__)

memory_cache = {}

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
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    cache_key = f"{model}_{content_hash}"

    if cache_key in memory_cache:
        logger.info(f"Memory cache hit for {os.path.basename(chunk_path)}")
        return {'file': chunk_path, 'summary': memory_cache[cache_key], 'cached': True}

    cached_summary = summary_cache.get(content, model)
    if cached_summary:
        logger.info(f"File cache hit for {os.path.basename(chunk_path)}")
        memory_cache[cache_key] = cached_summary
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

def batch_summarize_chunks(chunk_paths: List[str], client, model: str = "gpt-3.5-turbo", 
                           batch_size: int = 5, delay_between_batches: float = 1.0, verbose: bool = False) -> List[Dict[str, Any]]:
    if verbose:
        logger.info(f"Summarizing {len(chunk_paths)} chunks with dynamic batching")

    results = []
    uncached_chunks = []
    encoding = tiktoken.get_encoding("cl100k_base")
    max_tokens = 16000 if model == "gpt-3.5-turbo" else 8000 if model == "gpt-4" else 16000

    for chunk_path in chunk_paths:
        try:
            with open(chunk_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            cache_key = f"{model}_{content_hash}"

            if cache_key in memory_cache:
                results.append({'file': chunk_path, 'summary': memory_cache[cache_key], 'cached': True})
            else:
                cached_summary = summary_cache.get(content, model)
                if cached_summary:
                    memory_cache[cache_key] = cached_summary
                    results.append({'file': chunk_path, 'summary': cached_summary, 'cached': True})
                else:
                    token_count = len(encoding.encode(content))
                    uncached_chunks.append((chunk_path, content, token_count))
        except Exception as e:
            logger.error(f"Error reading {chunk_path}: {str(e)}")
            results.append({'file': chunk_path, 'summary': f"Error reading file: {str(e)}", 'error': True})

    if not uncached_chunks:
        if verbose:
            logger.info("All chunks were cached")
        return results

    batches = []
    current_batch = []
    current_token_count = 0

    for chunk in uncached_chunks:
        chunk_path, content, chunk_tokens = chunk
        if current_token_count + chunk_tokens + 100 > max_tokens:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_token_count = 0
        current_batch.append(chunk)
        current_token_count += chunk_tokens

    if current_batch:
        batches.append(current_batch)

    for batch_idx, batch in enumerate(batches):
        if verbose:
            logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} chunks")

        batch_prompt = "Summarize the following chunks individually:\n\n"
        for idx, (chunk_path, content, _) in enumerate(batch):
            batch_prompt += f"Chunk {idx + 1}:\n{content}\n\n"
        batch_prompt += "Provide a summary for each chunk, separated by '---'."

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=0.5
            )
            response_text = response.choices[0].message.content.strip()
            summaries = [s.strip() for s in response_text.split("---") if s.strip()]
            if len(summaries) != len(batch):
                raise ValueError(f"Mismatch in summary count: expected {len(batch)}, got {len(summaries)}")
            for (chunk_path, content, _), summary in zip(batch, summaries):
                cache_key = f"{model}_{hashlib.md5(content.encode('utf-8')).hexdigest()}"
                memory_cache[cache_key] = summary
                summary_cache.set(content, model, summary)
                results.append({'file': chunk_path, 'summary': summary, 'cached': False})
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1} failed: {e}. Processing individually.")
            for chunk_path, content, _ in batch:
                summary_data = summarize_chunk_with_retry(chunk_path, content, client, model)
                results.append(summary_data)

        if batch_idx < len(batches) - 1:
            time.sleep(delay_between_batches)

    return results