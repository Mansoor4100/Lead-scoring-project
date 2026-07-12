"""
Cross-platform replacement for patch_trigger.sh — runs natively on
Windows, macOS, and Linux with no bash/WSL dependency.

Called by scoring_api.py's /trigger-patch endpoint:
  python scripts/patch_trigger.py <lead_id> <correct_label>

What it does, in order:
  1. Loads the lead's stored features from leads_store.json
  2. Logs the correction into the regression suite
  3. Asks Antigravity (agy) to patch scoring_rules.py
  4. Runs the regression suite against the patched file
  5. Deploys (git commit + hot-reload) if it passes, reverts if it fails
"""

import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import append_regression_case  # noqa: E402
import run_regression  # noqa: E402

LEADS_STORE_PATH = os.path.join(BASE_DIR, "leads_store.json")
TEMPLATE_PATH = os.path.join(BASE_DIR, "antigravity_patch_prompt_template.md")


def load_lead(lead_id: str) -> dict:
    with open(LEADS_STORE_PATH) as f:
        store = json.load(f)
    if lead_id not in store:
        raise SystemExit(f"lead {lead_id} not found in leads_store.json")
    return store[lead_id]


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python patch_trigger.py <lead_id> <correct_label>")

    lead_id, correct_label = sys.argv[1], sys.argv[2]
    features = load_lead(lead_id)

    print("== 1. Logging corrected example to the regression suite ==")
    append_regression_case.add_case(features, correct_label, lead_id)

    print("== 2. Building the patch prompt ==")
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    prompt = (
        template
        + "\n\nMisclassified lead:\n"
        + json.dumps(features)
        + f"\n\nIt was scored incorrectly. The correct label is: {correct_label}\n"
    )

    print("== 3. Running Antigravity to propose a patch ==")
    try:
        agy_result = subprocess.run(
            ["agy", "-p", prompt, "--model", "claude-sonnet-4-6", "--output-format", "json"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
    	    errors="replace",
            timeout=300,
        )
    except FileNotFoundError:
        print("ERROR: 'agy' was not found. Is Antigravity CLI installed and on PATH?")
        print("RESULT: NEEDS_REVIEW")
        return
    print(agy_result.stdout)
    if agy_result.stderr:
        print("agy stderr:", agy_result.stderr)

    print("== 4. Running the regression suite against the patched file ==")
    summary = run_regression.run_checks()
    print(json.dumps(summary, indent=2))

    if summary["passed"]:
        print("PASSED — redeploying scoring API")
        subprocess.run(["git", "add", "scoring_rules.py", "regression_tests.json"], cwd=BASE_DIR)
        subprocess.run(
            ["git", "commit", "-m", f"Auto-patch: fix scoring for lead {lead_id} -> {correct_label}"],
            cwd=BASE_DIR,
        )
        try:
            req = urllib.request.Request("http://localhost:8000/reload", method="POST", data=b"")
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print("Warning: could not hit /reload automatically:", e)
        print("RESULT: DEPLOYED")
    else:
        print("FAILED — reverting patch, flagging for human review")
        subprocess.run(["git", "checkout", "--", "scoring_rules.py"], cwd=BASE_DIR)
        print("RESULT: NEEDS_REVIEW")


if __name__ == "__main__":
    main()
