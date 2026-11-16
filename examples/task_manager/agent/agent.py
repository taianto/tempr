"""Build a LangChain Task Manager and keep its conversation in memory."""

from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from task_manager.agent.store import TaskStore
from task_manager.agent.tools import make_tools
from task_manager.config import SYSTEM_PROMPT


class TaskManagerAgent:
    def __init__(
        self,
        model_name: str = "gpt-6-luna",
        store: TaskStore | None = None,
        model: Any | None = None,
    ) -> None:
        self.store = store or TaskStore()
        self.model_name = model_name
        self.tools = make_tools(self.store)
        self.graph = create_agent(
            model=model or ChatOpenAI(model=model_name),
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )
        self.messages: list[Any] = []

    def run(self, user_input: str) -> list[Any]:
        result = self.graph.invoke({"messages": [*self.messages, ("user", user_input)]})
        self.messages = result["messages"]
        return self.messages

    def reset(self) -> None:
        self.store = TaskStore()
        self.tools = make_tools(self.store)
        self.graph = create_agent(
            model=ChatOpenAI(model=self.model_name),
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )
        self.messages = []
