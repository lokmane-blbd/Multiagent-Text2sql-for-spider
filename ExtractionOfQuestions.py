import json
import random

# Load full Spider dev set
with open("...../Text2sql/spider/dev.json", "r", encoding="utf-8") as f:
    data = json.load(f)

#here we get a sample randomly( optional)
random.seed(99)  
sample_size = int(len(data) * 0.1)
sampled = random.sample(data, sample_size)


sample_questions = [
    {"question": item["question"], "db_id": item["db_id"]}
    for item in sampled
]


gold_sql_lines = [f"{item['query']}\t{item['db_id']}" for item in sampled]

# Write outputs
with open("sampled_questions.json", "w", encoding="utf-8") as f:
    json.dump(sample_questions, f, indent=2)

with open("sample_gold.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(gold_sql_lines))

print(" Files created: sample_questions.json and gold_sample.sql")
