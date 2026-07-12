You are patching a lead-scoring rules file used in production. Follow these
constraints exactly:

1. Only edit `scoring_rules.py`. Do not touch any other file.
2. The fix must be a small, targeted change to WEIGHTS or THRESHOLDS, or at
   most a few lines of logic in `score_lead`. Do not rewrite the file from
   scratch or change its function signature.
3. Do not remove or weaken any existing weight to force one case to pass —
   that just breaks a different case. Prefer adjusting thresholds or adding
   a narrow, clearly-named new signal if the existing weights can't be
   reconciled with the correction.
4. After editing, stop. Do not run the regression suite yourself and do not
   deploy anything — a separate script will test your patch and only apply
   it if every regression case still passes.
5. Explain in one or two sentences what you changed and why, so it can be
   logged for human review regardless of whether the patch is auto-deployed
   or flagged.
