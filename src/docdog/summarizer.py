from openai import OpenAI
import os
from dotenv import load_dotenv
import time
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("ERROR: OPENAI_API_KEY not found in .env file.")
client = OpenAI(api_key=api_key)

def summarize_code_chunk(chunk, config=None):
    """
    Summarize a single code chunk using OpenAI API
    
    Args:
        chunk: Dictionary with name, type, and code for a function or class
        config: Configuration dictionary with model parameters
        
    Returns:
        Dictionary with name, type, and summary
    """
    if config is None:
        config = {
            "model": "gpt-3.5-turbo",
            "max_tokens": 150,
            "temperature": 0.7
        }
    
    verbose = config.get('verbose', False)
    
    prompt = (
        f"Generate a docstring or summary for the following {chunk['type']}:\n\n"
        f"{chunk['code']}\n\n"
        "Summary:"
    )
    
    try:
        if verbose:
            logger.info(f"Sending {chunk['type']} '{chunk['name']}' to OpenAI API...")
        
        response = client.chat.completions.create(
            model=config.get('model', "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.get('max_tokens', 150),
            temperature=config.get('temperature', 0.7)
        )
        
        summary = response.choices[0].message.content.strip()
        
        if verbose:
            logger.info(f"Received summary for {chunk['type']} '{chunk['name']}'")
        
        return {
            "name": chunk['name'],
            "type": chunk['type'],
            "summary": summary
        }
        
    except Exception as e:
        if verbose:
            logger.error(f"Failed to summarize {chunk['type']} '{chunk['name']}': {e}")
        
        return {
            "name": chunk['name'],
            "type": chunk['type'],
            "summary": f"Summary generation failed: {str(e)}"
        }

def summarize_chunks(chunks, config=None, verbose=False, max_workers=5):

    if config is None:
        config = {
            "model": "gpt-3.5-turbo",
            "max_tokens": 150,
            "temperature": 0.7,
            "verbose": verbose
        }
    
    if 'verbose' not in config:
        config['verbose'] = verbose
    
    summaries = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {
            executor.submit(summarize_code_chunk, chunk, config): chunk
            for chunk in chunks
        }
        
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                summary = future.result()
                summaries.append(summary)
                
                if verbose:
                    logger.info(f"Completed {len(summaries)}/{len(chunks)}: {chunk['type']} '{chunk['name']}'")
                
                # added delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                if verbose:
                    logger.error(f"Error processing {chunk['type']} '{chunk['name']}': {e}")
                
                summaries.append({
                    "name": chunk['name'],
                    "type": chunk['type'],
                    "summary": f"Summary generation failed: {str(e)}"
                })
    
    if verbose:
        logger.info(f"All {len(chunks)} code chunks processed")
    
    return summaries

def summarize_content(text, model="gpt-3.5-turbo", max_tokens=250, temperature=0.7):
    """
    Summarize arbitrary text content
    
    Args:
        text: Text content to summarize
        model: OpenAI model to use
        max_tokens: Maximum tokens in the summary
        temperature: Temperature for the model
        
    Returns:
        Generated summary text
    """
    try:
        # truncate superrrrr long texts to prevent token overflows
        max_input_chars = 12000
        if len(text) > max_input_chars:
            text = text[:max_input_chars] + "... [text truncated]"
        
        prompt = f"Summarize this text:\n\n{text}\n\nSummary:"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error summarizing content: {str(e)}")
        return f"Summary generation failed: {str(e)}"

def batch_summarize_files(file_paths, model="gpt-3.5-turbo", max_workers=5, verbose=False):
    """
    Summarize multiple files in parallel
    
    Args:
        file_paths: List of file paths to summarize
        model: OpenAI model to use
        max_workers: Maximum number of parallel workers
        verbose: Enable verbose logging
        
    Returns:
        List of dictionaries with file path and summary
    """
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a mapping of futures to file paths
        future_to_file = {}
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                if verbose:
                    logger.warning(f"File not found: {file_path}")
                continue
                
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Submit the task to the executor
                future = executor.submit(
                    summarize_content, 
                    content, 
                    model=model
                )
                future_to_file[future] = file_path
                
            except Exception as e:
                if verbose:
                    logger.error(f"Error reading {file_path}: {str(e)}")
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                summary = future.result()
                results.append({
                    'file': file_path,
                    'summary': summary
                })
                
                if verbose:
                    logger.info(f"Completed summary for {os.path.basename(file_path)}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                if verbose:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                
                results.append({
                    'file': file_path,
                    'summary': f"Summary generation failed: {str(e)}"
                })
    
    return results