"""
Lead scoring rules — THIS FILE IS PATCHABLE BY ANTIGRAVITY.

When a sales rep flags a lead as misclassified, Antigravity edits this
file directly to fix the rule, then the regression suite decides whether
the patch is safe to deploy. Keep the logic here simple and declarative
so an agent can reason about it and make small, targeted edits.
"""

WEIGHTS = {
    "company_size_large": 25,
    "company_size_medium": 15,
    "company_size_small": 5,
    "budget_mentioned": 20,
    "urgent_language": 15,
    "decision_maker_title": 20,
    "generic_inquiry": -10,
    "competitor_mention": 10,
}

THRESHOLDS = {
    "hot": 60,
    "warm": 30,
}

# Narrow combo bonus: a decision-maker expressing urgency is nearly as
# strong a buying signal as an explicit budget mention.  Applied only when
# BOTH urgent_language and decision_maker_title are true.
URGENT_DECISION_MAKER_BONUS: float = 12


def score_lead(features: dict) -> dict:
    """
    features: dict of boolean signals extracted from the lead
      (produced upstream by an LLM extraction step in n8n)

    Returns: {"score": int, "label": "hot" | "warm" | "cold", "reasons": [...]}
    """
    score = 0
    reasons = []
    for key, weight in WEIGHTS.items():
        if features.get(key):
            score += weight
            sign = "+" if weight > 0 else ""
            reasons.append(f"{key} ({sign}{weight})")

    # Apply combo bonus for urgency + decision-maker (strong buying signal
    # even without an explicit budget mention).
    if features.get("urgent_language") and features.get("decision_maker_title"):
        score += URGENT_DECISION_MAKER_BONUS
        reasons.append(f"urgent_language+decision_maker_title combo (+{URGENT_DECISION_MAKER_BONUS})")

    if score >= THRESHOLDS["hot"]:
        label = "hot"
    elif score >= THRESHOLDS["warm"]:
        label = "warm"
    else:
        label = "cold"

    return {"score": score, "label": label, "reasons": reasons}
