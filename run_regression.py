"""
Runs every labeled example in regression_tests.json against the CURRENT
scoring_rules.py.

This is the safety gate: a patch only gets redeployed if run_checks()
returns passed=True. This is what keeps the "self-healing" loop from
silently making things worse. Can be run directly (python run_regression.py)
or imported and called from patch_trigger.py.
"""

import importlib
import json
import os
import sys

import scoring_rules

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(BASE_DIR, "regression_tests.json")


def run_checks() -> dict:
    importlib.reload(scoring_rules)  # always test the latest patched file

    with open(TESTS_PATH) as f:
        cases = json.load(f)

    failures = []
    for case in cases:
        result = scoring_rules.score_lead(case["features"])
        if result["label"] != case["expected_label"]:
            failures.append(
                {
                    "name": case["name"],
                    "expected": case["expected_label"],
                    "got": result["label"],
                    "score": result["score"],
                }
            )

    return {
        "passed": len(failures) == 0,
        "total": len(cases),
        "passed_count": len(cases) - len(failures),
        "failed_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    summary = run_checks()
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
