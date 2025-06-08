from langgraph_workflow import build_graph
import re


question = "What are the different years in which there were cars produced that weighed less than 4000 and also cars that weighted more than 3000 ?"
db_id = "car_1"

print(f"\n🔹 Testing question: {question} (DB: {db_id})")
graph = build_graph()

try:
    result = graph.invoke({
        "question": question,
        "dbs": [db_id]  
    })

    sql = result.get("final_sql", "").strip() 
    answer = result.get("output", "").strip()

except Exception as e:
    print(f"\n❌ Error during execution: {e}")
