"""Adapt generated Agents JSONL results into Promptfoo test cases."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _optional_string(item: dict, key: str):
    """Mirror the former evaluator's handling of present and missing fields."""
    return str(item.get(key, "")) if key in item else None


def generate_tests(config=None):
    """Load the generated Agents answers without rerunning the agent workflow."""
    config = config or {}
    dataset = os.getenv(
        "AGENTS_EVAL_DATA_FILE",
        config.get("dataset", "../data/agent_model_answer.jsonl"),
    )
    dataset_path = Path(dataset).expanduser()
    if not dataset_path.is_absolute():
        dataset_path = (Path(__file__).parent / dataset_path).resolve()

    tests = []
    with dataset_path.open(encoding="utf-8-sig") as source:
        for line in source:
            if not line.strip():
                continue
            payload = json.loads(line)
            item = payload.get("item", {})
            normalized_item = {
                "input": str(item.get("input", "")),
                "expected_answer": str(item.get("expected_answer", "")),
                "model_answer": str(item.get("model_answer", "")),
                "expected_tool": _optional_string(item, "expected_tool"),
                "expected_category": _optional_string(item, "expected_category"),
                "model_toolcall": _optional_string(item, "model_toolcall"),
            }
            tests.append(
                {
                    "description": normalized_item["input"],
                    "vars": {"item": normalized_item},
                    "metadata": {
                        "expected_tool": normalized_item["expected_tool"],
                        "expected_category": normalized_item["expected_category"],
                        "model_toolcall": normalized_item["model_toolcall"],
                    },
                }
            )
    return tests