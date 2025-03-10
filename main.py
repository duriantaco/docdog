#!/usr/bin/env python3

import os
import sys
import argparse
from dotenv import load_dotenv

from process import process_document
from chunking import chunk_code
from summarizer import summarize_chunks
from md_generator import generate_markdown

def main():
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in .env file.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Code and document summarizer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    doc_parser = subparsers.add_parser("summarize-doc", help="Summarize a document by chunks")
    doc_parser.add_argument("file_path", help="Path to the document to summarize")
    doc_parser.add_argument("-o", "--output", default="summary.md", help="Output file path (default: summary.md)")
    
    code_parser = subparsers.add_parser("summarize-code", help="Summarize code files")
    code_parser.add_argument("file_paths", nargs="+", help="Path(s) to the code file(s) to summarize")
    code_parser.add_argument("-o", "--output", default="code_summary.md", help="Output file path (default: code_summary.md)")
    
    args = parser.parse_args()
    
    if args.command == "summarize-doc":
        print(f"[INFO] Summarizing document: {args.file_path}")
        process_document(args.file_path, args.output)
    
    elif args.command == "summarize-code":
        print(f"[INFO] Summarizing code files: {', '.join(args.file_paths)}")
        all_chunks = []
        for file_path in args.file_paths:
            chunks = chunk_code(file_path)
            if chunks:
                print(f"[INFO] Found {len(chunks)} functions/classes in {file_path}")
                all_chunks.extend(chunks)
        
        if all_chunks:
            print(f"[INFO] Summarizing {len(all_chunks)} code chunks...")
            summaries = summarize_chunks(all_chunks)
            generate_markdown(summaries, args.output)
            print(f"[INFO] Done! Check out {args.output} for the summaries.")
        else:
            print("[ERROR] No functions or classes found in the provided files.")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()