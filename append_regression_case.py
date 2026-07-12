"""
Adds a sales-corrected lead to regression_tests.json so every future
patch is checked against it too, not just the case that triggered the fix.

Can be run directly:
  python append_regression_case.py '<features_json>' <correct_label> <lead_id>
or imported and called from patch_trigger.py via add_case(...).
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(BASE_DIR, "regression_tests.json")


def add_case(features: dict, correct_label: str, lead_id: str) -> None:
    features = dict(features)
    features["lead_id"] = lead_id

    with open(TESTS_PATH) as f:
        cases = json.load(f)

    cases.append(
        {
            "name": f"corrected_{lead_id}",
            "features": features,
            "expected_label": correct_label,
        }
    )

    with open(TESTS_PATH, "w") as f:
        json.dump(cases, f, indent=2)

    print(f"Added regression case for {lead_id} -> {correct_label}")


def main():
    features_json, correct_label, lead_id = sys.argv[1], sys.argv[2], sys.argv[3]
    add_case(json.loads(features_json), correct_label, lead_id)


if __name__ == "__main__":
    main()
