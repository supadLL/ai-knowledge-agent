$ErrorActionPreference = "Stop"

.\.venv\Scripts\python.exe -m uvicorn ai_knowledge_agent.web:app --host 127.0.0.1 --port 8766 --reload
