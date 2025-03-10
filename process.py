#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from pykomodo.multi_dirs_chunker import ParallelChunker
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import tempfile

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("ERROR: OPENAI_API_KEY not found in .env file.")

client = OpenAI(api_key=api_key)

def summarize_chunk(chunk_text):
    try:
        prompt = (
            "Summarize this text and explain why you included what you did:\n\n"
            f"{chunk_text}\n\n"
            "Summary:\n\nReasoning:"
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,  
            temperature=0.7  
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Error summarizing chunk: {e}")
        return "Summary failed due to an error."

def process_document(file_path, output_file="summary.md"):
    with tempfile.TemporaryDirectory() as temp_dir:
        chunker = ParallelChunker(
            max_chunk_size=1000,  
            output_dir=temp_dir,
            file_type="txt"  
        )
        
        chunker.process_file(file_path)
        
        chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk-")])
        if not chunk_files:
            print("[ERROR] No chunks found. Check your file or PyKomodo setup.")
            return

        summaries = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            chunk_texts = []
            for chunk_file in chunk_files:
                with open(os.path.join(temp_dir, chunk_file), "r", encoding="utf-8") as f:
                    chunk_texts.append(f.read())
            summaries = list(executor.map(summarize_chunk, chunk_texts))

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Summaries for {os.path.basename(file_path)}\n\n")
            f.write("Here's the breakdown of your document, chunk by chunk, with summaries and reasoning.\n\n")
            for i, summary in enumerate(summaries, 1):
                f.write(f"## Chunk {i}\n\n{summary}\n\n")
        
        print(f"[INFO] Done! Check out {output_file} for the summaries and reasoning.")