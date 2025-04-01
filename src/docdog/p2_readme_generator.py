import logging
import traceback

logger = logging.getLogger(__name__)

def generate_readme(client, model, messages, analyzed_chunks, expected_chunks):
    """
    Phase 2: Generate README based on analyzed project chunks.
    """
    
    generation_prompt = (
        "Now that you have analyzed all available chunks, please generate the complete README.md file "
        "based on the code you've examined. Follow the structure specified in the initial instructions. "
        "Your response should start with 'Final README:' followed by the complete README content."
    )
    
    if len(analyzed_chunks) < len(expected_chunks):
        generation_prompt += f"\n\nNote: You've only been able to analyze {len(analyzed_chunks)} out of {len(expected_chunks)} chunks. Please generate the best README possible with the information you have."
    
    messages.append({"role": "user", "content": generation_prompt})
    
    readme_content = None
    reasoning_content = None
    full_text = ""
    
    try:
        logger.info("Requesting README generation from Claude")
        response = client.messages.create(
            model=model,
            messages=messages,
            max_tokens=4000
        )
        
        full_text = "".join([c.text for c in response.content if c.type == "text"])
        
        if "Final README:" in full_text:
            parts = full_text.split("Final README:", 1)
            if len(parts) > 1:
                readme_and_reasoning = parts[1].strip()
                if "Reasoning:" in readme_and_reasoning:
                    readme_content, reasoning_content = readme_and_reasoning.split("Reasoning:", 1)
                    readme_content = readme_content.strip()
                    reasoning_content = reasoning_content.strip()
                else:
                    readme_content = readme_and_reasoning
            else:
                readme_content = full_text.strip()
        else:
            readme_content = full_text.strip()
        
        if readme_content:
            logger.info("README content successfully generated")
        else:
            logger.warning("No README content found in the response")
    
    except Exception as e:
        logger.error(f"Error in README generation: {str(e)}")
        traceback.print_exc()
    
    return readme_content, reasoning_content, full_text