from pathlib import Path

NAME = "Task Manager"
DESCRIPTION = "An in-memory assistant for managing tasks."
MODEL = "gpt-6-luna"
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()
