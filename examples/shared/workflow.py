from shared.agents import AgentDefinition
from shared.execution import run_test_cases
from shared.polling import wait_for_completion
from shared.versions import create_next_version
from tempr.client import TemprAPIError, TemprClient
from tempr.integrations.langchain import configuration


def evaluate_agent(client: TemprClient, agent: AgentDefinition, count: int) -> int:
    schema = _agent_configuration(agent)
    agent_id, version = _create_version(client, agent, schema)
    _classify_version(client, version["id"], version["version"])
    suite = _generate_suite(client, version["id"], count)
    executions, failures = run_test_cases(agent, suite["items"])
    _upload_executions(client, suite["id"], executions)
    evaluation = _judge_suite(client, suite["id"])
    _print_summary(client, agent_id, version, failures, evaluation)
    return 1 if failures else 0


def _agent_configuration(agent: AgentDefinition) -> dict:
    runnable = agent.create()
    return configuration(
        agent.name, agent.description, agent.model, agent.system_prompt, runnable.tools
    )


def _create_version(
    client: TemprClient, agent: AgentDefinition, schema: dict
) -> tuple[str, dict]:
    print("Creating next agent version…")
    return create_next_version(client, agent.name, agent.description, schema)


def _classify_version(client: TemprClient, version_id: str, label: str) -> None:
    print(f"Classifying version {label}…")
    client.classify(version_id)


def _generate_suite(client: TemprClient, version_id: str, count: int) -> dict:
    print(f"Generating {count} test cases…")
    client.generate_suite(version_id, count)
    suite = wait_for_completion(lambda: client.get_suite(version_id), "Test suite")
    if len(suite.get("items", [])) != count:
        raise TemprAPIError("Tempr returned an unexpected number of test cases")
    return suite


def _upload_executions(
    client: TemprClient, suite_id: str, executions: list[dict]
) -> None:
    client.upload_trace(suite_id, {"executions": executions})


def _judge_suite(client: TemprClient, suite_id: str) -> dict:
    print("Judging executions…")
    client.start_evaluation(suite_id)
    return wait_for_completion(lambda: client.get_evaluation(suite_id), "Evaluation")


def _print_summary(
    client: TemprClient, agent_id: str, version: dict, failures: int, evaluation: dict
) -> None:
    app_url = client.base_url.removesuffix("/api/v1")
    print(f"Complete: {app_url}/agents/{agent_id} (version {version['version']})")
    results = evaluation.get("results", [])
    for key in ("adherence_score", "consistency_score", "grounding_score"):
        if results:
            average = sum(float(result[key]) for result in results) / len(results)
            print(f"{key.removesuffix('_score').capitalize()}: {average:.0%}")
    print(f"Runtime failures: {failures}")
