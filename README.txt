# For this system to work you need to import the spider database and replace it with the duplicate empty file under spider/.
# An env need to be set and satisfy requirements.txt
# Inside config.py the api key must be entered. 
# TEXT2SQL System

This repository contains a system for converting natural language questions into SQL queries, specifically designed for the Spider dataset. The system is built with LangGraph and various prompt engineering strategies.

---

## Directory Structure

- `main.py`  
  Main entry point for querying the system interactively.

- `ExtractionOfQuestions.py`  
  Script to extract questions from `dev.json` and create a set of questions to test.

- `Low-Level-Test.py`  
  For **single-question testing** (quick debug).

- `Wide-Level-Test.py`  
  For **evaluating a batch of questions** (even full dataset evaluation).

- `evaluation.py`  
  Spider’s official evaluation script (adapted to log predictions and analyze mismatches).

- `langgraph_workflow.py`  
  LangGraph implementation for agent orchestration.

- `description_utils.py`  
  Utilities for enriching schema chunks with descriptions.

- `schema_utils.py`  
  Functions to load and format database schemas.

- `vector_store.py`  
  RAG-based retriever for schema-aware chunk retrieval.

- `model_runner.py`  
  Model invocation logic (e.g., GPT-4, GPT-4o Mini).

