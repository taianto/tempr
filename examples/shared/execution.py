from shared.trace import case_execution
from tempr.integrations.langchain import TracedAgent


def run_test_cases(definition, cases):
    executions, failures = [], 0
    for index, case in enumerate(cases, 1):
        try:
            agent = definition.create()
            traced = TracedAgent(agent.graph).run(
                {"messages": [("user", case["question"])]}
            )
            executions.append(traced.for_case(case["id"]))
            print(f"Ran case {index}/{len(cases)}")
        except Exception as exc:  # noqa: BLE001 — record failures for every case.
            failures += 1
            executions.append(
                case_execution(case, error=f"{type(exc).__name__}: {exc}")
            )
            print(f"Case {index} failed: {exc}")
    return executions, failures
