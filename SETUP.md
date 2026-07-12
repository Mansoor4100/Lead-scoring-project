# Self-healing lead qualification & routing

n8n handles intake, scoring, and Slack review. A custom scoring API
(built and later *patched* by Antigravity) does the actual judgment call.
When sales flags a lead as misclassified, Antigravity proposes a fix to
the scoring logic, a regression suite decides whether it's safe, and the
API only redeploys if every past labeled case still passes.

## Why this exists

Most "AI automation" portfolio projects are a single LLM call wrapped in
an if/else. This one shows something harder: a system whose business
logic improves from feedback instead of silently going stale — with a
safety gate so a bad patch can't quietly make things worse.

## Files

- `scoring_rules.py` — the patchable scoring logic (weights + thresholds).
  This is the *only* file Antigravity should ever edit.
- `scoring_api.py` — FastAPI service n8n calls. Hot-reloads
  `scoring_rules.py` so a patch takes effect without a restart.
- `regression_tests.json` — labeled leads used as the safety net.
- `run_regression.py` — exits non-zero if any labeled case fails.
- `append_regression_case.py` — adds a newly corrected lead to the suite.
- `antigravity_patch_prompt_template.md` — keeps Antigravity's edits narrow.
- `scripts/patch_trigger.py` — the full loop: log correction, ask
  Antigravity to patch, run regression tests, deploy or revert. Pure
  Python — no bash/WSL dependency, so it runs natively on Windows too.
- `n8n-workflow.json` — import into n8n. Two webhook paths: `/lead-intake`
  and `/lead-feedback`.

## One-time setup (~30-45 min) — using n8n Cloud

n8n Cloud runs on n8n's servers, not your laptop. That's fine for the
scoring API's `/score` and `/leads` endpoints — n8n Cloud can call any
public URL. But it can't run a shell command *on your machine*, which is
why the workflow calls a `/trigger-patch` HTTP endpoint instead of using
n8n's "Execute Command" node. Your laptop still needs a public address
for n8n Cloud to reach it — that's what the tunnel step below is for.

1. **Scoring API** (on your laptop):
   ```bash
   cd lead-scoring-project
   pip install fastapi uvicorn
   git init && git add . && git commit -m "initial scoring rules"
   uvicorn scoring_api:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Antigravity CLI** — install `agy`, sign in, and confirm
   `agy -p "say hi" --output-format json` works from this folder.

3. **Give your laptop a public address (ngrok)** — n8n Cloud lives on the
   internet and can't see `localhost` on your machine, so you need a
   tunnel: a free service that hands your local port a public URL and
   forwards traffic through it.
   ```bash
   # install from ngrok.com, then:
   ngrok http 8000
   ```
   ngrok prints something like `https://a1b2c3.ngrok-free.app` — copy it.
   This URL now points straight at the scoring API running on your laptop.
   Leave this terminal window running for the whole demo; if you restart
   ngrok, the URL changes and you'll need to update it in n8n again.

4. **n8n Cloud** — sign up free at n8n.io, create a new workflow, and use
   the "Import from File" option to load `n8n-workflow.json`.
   - Go to your workflow's **Settings → Variables** (or set environment
     variables if you're on a plan that supports them) and add
     `SCORING_API_URL` = the ngrok URL from step 3 (no trailing slash).
   - Activate the workflow. n8n will show you the live webhook URLs —
     something like `https://yourname.app.n8n.cloud/webhook/lead-intake`
     and `.../webhook/lead-feedback`. Point your lead form at the first
     one.
   - Connect Slack credentials on the "Post to Slack for Review" node,
     and set your channel ID.

5. **Slack app** — you need a Slack app with a bot token and permission
   to post to your channel (`chat:write`). The buttons in the message are
   plain URL buttons, not interactive components, so there's no need to
   set up Slack's Events API — clicking one just opens the feedback
   webhook URL in the browser.

### Why the tunnel matters (in plain terms)

Your laptop, by default, is like an unlisted phone number — only
things on the same network (like your own terminal) can call it.
n8n Cloud lives out on the public internet and has no way to dial an
unlisted number. ngrok gives your laptop a temporary public number and
forwards any call it gets straight to your local port 8000. That's the
only reason the tunnel exists — everything else about the workflow is
unchanged.

## The demo (what to actually show)

Don't try to demo the fully-general "learns forever" system live — script
one clean cycle:

1. Submit a lead through `/lead-intake` that your current weights will
   score wrong on purpose (e.g. a large company using generic language
   that should obviously be hot given context, but scores warm).
2. Show the Slack message with its score and reasoning.
3. Click "Flag: should be HOT."
4. Show the terminal running `patch_trigger.sh`: Antigravity proposing
   a change to `scoring_rules.py`, the regression suite running, and the
   API confirming redeploy.
5. Re-submit a similar lead and show it now scores correctly — and that
   the earlier regression cases still pass.

That's a complete, honest "wow" moment in under two minutes, and you can
describe how you'd generalize it (bigger regression suite, a review
dashboard for failed patches, alerting) without needing to have built
all of that today.

## Honest caveats to mention in the interview

- The safety gate (regression suite) is essential — LLM-adjacent business
  logic can look "fixed" for the case you tested and be wrong elsewhere.
  This is why patches are gated, not auto-trusted.
- `git checkout` revert on failure requires the folder to actually be a
  git repo — don't skip `git init` in setup.
- `agy -p` is a one-shot patch call; check `agy --help` on your installed
  version, since CLI flags on fast-moving tools like this can change
  between releases.
- The patch trigger is pure Python (`scripts/patch_trigger.py`), not a
  shell script — this avoids needing bash or WSL on Windows.
