from langgraph.graph import StateGraph
from typing import TypedDict
from model_runner import run_gpt4
from main import run_query
import json
class QueryState(TypedDict):
    question: str
    dbs: list[str]
    output: str
    attempt: int
    filter_hint: dict | None
    final_db: str | None
    final_sql: str | None


def helper_analyze_question(state: QueryState) -> QueryState:
    print("helper_analyze_question agent started -->>")
    question = state["question"]

    prompt = f"""
You are a JSON-only assistant.

Your task is to analyze the user's question and return SQL generation preferences.

Return a JSON object with:
- "filter_style": "LIKE" or "="
- "range_style": "between" or "comparison"
- "allow_in": false always unless it’s explicitly semantically required
- "date_style": "direct"
- "having_count": "*" or a column name
- "allow_join": false unless question clearly requires multiple tables
- "allow_aliases": true only if the question requires a JOIN, otherwise false
- "group_by_primary": true if grouping by ID but returning other attributes (e.g., name)
- "use_count_star": true if counting all rows, false if question refers to a specific or filtered column
- "use_count_distinct": true if the question asks for:
    - "distinct"
    - "unique"
    Otherwise false.
  DO NOT add any explanation, markdown, or formatting.
  DO NOT wrap the output in code blocks (no ```).
  DO NOT respond with "Here is the JSON" — just the raw JSON.
Only return valid JSON like this:
{{
  "filter_style": "=",
  "range_style": "comparison",
  "allow_in": false,
  "date_style": "direct",
  "having_count": "*",
  "allow_join": false,
  "allow_aliases": false,
  "group_by_primary": true,
  "use_count_star": true,
  "use_count_distinct": false
}}

Question:
\"\"\"{question}\"\"\"
""".strip()

    try:
        response, _ = run_gpt4(prompt)
        parsed = json.loads(response)
        print(f" Filter hint extracted: {parsed}")
        return {**state, "filter_hint": parsed}
    except Exception as e:
        print(f" Failed to extract hints: {e}")
        return {**state, "filter_hint": {}}


def generate_sql_single(state: QueryState) -> QueryState:
    print(" generate_sql_single -->>")

    question = state["question"]
    db_id = state["dbs"][0]
    filter_hint = state.get("filter_hint")

    sql, result = run_query(db_id, question, filter_hint=filter_hint)
    result_str = str(result) if result is not None else "(No result returned)"
    sql_str = str(sql) if sql is not None else "SQL generation failed"

    combined = result_str + f"\n\n SQL used:\n{sql_str}"
    return {
        **state,
        "output": combined,
        "final_sql": sql_str,
        "final_db": db_id
    }


def sql_rewriter_agent(state: QueryState) -> QueryState:
    print(" sql_rewriter_agent -->>")

    import re
    output = state.get("output", "")
    db_id = state["final_db"]
    
    sql_match = re.search(r" SQL used:\n(.+)", output, re.DOTALL)
    raw_sql = sql_match.group(1).strip() if sql_match else ""

    prompt = f"""
You are a SQL formatting corrector.

Revise the SQL query below ONLY IF it violates any of the following rules. Do not change the logic, only fix formatting.

Rules:
- Remove column or table aliases unless used in JOINs.
- Remove AS ... column renaming unless needed for disambiguation.
- Remove WHERE x IS NOT NULL — assume clean data.
- Avoid IN (SELECT ...) unless it’s for exclusion (NOT IN).
- Use JOINs instead of subqueries if simulating joins.
- Use SELECT ... FROM A JOIN B ON A.x = B.y WHERE ... rather than nested filters.
- if an SQL uses WHERE x IN ('a', 'b') convert to WHERE x = 'a' OR x = 'b'.
If the SQL is already correct, return the exact SQL query unchanged — no explanation, no formatting, no commentary.
Only return valid SQL, starting with SELECT. No markdown, no text.

SQL:
{raw_sql}
"""

    try:
        corrected_sql, _ = run_gpt4(prompt)
        corrected_sql = corrected_sql.strip()
        if not corrected_sql.lower().startswith("select"):
            print(" Rewriter output was not valid SQL — falling back to original")
            corrected_sql = raw_sql

        rewritten_output = re.sub(
            r" SQL used:\n(.+)",
            f" SQL used:\n{corrected_sql}",
            output,
            flags=re.DOTALL
        )
        return {**state, "output": rewritten_output, "final_sql": corrected_sql}
    except Exception as e:
        print(f" Failed to rewrite SQL: {e}")
        return state


def final_output(state: QueryState) -> QueryState:
    print("final_output -->>")
    print("\n Final Answer:")
    print(state["output"])
    return state


def build_graph():
    graph = StateGraph(QueryState)
    graph.add_node("helper_analyze_question", helper_analyze_question)
    graph.add_node("generate_sql_single", generate_sql_single)
    graph.add_node("sql_rewriter_agent", sql_rewriter_agent)
    graph.add_node("final_output", final_output)

    graph.set_entry_point("helper_analyze_question")
    graph.add_edge("helper_analyze_question", "generate_sql_single")
    graph.add_edge("generate_sql_single", "sql_rewriter_agent")
    graph.add_edge("sql_rewriter_agent", "final_output")

    graph.set_finish_point("final_output")

    return graph.compile()
