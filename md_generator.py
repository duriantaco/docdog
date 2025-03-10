from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("ERROR: OPENAI_API_KEY not found in .env file.")
client = OpenAI(api_key=api_key)

def generate_markdown(summaries, output_file):
    prompt = "Create a Markdown file with the following summaries of code functions and classes:\n\n"
    for summary in summaries:
        prompt += f"- **{summary['type'].capitalize()} {summary['name']}**: {summary['summary']}\n"
    prompt += "\nOrganize them into sections with headers for each function or class."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates markdown documentation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        md_content = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Failed to generate Markdown: {e}")
        md_content = "# Summary Generation Failed\n\nUnable to generate Markdown content due to an error."

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md_content)