from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("ERROR: OPENAI_API_KEY not found in .env file.")
client = OpenAI(api_key=api_key)

def summarize_chunks(chunks):
    summaries = []
    for chunk in chunks:
        prompt = (
            f"Generate a docstring or summary for the following {chunk['type']}:\n\n"
            f"{chunk['code']}\n\n"
            "Summary:"
        )
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes code."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            summary = response.choices[0].message.content.strip()
            summaries.append({
                "name": chunk['name'],
                "type": chunk['type'],
                "summary": summary
            })
        except Exception as e:
            print(f"[ERROR] Failed to summarize {chunk['type']} {chunk['name']}: {e}")
            summaries.append({
                "name": chunk['name'],
                "type": chunk['type'],
                "summary": "Summary generation failed due to an error."
            })
    return summaries