import json
from langgraph_workflow import build_graph  


with open("sampled_questions.json") as f:
    sampled_questions = json.load(f)


graph = build_graph()


lines = []

for idx, item in enumerate(sampled_questions, 1):
    question = item["question"]
    db_id = item["db_id"]

    print(f"\n🔹 [{idx}/{len(sampled_questions)}] {question}. use {db_id} database.")

    try:
        result = graph.invoke({
            "question": question,
            "dbs": [db_id]  
        })

        sql = result.get("final_sql", "").replace("\n", " ").replace("\t", " ").strip()
        print("Result object:", result)

        if not sql:
            sql = "SELECT 1" 

        lines.append(f"{sql}\t{db_id}")
    except Exception as e:
        print(f"❌ Error: {e}")
        lines.append(f"SELECT 1\t{db_id}")  


with open("sample_predictions.tsv", "w") as f:
    f.write("\n".join(lines))

print("\n Done. Predictions written to sample_predictions.tsv")
