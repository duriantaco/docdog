import os
import logging
import traceback

logger = logging.getLogger(__name__)

def analyze_project(client, model, messages, tools, doc_tools, expected_chunks, max_iterations):

    analyzed_chunks = set()
    analysis_iteration = 0
    
    while len(analyzed_chunks) < len(expected_chunks) and analysis_iteration < max_iterations:
        try:
            logger.info(f"Analysis iteration {analysis_iteration+1}/{max_iterations}")
            response = client.messages.create(
                model=model,
                messages=messages,
                tools=tools,
                max_tokens=4000
            )
            
            assistant_content = []
            for content in response.content:
                if content.type == "text":
                    assistant_content.append({"type": "text", "text": content.text})
                elif content.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": content.id,
                        "name": content.name,
                        "input": content.input
                    })
            
            messages.append({"role": "assistant", "content": assistant_content})
            
            tool_calls = [c for c in response.content if c.type == "tool_use"]
            if tool_calls:
                tool_results_content = []
                for tool_call in tool_calls:
                    tool_name = tool_call.name
                    tool_input = tool_call.input
                    tool_id = tool_call.id
                    
                    if tool_name == "read_file" and "file_path" in tool_input:
                        file_path = tool_input["file_path"]
                        chunk_name = os.path.basename(file_path)
                        if chunk_name in expected_chunks:
                            analyzed_chunks.add(chunk_name)
                            logger.info(f"Analyzed chunk: {chunk_name} ({len(analyzed_chunks)}/{len(expected_chunks)})")
                    elif tool_name == "batch_read_files" and "file_paths" in tool_input:
                        for file_path in tool_input["file_paths"]:
                            chunk_name = os.path.basename(file_path)
                            if chunk_name in expected_chunks:
                                analyzed_chunks.add(chunk_name)
                                logger.info(f"Analyzed chunk: {chunk_name} ({len(analyzed_chunks)}/{len(expected_chunks)})")
                    
                    logger.info(f"Claude requested tool: {tool_name} with input: {tool_input}")
                    result = doc_tools.handle_tool_call(tool_name, tool_input)
                    log_preview = result[:100] + "..." if len(result) > 100 else result
                    logger.info(f"Tool {tool_name} returned: {log_preview}")
                    
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })
                
                messages.append({"role": "user", "content": tool_results_content})
            
            for content in response.content:
                if content.type == "text" and "Final README:" in content.text:
                    logger.info("Claude prematurely generated a README during analysis. Continuing to ensure all chunks are analyzed.")
            
            analysis_iteration += 1
            
        except Exception as e:
            logger.error(f"Error in analysis phase: {str(e)}")
            traceback.print_exc()
            break
    
    if len(analyzed_chunks) < len(expected_chunks):
        logger.warning(f"Analysis incomplete: Only {len(analyzed_chunks)}/{len(expected_chunks)} chunks were analyzed")
        missing_chunks = set(expected_chunks) - analyzed_chunks
        logger.warning(f"Missing chunks: {', '.join(missing_chunks)}")
    else:
        logger.info(f"Successfully analyzed all {len(expected_chunks)} chunks")
    
    return messages, analyzed_chunks, analysis_iteration