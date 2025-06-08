## 🌍 Performance

This system is currently **ranked 23rd worldwide** on the official **Spider evaluation leaderboard**, based on accuracy and execution quality.

📊 See the leaderboard:  
👉 [Spider Leaderboard – Yale LILY Lab](https://yale-lily.github.io/spider)

**Evaluation Results**:
|           | Easy | Medium | Hard | Extra | All  |
| --------- | ---- | ------ | ---- | ----- | ---- |
| **Count** | 248  | 446    | 174  | 166   | 1034 |
|                        | Easy  | Medium | Hard  | Extra | All   |
| ---------------------- | ----- | ------ | ----- | ----- | ----- |
| **Execution Accuracy** | 0.931 | 0.767  | 0.695 | 0.422 | 0.739 |
| **Exact Match**        | 0.911 | 0.702  | 0.529 | 0.223 | 0.646 |

**Partial Matching F1 Score**

| Metric            | Easy  | Medium | Hard  | Extra | All   |
| ----------------- | ----- | ------ | ----- | ----- | ----- |
| Select            | 0.947 | 0.906  | 0.950 | 0.792 | 0.906 |
| Select (no AGG)   | 0.976 | 0.915  | 0.950 | 0.799 | 0.917 |
| Where             | 0.968 | 0.719  | 0.500 | 0.389 | 0.674 |
| Where (no OP)     | 0.968 | 0.741  | 0.570 | 0.511 | 0.718 |
| Group (no Having) | 0.842 | 0.790  | 0.895 | 0.720 | 0.789 |
| Group             | 0.842 | 0.700  | 0.868 | 0.640 | 0.718 |
| Order             | 0.857 | 0.901  | 0.887 | 0.386 | 0.727 |
| And/Or            | 0.996 | 0.995  | 0.967 | 0.926 | 0.980 |
| IUEN              | 1.000 | 1.000  | 0.390 | 0.286 | 0.351 |
| Keywords          | 0.947 | 0.902  | 0.726 | 0.686 | 0.835 |


---


# 🧠 TEXT2SQL System

This repository contains a system for converting natural language questions into SQL queries, specifically designed for the **Spider** dataset. The system is built with **LangGraph** and various **prompt engineering strategies**.

---

## ⚙️ Setup Instructions

- For this system to work, you need to **import the Spider database** and replace it with the duplicate empty file under `spider/`.
- An **environment must be set** and satisfy `requirements.txt`.
- Inside `config.py`, the **API key must be entered**.

---

## 📁 Directory Structure

- `main.py`  
  🔹 Main entry point for querying the system interactively.

- `ExtractionOfQuestions.py`  
  🔹 Script to extract questions from `dev.json` and create a set of questions to test.

- `Low-Level-Test.py`  
  🔹 For **single-question testing** (quick debug).

- `Wide-Level-Test.py`  
  🔹 For **evaluating a batch of questions** (even full dataset evaluation).

- `evaluation.py`  
  🔹 Spider’s official evaluation script (adapted to log predictions and analyze mismatches).

- `langgraph_workflow.py`  
  🔹 LangGraph implementation for agent orchestration.

- `description_utils.py`  
  🔹 Utilities for enriching schema chunks with descriptions.

- `schema_utils.py`  
  🔹 Functions to load and format database schemas.

- `vector_store.py`  
  🔹 RAG-based retriever for schema-aware chunk retrieval.

- `model_runner.py`  
  🔹 Model invocation logic (e.g., GPT-4, GPT-4o Mini).

---


