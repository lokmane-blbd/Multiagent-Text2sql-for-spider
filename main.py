import sys
import os
import sqlite3
import re
import time
import torch
from schema_utils import load_schema_chunks, list_databases
from vector_store import RAGRetriever
from model_runner import convert_sql_to_answer, run_gpt4
from sqlparse import format as format_sql
from description_utils import load_descriptions, enrich_schema_with_descriptions
from sentence_transformers import SentenceTransformer, util
os.environ["TOKENIZERS_PARALLELISM"] = "false"

SPIDER_PATH = "spider/database"
EMBEDDING_DIR = "schema_embeddings"
model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_sql(gpt_output: str) -> str | None:
    # Remove Markdown code block wrappers if present
    if "```sql" in gpt_output.lower():
        gpt_output = gpt_output.lower().split("```sql", 1)[1]
        gpt_output = gpt_output.split("```", 1)[0]
    gpt_output = gpt_output.strip("`").strip()
    match = re.search(r"(select\s.+?)(;|\Z)", gpt_output, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()

    return None



def execute_sql_query(db_path, query):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return f"[Execution Error] {e}"


FEW_SHOT_EXAMPLES = """
Q: What are the names of poker players?
SQL: SELECT people.name FROM people JOIN poker_player ON people.people_id = poker_player.people_id;

Q:Show the stadium names without any concert.
SQL:SELECT name FROM stadium WHERE stadium_id NOT IN (SELECT stadium_id FROM concert)

Q: How many models does each car maker produce? List maker full name, id and the number.
SQL: SELECT car_makers.fullname, car_makers.id, COUNT(*) FROM car_makers JOIN model_list ON car_makers.id = model_list.maker GROUP BY car_makers.id;

Q: Show all template type codes that are not used by any document.
SQL: SELECT template_type_code FROM Templates EXCEPT SELECT template_type_code FROM Templates JOIN Documents ON Templates.template_id = Documents.template_id;

Q: Find the minimum grade of students who have no friends.
SQL: SELECT MIN(grade) FROM Highschooler WHERE id NOT IN (SELECT student_id FROM Friend);

Q:Return the country codes for countries that do not speak English.
SQL:SELECT CountryCode FROM countrylanguage EXCEPT SELECT CountryCode FROM countrylanguage WHERE LANGUAGE  =  "English"

Q:What is the series name and country of all TV channels that are playing cartoons directed by Ben Jones and cartoons directed by Michael Chang?
SQL:SELECT T1.series_name ,  T1.country FROM TV_Channel AS T1 JOIN cartoon AS T2 ON T1.id = T2.Channel WHERE T2.directed_by  =  'Michael Chang' INTERSECT SELECT T1.series_name ,  T1.country FROM TV_Channel AS T1 JOIN cartoon AS T2 ON T1.id = T2.Channel WHERE T2.directed_by  =  'Ben Jones'

Q:Show all template type codes with less than three templates.
SQL:SELECT template_type_code FROM Templates GROUP BY template_type_code HAVING count(*)  <  3

Q:What are the different years in which there were cars produced that weighed less than 4000 and also cars that weighted more than 3000 ?
SQL:select distinct year from cars_data where weight between 3000 and 4000;

Q:What are the names of nations where both English and French are official languages?
SQL:SELECT T1.Name FROM country AS T1 JOIN countrylanguage AS T2 ON T1.Code  =  T2.CountryCode WHERE T2.Language  =  "English" AND T2.IsOfficial  =  "T" INTERSECT SELECT T1.Name FROM country AS T1 JOIN countrylanguage AS T2 ON T1.Code  =  T2.CountryCode WHERE T2.Language  =  "French" AND T2.IsOfficial  =  "T"

Q:Find the first name and gender of student who have more than one pet.
SQL =SELECT T1.fname ,  T1.sex FROM student AS T1 JOIN has_pet AS T2 ON T1.stuid  =  T2.stuid GROUP BY T1.stuid HAVING count(*)  >  1

Q:Which professional did not operate any treatment on dogs? List the professional's id, role and email.
SQL: SELECT professional_id ,  role_code ,  email_address FROM Professionals EXCEPT SELECT T1.professional_id ,  T1.role_code ,  T1.email_address FROM Professionals AS T1 JOIN Treatments AS T2 ON T1.professional_id  =  T2.professional_id

""".strip()




def format_schema_for_prompt(chunks: list[str]) -> str:
    formatted = []
    for chunk in chunks:
        if "Table:" in chunk:
            lines = chunk.strip().splitlines()
            if lines:
                table_name = lines[0].replace("Table:", "").strip()
                columns = [line.strip() for line in lines[1:] if line.strip()]
                formatted.append(f"Table: {table_name}")
                for col in columns:
                    formatted.append(f"  - {col}")
    return "\n".join(formatted)

def run_query(db_id, user_question, filter_hint=None):
    db_path = f"{SPIDER_PATH}/{db_id}/{db_id}.sqlite"

    try:
        descriptions = load_descriptions()
        schema_chunks = load_schema_chunks(db_id, db_path)
        enriched_chunks = enrich_schema_with_descriptions(schema_chunks, db_id, descriptions)

        retriever = RAGRetriever(collection_name=f"schema_chunks_{db_id}")
        retriever.add_chunks(enriched_chunks)
        retrieved_chunks = retriever.retrieve(user_question, k=8)

        schema_text = format_schema_for_prompt(retrieved_chunks)
        

        hints = []
        if filter_hint:
            if filter_hint.get("filter_style") == "=":
                hints.append("- Use `=` for filtering text unless partial match is asked.")
            elif filter_hint.get("filter_style") == "LIKE":
                hints.append("- Use `LIKE '%value%'` only if partial match is intended.")
            if filter_hint.get("range_style") == "between":
                hints.append("- Use BETWEEN A AND B for numeric range filters.")
            if filter_hint.get("range_style") == "comparison":
                hints.append("- Use between A and B for numeric ranges instead of WHERE x > A AND x < B.")
            if filter_hint.get("allow_in") is False:
                hints.append("- Do NOT use IN (...) unless it is a subquery or exclusion (like NOT IN (SELECT ...)).")
                hints.append("- Use OR clauses for multiple values instead.")
            if filter_hint.get("date_style") == "direct":
                hints.append("- Avoid using date functions like strftime; use WHERE year = 2020.")
            if filter_hint.get("having_count") == "*":
                hints.append("- Use COUNT(*) in HAVING unless a specific column is requested.")
            if filter_hint.get("group_by_primary"):
                hints.append("- When grouping, use the primary field (e.g., name) not ID fields.")
            if filter_hint.get("use_count_star"):
                hints.append("- Use COUNT(*) unless the question refers to getting unique values by saying distinct, different and unique for example.")
            if filter_hint.get("use_count_distinct"):
                hints.append("- Use COUNT(DISTINCT column) because the question asks for different or unique values.")
            if not filter_hint.get("allow_aliases"):
                hints.append("- Do NOT use table/column aliases like AS or T1 unless absolutely needed.")
            if not filter_hint.get("allow_join"):
                hints.append("- Avoid JOIN unless values from multiple tables are needed.")

        hint_block = "\n".join(hints)

        rag_prompt = f"""
You are an expert in writing SQLite-compatible SQL queries for natural language questions.

  General SQL Rules:
- Use only the exact tables and columns provided in the schema. Do NOT invent or guess.
- Use WHERE ... = ... for direct filtering. Do NOT JOIN just to filter.
- Use JOINs only if the question explicitly asks for values from multiple tables.
- Do NOT use subqueries or IN (SELECT ...) to simulate joins.
- Prefer: SELECT ... FROM A JOIN B ON A.x = B.y WHERE ...
- Use EXCEPT only for exclusion (e.g., "who did not...")
- Do NOT use column/table aliases (like T1, s.) unless JOIN is needed.
- DO NOT use WHERE x IS NOT NULL. Assume all columns are clean.
- Do NOT rename columns using `AS` unless disambiguation is required.
- Use COUNT(DISTINCT column) if the question includes:
    - "distinct", "different", "unique"
    - Example: "How many different nationalities?" → COUNT(DISTINCT Nationality)
    - Example: "Number of distinct loser names?" → COUNT(DISTINCT loser_name)
- Do NOT use MAX/MIN for date unless the question directly asks for latest/earliest.
- Use LIKE '%...%' only for "contains", "includes", or fuzzy matching.
- When using GROUP BY:
    - Group by primary fields (e.g., `student.name`) NOT IDs
    - If joining, group only by the correct primary field
- - Use `!=` for "not equal to". Do NOT use `<>`.
- Use exact column and table names — match their casing (e.g., `LANGUAGE`, not `language`).
- Combine multiple aggregate columns in one SELECT, without using AS.
- Do NOT rename columns using `AS ...`. Avoid using `AS` to assign new column names in the SELECT clause.
- This includes expressions like: `SELECT column AS new_name` or `SELECT AVG(x) AS avg_x`.
- Such renaming is unnecessary unless required for JOIN disambiguation, and it will cause mismatches in exact SQL evaluation.
- When asked for the youngest something, dont use the column with date of birth, use the column with age.
- Always use Between A and B for numeric ranges, not WHERE x > A or x < B.
- If the question asks for the column value of the row with the largest (or smallest), youngest (or oldest), biggest(or smallest) value in another column, use ORDER BY ... DESC LIMIT 1.
  - Example (Correct): SELECT accelerate FROM cars_data ORDER BY horsepower DESC LIMIT 1
  - Example (Wrong): SELECT MAX(horsepower) FROM cars_data

- if the question is as simple as "What is the age of the oldest dog?",use max(age).

 Dynamic Constraints Based on Question:
{hint_block}

 Example Questions from different difficulites and their SQL:

{FEW_SHOT_EXAMPLES}

 Schema:
{schema_text}

 Question:
{user_question}

SQL:
""".strip()

        gpt_output, token_usage = run_gpt4(rag_prompt)
        print("\n GPT Output:\n", gpt_output)
        print(f"\n Token usage: {token_usage}")

        sql_query = extract_sql(gpt_output)        

        if not sql_query:
            print(" No SQL generated")
            return "SQL generation failed", "( GPT failed to generate a valid SELECT query.)"

        rows = execute_sql_query(db_path, sql_query)
        answer = convert_sql_to_answer(rows, sql_query)
        print(f"\n Raw answer type: {type(answer)} — value: {answer}")

        if not answer:
            answer = "(No result returned)"
        elif not isinstance(answer, str):
            answer = str(answer)
        return sql_query, answer

    except Exception as e:
        print(f"[ERROR] Exception in run_query: {e}")
        
        return "SQL generation failed", f"[Error] {str(e)}"


if __name__ == "__main__":
    try:
        user_question = input("Enter your question: ")
        t0 = time.time()
        question_embedding = model.encode(user_question, convert_to_tensor=True)

        if len(sys.argv) == 1:
            relevance_scores = []

            for db_id in list_databases():
                embedding_path = os.path.join(EMBEDDING_DIR, f"{db_id}.pt")
                if not os.path.exists(embedding_path):
                    continue
                try:
                    schema_embedding = torch.load(embedding_path)
                    score = util.pytorch_cos_sim(question_embedding, schema_embedding).item()
                    relevance_scores.append((score, db_id))
                except Exception as e:
                    print(f" Skipping {db_id}: {e}")

            top_dbs = sorted(relevance_scores, reverse=True)[:3]
            

            for _, db_id in top_dbs:
                run_query(db_id, user_question)

        else:
            db_id = sys.argv[1]
            run_query(db_id, user_question)

        print(f"\n Total time taken: {time.time() - t0:.2f} seconds")

    except KeyboardInterrupt:
        print("\n Interrupted by user. Exiting.")
