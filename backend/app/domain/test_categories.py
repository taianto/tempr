"""Canonical category names shared by generation, validation, and persistence."""

from typing import Literal, get_args

TestCategory = Literal[
    "happy_path",
    "boundary_probe",
    "missing_information",
    "ambiguous_input",
    "prompt_injection",
    "policy_bypass",
    "sensitive_data_request",
    "hallucination_probe",
]

TEST_CATEGORIES: tuple[str, ...] = get_args(TestCategory)
