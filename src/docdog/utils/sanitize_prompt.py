import unicodedata
import re

def sanitize_prompt(prompt: str) -> str:
    """
    Sanitize a prompt to prevent Unicode obfuscation and prompt injection attacks.
    
    Args:
        prompt (str): The input prompt to clean.
    
    Returns:
        str: The sanitized prompt.
    """
    prompt = unicodedata.normalize('NFKC', prompt)
    prompt = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', prompt)
    
    # L (letters), N (numbers), P (punctuation), S (symbols), Z (separators)
    allowed_categories = {'L', 'N', 'P', 'S', 'Z'}
    prompt = ''.join(c for c in prompt if unicodedata.category(c)[0] in allowed_categories)
    
    lines = prompt.split('\n')
    sanitized_lines = []
    suspicious_patterns = [
        r"ignore all previous instructions",
        r"forget everything",
        r"execute the following",
    ]
    for line in lines:
        if any(re.search(pattern, line.lower()) for pattern in suspicious_patterns):
            continue 
        sanitized_lines.append(line)
    prompt = '\n'.join(sanitized_lines)
    
    return prompt