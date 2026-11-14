import pytest
from task_manager.tempr.client import TemprAPIError
from task_manager.workflow import evaluate


class FakeClient:
    base_url = "http://localhost:8080/api/v1"

    def __init__(self, suite_status="completed", evaluation_status="completed"):
        self.suite_status = suite_status
        self.evaluation_status = evaluation_status
        self.trace = None
        self.calls = []

    def create_agent(self, name, version, schema):
        self.calls.append(("create_agent", name, version, schema))
        return {"id": "agt_1", "latest_version": {"id": "agv_1", "version": version}}

    def create_version(self, agent_id, version, schema):
        self.calls.append(("create_version", agent_id, version, schema))
        return {"id": "agv_2", "version": version}

    def classify(self, version_id):
        self.calls.append(("classify", version_id))

    def generate_suite(self, version_id, count):
        self.calls.append(("generate_suite", version_id, count))

    def get_suite(self, version_id):
        status = self.suite_status
        return {
            "id": "ts_1",
            "status": status,
            "items": [
                {"id": "tc_1", "question": "Add task 1"},
                {"id": "tc_2", "question": "Add task 2"},
            ]
            if status == "completed"
            else [],
            "error": "provider failed" if status == "failed" else None,
        }

    def upload_trace(self, suite_id, trace):
        self.calls.append(("upload_trace", suite_id))
        self.trace = trace

    def start_evaluation(self, suite_id):
        self.calls.append(("start_evaluation", suite_id))

    def get_evaluation(self, suite_id):
        return {
            "id": "evj_1",
            "status": self.evaluation_status,
            "error": "judge failed" if self.evaluation_status == "failed" else None,
            "results": [
                {"adherence_score": 1, "consistency_score": 0.8, "grounding_score": 0.6}
            ],
        }


class FakeAgent:
    def __init__(self, fail_questions=()):
        self.agent = type("Model", (), {"model_name": "fake"})()
        self.fail_questions = set(fail_questions)
        self.questions = []

    def configuration(self):
        return {"prompt": {"system": "Task Manager"}, "tools": []}

    def run(self, question):
        self.questions.append(question)
        if question in self.fail_questions:
            raise RuntimeError("model unavailable")
        return [Message("ai", question)]


class Message:
    type = "ai"

    def __init__(self, content):
        self.content = content


def test_workflow_runs_full_flow_with_fresh_case_agent(monkeypatch):
    import task_manager.agent.agent as agent_module

    class FreshAgent(FakeAgent):
        def __init__(self, model_name):
            super().__init__()
            instances.append(self)

        def run(self, question):
            self.questions.append(question)
            return [Message(question)]

    instances = []
    monkeypatch.setattr(agent_module, "TaskManagerAgent", FreshAgent)
    client = FakeClient()
    progress = []

    result = evaluate(
        client,
        FakeAgent(),
        count=2,
        progress=progress.append,
        poll_interval=0,
        timeout=1,
    )

    assert [call[0] for call in client.calls] == [
        "create_agent",
        "classify",
        "generate_suite",
        "upload_trace",
        "start_evaluation",
    ]
    assert len(instances) == 2
    assert [entry["test_case_id"] for entry in client.trace["executions"]] == [
        "tc_1",
        "tc_2",
    ]
    assert result["agent_url"] == "http://localhost:8080/agents/agt_1"
    assert any("Average scores" in message for message in progress)


def test_workflow_continues_after_case_runtime_failure(monkeypatch):
    import task_manager.agent.agent as agent_module

    class FreshAgent(FakeAgent):
        def __init__(self, model_name):
            super().__init__(fail_questions={"Add task 1"})

        def run(self, question):
            self.questions.append(question)
            if question in self.fail_questions:
                raise RuntimeError("model unavailable")
            return [Message(question)]

    monkeypatch.setattr(agent_module, "TaskManagerAgent", FreshAgent)
    client = FakeClient()

    evaluate(client, FakeAgent(), count=2, progress=lambda _: None, poll_interval=0)

    entries = client.trace["executions"]
    assert len(entries) == 2
    assert "runtime_error" in entries[0]["execution"]
    assert "final_response" in entries[1]["execution"]


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (FakeClient(suite_status="failed"), "Test suite generation failed"),
        (FakeClient(evaluation_status="failed"), "Evaluation failed"),
    ],
)
def test_workflow_surfaces_background_job_failures(client, message, monkeypatch):
    import task_manager.agent.agent as agent_module

    class FreshAgent(FakeAgent):
        def __init__(self, model_name):
            super().__init__()

    monkeypatch.setattr(agent_module, "TaskManagerAgent", FreshAgent)
    with pytest.raises(TemprAPIError, match=message):
        evaluate(client, FakeAgent(), count=2, progress=lambda _: None, poll_interval=0)


def test_workflow_requires_new_version_for_existing_agent():
    with pytest.raises(ValueError, match="--version is required"):
        evaluate(FakeClient(), FakeAgent(), agent_id="agt_1", progress=lambda _: None)


def test_workflow_times_out_waiting_for_suite():
    with pytest.raises(TemprAPIError, match="Timed out waiting for test suite"):
        evaluate(
            FakeClient(suite_status="running"),
            FakeAgent(),
            count=2,
            progress=lambda _: None,
            poll_interval=0,
            timeout=0,
        )
