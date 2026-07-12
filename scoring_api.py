"""
Lead scoring API.

- POST /score        -> score a lead using the current scoring_rules.py
- POST /leads/{id}    -> store a lead's raw features (so the feedback
                         webhook can retrieve them later without needing
                         the full payload passed back through Slack)
- GET  /leads/{id}    -> retrieve a stored lead's features
- POST /reload        -> force a reload of scoring_rules.py (called after
                         Antigravity patches it and the regression suite passes)
- POST /trigger-patch -> runs the full patch_trigger.sh loop over HTTP, so
                         n8n Cloud (which can't run local shell commands on
                         your laptop) can kick it off with a normal HTTP
                         Request node instead

Run with: uvicorn scoring_api:app --host 0.0.0.0 --port 8000 --reload
(--reload is fine for the demo; drop it for anything resembling production)
"""

import importlib
import json
import os
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import scoring_rules

app = FastAPI(title="Lead Scoring API")

LEADS_STORE_PATH = os.path.join(os.path.dirname(__file__), "leads_store.json")


def _load_store() -> dict:
    if not os.path.exists(LEADS_STORE_PATH):
        return {}
    with open(LEADS_STORE_PATH, "r") as f:
        return json.load(f)


def _save_store(store: dict) -> None:
    with open(LEADS_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


class LeadFeatures(BaseModel):
    lead_id: str
    company_size_large: bool = False
    company_size_medium: bool = False
    company_size_small: bool = False
    budget_mentioned: bool = False
    urgent_language: bool = False
    decision_maker_title: bool = False
    generic_inquiry: bool = False
    competitor_mention: bool = False


@app.post("/score")
def score(features: LeadFeatures):
    importlib.reload(scoring_rules)  # picks up any patch Antigravity made
    result = scoring_rules.score_lead(features.dict())
    result["lead_id"] = features.lead_id
    return result


@app.post("/leads/{lead_id}")
def save_lead(lead_id: str, features: LeadFeatures):
    store = _load_store()
    store[lead_id] = features.dict()
    _save_store(store)
    return {"saved": True, "lead_id": lead_id}


@app.get("/leads/{lead_id}")
def get_lead(lead_id: str):
    store = _load_store()
    if lead_id not in store:
        raise HTTPException(status_code=404, detail="lead not found")
    return store[lead_id]


@app.post("/reload")
def reload_rules():
    importlib.reload(scoring_rules)
    return {"reloaded": True}


class PatchRequest(BaseModel):
    lead_id: str
    correct_label: str


@app.post("/trigger-patch")
def trigger_patch(req: PatchRequest):
    """
    Called by n8n (Cloud or self-hosted) instead of running a shell command
    directly. Starts patch_trigger.py in the background and returns
    immediately — the full loop (Antigravity + regression tests + git) can
    take over a minute, which is longer than n8n/Cloudflare will wait for
    a webhook response. Check /patch-log/{lead_id} afterward for the result.
    """
    store = _load_store()
    if req.lead_id not in store:
        raise HTTPException(status_code=404, detail="lead not found")

    base_dir = os.path.dirname(__file__)
    script_path = os.path.join(base_dir, "scripts", "patch_trigger.py")
    log_path = os.path.join(base_dir, f"patch_log_{req.lead_id}.txt")

    popen_kwargs = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    with open(log_path, "w", encoding="utf-8", errors="replace") as log_file:
        subprocess.Popen(
            [sys.executable, script_path, req.lead_id, req.correct_label],
            cwd=base_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            **popen_kwargs,
        )

    

    return {
        "lead_id": req.lead_id,
        "correct_label": req.correct_label,
        "status": "started",
        "message": "Patch process started in the background. Check /patch-log/"
        + req.lead_id + " in a minute or two for the result, or watch the "
        "uvicorn terminal window.",
    }


@app.get("/patch-log/{lead_id}")
def patch_log(lead_id: str):
    base_dir = os.path.dirname(__file__)
    log_path = os.path.join(base_dir, f"patch_log_{lead_id}.txt")
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="no patch log for this lead yet")
    with open(log_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    finished = "RESULT: DEPLOYED" in content or "RESULT: NEEDS_REVIEW" in content
    return {"lead_id": lead_id, "finished": finished, "log": content}


@app.get("/health")
def health():
    return {"status": "ok"}
