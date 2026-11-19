"""Run a complete evaluation for one example agent."""

import argparse
import os
import sys

from shared.config import API_URL, CASE_COUNT
from shared.registry import get_agent
from shared.workflow import evaluate_agent
from tempr.client import TemprAPIError, TemprClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", help="Name of an agent example to evaluate")
    parser.add_argument(
        "--count", type=int, default=CASE_COUNT, help="Generated cases (1–100)"
    )
    args = parser.parse_args()

    if not 1 <= args.count <= 100:
        parser.error("--count must be between 1 and 100")
    return args


def main() -> int:
    args = parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY in examples/.env", file=sys.stderr)
        return 2

    try:
        definition = get_agent(args.agent)
        with TemprClient(API_URL) as client:
            return evaluate_agent(client, definition, args.count)
    except (TemprAPIError, ValueError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
