import os
import logging

logger = logging.getLogger(__name__)

def validate_readme(client, model, messages, full_text, readme_content, reasoning_content, templates_dir):
    """
    Phase 3: Validate and potentially improve the generated README.
    """
    
    messages.append({
        "role": "assistant", 
        "content": [{"type": "text", "text": full_text}]
    })
    
    validation_prompt_path = os.path.join(templates_dir, "validation_prompt.txt")
    if os.path.exists(validation_prompt_path):
        with open(validation_prompt_path, "r") as f:
            validation_prompt = f.read()
    else:
        logger.error(f"Validation prompt template not found at {validation_prompt_path}")
        return readme_content, reasoning_content
    
    messages.append({"role": "user", "content": validation_prompt})
    
    try:
        logger.info("Requesting README validation from Claude")
        response = client.messages.create(
            model=model,
            messages=messages,
            max_tokens=4000
        )
        
        validation_text = "".join([c.text for c in response.content if c.type == "text"])
        
        if "Improved README:" in validation_text:
            logger.info("README improvements suggested - using improved version")
            improved_parts = validation_text.split("Improved README:", 1)
            if len(improved_parts) > 1:
                improved_content = improved_parts[1].strip()
                if "Reasoning:" in improved_content:
                    improved_readme, improved_reasoning = improved_content.split("Reasoning:", 1)
                    readme_content = improved_readme.strip()
                    reasoning_content = improved_reasoning.strip()
                else:
                    readme_content = improved_content
        elif "README validation passed" in validation_text:
            logger.info("README validation passed - no changes needed")
        else:
            logger.info("README validation complete but unclear result - using original README")
    
    except Exception as e:
        logger.warning(f"Error in README validation: {str(e)}")
        logger.warning("Proceeding with unvalidated README")
    
    return readme_content, reasoning_content