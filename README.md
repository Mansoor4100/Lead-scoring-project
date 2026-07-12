# Self-healing lead qualification

A lead-scoring automation that fixes its own mistakes — safely.

Most "AI automation" demos are a single LLM call wrapped in an if/else.
This one is different: when sales flags a misclassified lead, an AI
coding agent (Google Antigravity) proposes a real fix to the scoring
logic itself, and the fix only ships if it passes a regression suite of
every previously-labeled lead. If it would break something else, it's
automatically reverted and flagged for a human instead of silently
degrading the system.

**[See it happen in git history →](../../commits/main)** — look for a
commit like `Auto-patch: fix scoring for lead test-006 -> hot`. That
commit was written by an AI agent, not by me, triggered by a real
sales correction, and only merged because it passed every existing test.

## How it works

```
Google Form → n8n → Scoring API → Slack (score + reasoning)
                                       │
                          sales clicks "this is wrong"
                                       │
                                       ▼
                     regression suite ← Antigravity proposes a fix
                                       │
                        passes? → deploy live, commit to git
                        fails?  → revert, flag for human review
```

- **Intake**: a Google Form feeds a Sheet; n8n watches it for new rows.
- **Scoring**: a small, readable Python file (`scoring_rules.py`) — not
  a prompt — holds the actual weighted logic. Readable and testable
  business logic, not a black box.
- **Review**: every scored lead posts to Slack with its score, its
  reasoning, and one-click correction buttons.
- **Self-healing**: a correction triggers Antigravity to patch the
  scoring file. A regression suite of every past labeled lead gates
  the deploy — this is the part that makes it trustworthy rather than
  reckless.

## Stack

n8n (Cloud) · FastAPI · Google Antigravity CLI (`agy`) · Google Forms/Sheets
· Slack · git (as the safety net's undo button)

## Setup

Full step-by-step instructions, including Windows-specific notes and
troubleshooting for issues I actually hit while building this (WSL
dependency conflicts, Cloudflare webhook timeouts, Windows character
encoding crashes), are in [`SETUP.md`](./SETUP.md).

## What I'd build next

- A small review dashboard for patches that get flagged `NEEDS_REVIEW`,
  instead of only surfacing them in a log file
- Deduping regression cases so repeated corrections for the same lead
  don't pile up redundant entries
- A bigger, more adversarial regression suite before trusting this with
  real production traffic
