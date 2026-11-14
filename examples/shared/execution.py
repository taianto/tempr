from shared.trace import capture, case_execution


def run_test_cases(definition, cases):
    executions, failures = [], 0
    for index, case in enumerate(cases, 1):
        try:
            agent = definition.create()
            executions.append(
                case_execution(case, capture(agent.run(case["question"])))
            )
            print(f"Ran case {index}/{len(cases)}")
        except Exception as exc:  # noqa: BLE001 — record failures for every case.
            failures += 1
            executions.append(
                case_execution(case, error=f"{type(exc).__name__}: {exc}")
            )
            print(f"Case {index} failed: {exc}")
    return executions, failures
