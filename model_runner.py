from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def run_gpt4(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini"
,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    usage = response.usage
    total_tokens = usage.prompt_tokens + usage.completion_tokens
    return content, total_tokens


def convert_sql_to_answer(rows, query):
    if isinstance(rows, str):  
        return rows

    if not rows:
        return "The result is empty."

    # Single row, single column
    if len(rows) == 1 and len(rows[0]) == 1:
        return f"The result is: {rows[0][0]}."

    # Single column, multiple rows
    if all(len(row) == 1 for row in rows):
        values = [str(row[0]) for row in rows]
        return "Results:\n- " + "\n- ".join(values)

    # Multiple columns ( grouped result)
    header = ["Result " + str(i+1) for i in range(len(rows[0]))]
    formatted = [
        ", ".join(map(str, row)) for row in rows
    ]
    return "Results:\n" + "\n".join(f"- {line}" for line in formatted)

