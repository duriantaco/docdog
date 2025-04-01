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
    prompt = re.sub(r'[\x00-\x08\x0B-\x1F\x7F-\x9F]', '', prompt)
    prompt = re.sub(r'[\u2028\u2029\u0085\u000C\u000D]', '', prompt)
    
    allowed_categories = {'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Nl', 'No', 
                         'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po', 
                         'Sm', 'Sc', 'Sk', 'So', 'Zs'}
    
    filtered_chars = []
    for c in prompt:
        if c in {'\n', '\t', ' '} or unicodedata.category(c) in allowed_categories:
            filtered_chars.append(c)
    prompt = ''.join(filtered_chars)
    
    lines = prompt.split('\n')
    sanitized_lines = []
    suspicious_patterns = [
        r"ignore all previous instructions",
        r"forget everything",
        r"execute the following",
        r"run the following",
        r"do not answer the following question",
        r"do not respond to the following prompt",
        r"do not answer the following"
    ]

    for line in lines:
        if any(re.search(pattern, line.lower()) for pattern in suspicious_patterns):
            continue
        sanitized_lines.append(line)
    
    prompt = '\n'.join(sanitized_lines)
    
    return prompt