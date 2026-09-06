"""
AI Proposal QA
==============

Semantic QA of a generated proposal using Groq.

This module:
- Uses the canonical schemas from schemas.py
- Uses real Groq AI
- Does not define duplicate QA models
- Checks proposal grounding against ValidatedScope
- Checks rejected requirement leakage
- Checks unresolved scope leakage
- Checks unsupported commitments
- Checks safety
- Checks hallucination / overpromising
- Checks requirement completeness

The deterministic Proposal QA remains the hard structural gate.
This module provides semantic AI review.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI

from .schemas import (
    AIProposalQAResult,
    AIQAIssueType,
    PitchDraft,
    ProposalDraft,
    QAIssueSeverity,
    ValidatedScope,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

AI_PASS_THRESHOLD = 8.0


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_scope(
    value: ValidatedScope | Dict[str, Any],
) -> ValidatedScope:
    if isinstance(value, ValidatedScope):
        return value

    return ValidatedScope.model_validate(value)


def _to_pitch(
    value: PitchDraft | Dict[str, Any],
) -> PitchDraft:
    if isinstance(value, PitchDraft):
        return value

    return PitchDraft.model_validate(value)


def _to_proposal(
    value: ProposalDraft | Dict[str, Any],
) -> ProposalDraft:
    if isinstance(value, ProposalDraft):
        return value

    return ProposalDraft.model_validate(value)


def _json(value: Any) -> str:
    """Serialize a Pydantic model or dict."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
    )


def _severity_value(value: QAIssueSeverity | str) -> str:
    if isinstance(value, QAIssueSeverity):
        return value.value

    return str(value).lower()


def _issue_type_value(value: AIQAIssueType | str) -> str:
    if isinstance(value, AIQAIssueType):
        return value.value

    return str(value).lower()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    return """
You are the final semantic QA reviewer for a consultancy
Scope-to-Proposal AI OS.

Your job is NOT to improve the proposal.
Your job is to detect whether the proposal is faithful to the
validated scope.

You must be conservative.

IMPORTANT RULES:

1. The ValidatedScope is the ONLY source of truth for final scope.

2. Do not assume that something is allowed merely because it sounds
   commercially useful.

3. Rejected requirements MUST NOT appear as committed functionality.

4. Unresolved scope MUST NOT be converted into assumptions.

5. Do not invent requirements, integrations, features, timelines,
   metrics, guarantees, pricing, capabilities, or technical details.

6. Confirmed and modified requirements must be represented accurately.

7. Modified requirements must follow final_scope, not the original wording
   when the two differ.

8. Scope boundaries must be respected.

9. Assumptions must not secretly introduce new scope.

10. Safety-sensitive requirements must preserve appropriate human escalation.

11. Never approve autonomous medical diagnosis or autonomous prescribing
    unless it is explicitly and safely supported by the validated scope.
    In a normal healthcare chatbot proposal, such functionality should be
    treated as a serious safety problem.

12. Do not penalize a proposal merely because it contains the valid
    ProposalDraft field `open_items`. Only flag open_items when the proposal
    actually contains unresolved items that contradict its claimed readiness.

13. A strong proposal may rephrase validated requirements. Exact wording
    is NOT required.

14. Focus on semantic grounding, not stylistic preferences.

Return ONLY valid JSON matching the supplied response schema.
"""


def _build_user_prompt(
    scope: ValidatedScope,
    pitch: PitchDraft,
    proposal: ProposalDraft,
) -> str:
    return f"""
Review the following proposal against the validated scope.

================ VALIDATED SCOPE ================
{_json(scope)}

================ PITCH ================
{_json(pitch)}

================ PROPOSAL ================
{_json(proposal)}

Evaluate:

A. Unsupported scope
- Did the proposal promise functionality not present in validated scope?

B. Rejected requirement leakage
- Did any rejected requirement reappear as committed functionality?

C. Unresolved scope
- Did unresolved questions/items get silently converted into scope?

D. Missing requirements
- Are confirmed/modified requirements represented?

E. Incorrect final scope
- Did the proposal use the original requirement instead of the modified
  final scope?

F. Safety
- Does the proposal make unsafe healthcare, financial, legal, security,
  or other high-risk claims?
- Does it preserve human escalation where required?

G. Overpromise
- Does it guarantee outcomes or imply unsupported certainty?

H. Hallucination
- Are there invented integrations, metrics, technologies, timelines,
  capabilities, or business claims?

I. Proposal readiness
- Is the proposal credible and consistent with the validated scope?

SCORING:

10 = fully grounded and safe.
9 = excellent with only extremely minor issues.
8 = acceptable and proposal-ready.
7 = needs revision.
6 or below = substantial problems.

Set passed=true ONLY when:
- score >= 8.0
- no high or critical issue exists
- no rejected requirement leakage exists
- no unresolved scope is presented as committed scope
- no serious safety issue exists.

For each issue:
- issue_type MUST be one of the allowed enum values.
- severity MUST be one of low, medium, high, critical.
- evidence MUST quote or precisely identify the relevant proposal/scope
  content.
- recommendation MUST explain the specific correction.

Return ONLY JSON.
"""


# ---------------------------------------------------------------------------
# AI result normalization
# ---------------------------------------------------------------------------

def _apply_result_gate(
    result: AIProposalQAResult,
) -> AIProposalQAResult:
    """
    Apply deterministic rules to the AI result.

    The LLM supplies semantic judgment.
    Python enforces the hard pass threshold.
    """
    high_or_critical = any(
        _severity_value(issue.severity)
        in {"high", "critical"}
        for issue in result.issues
    )

    serious_issue_types = {
        "rejected_requirement_leakage",
        "unresolved_scope",
        "unsupported_scope",
        "safety",
        "incorrect_final_scope",
    }

    serious_type = any(
        _issue_type_value(issue.issue_type) in serious_issue_types
        and _severity_value(issue.severity) in {"high", "critical"}
        for issue in result.issues
    )

    passed = (
        float(result.score) >= AI_PASS_THRESHOLD
        and not high_or_critical
        and not serious_type
    )

    return AIProposalQAResult(
        passed=passed,
        score=float(result.score),
        issues=result.issues,
        summary=result.summary,
    )


# ---------------------------------------------------------------------------
# Main AI QA
# ---------------------------------------------------------------------------

def run_ai_proposal_qa(
    validated_scope: ValidatedScope | Dict[str, Any],
    pitch: PitchDraft | Dict[str, Any],
    proposal: ProposalDraft | Dict[str, Any],
) -> AIProposalQAResult:
    """
    Run semantic AI proposal QA using Groq.

    Parameters
    ----------
    validated_scope:
        Canonical ValidatedScope.

    pitch:
        Canonical PitchDraft.

    proposal:
        Canonical ProposalDraft.

    Returns
    -------
    AIProposalQAResult
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "Set GROQ_API_KEY before running AI Proposal QA."
        )

    scope_model = _to_scope(validated_scope)
    pitch_model = _to_pitch(pitch)
    proposal_model = _to_proposal(proposal)

    # Hard gate before calling AI.
    if not scope_model.is_ready_for_proposal:
        return AIProposalQAResult(
            passed=False,
            score=0.0,
            issues=[],
            summary=(
                "AI Proposal QA blocked because the validated scope is "
                "not READY_FOR_PROPOSAL."
            ),
        )

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(
        scope=scope_model,
        pitch=pitch_model,
        proposal=proposal_model,
    )

    response = client.chat.completions.create(
        model=DEFAULT_GROQ_MODEL,
        temperature=0.0,
        max_tokens=5000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ai_proposal_qa_result",
                "strict": True,
                "schema": AIProposalQAResult.model_json_schema(),
            },
        },
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Groq returned an empty response during AI Proposal QA."
        )

    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Groq returned invalid JSON during AI Proposal QA."
        ) from exc

    result = AIProposalQAResult.model_validate(raw)

    return _apply_result_gate(result)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

def ai_proposal_qa(
    validated_scope: ValidatedScope | Dict[str, Any] = None,
    pitch: PitchDraft | Dict[str, Any] = None,
    proposal: ProposalDraft | Dict[str, Any] = None,
    **kwargs: Any,
) -> AIProposalQAResult:
    """
    Backward-compatible wrapper.

    Supports both:

        ai_proposal_qa(
            validated_scope=scope,
            pitch=pitch,
            proposal=proposal,
        )

    and the older accidental keyword:

        ai_proposal_qa(
            scope=scope,
            pitch=pitch,
            proposal=proposal,
        )
    """
    if validated_scope is None:
        validated_scope = kwargs.get("scope")

    if pitch is None:
        pitch = kwargs.get("pitch")

    if proposal is None:
        proposal = kwargs.get("proposal")

    if validated_scope is None:
        raise ValueError("validated_scope is required.")

    if pitch is None:
        raise ValueError("pitch is required.")

    if proposal is None:
        raise ValueError("proposal is required.")

    return run_ai_proposal_qa(
        validated_scope=validated_scope,
        pitch=pitch,
        proposal=proposal,
    )


__all__ = [
    "run_ai_proposal_qa",
    "ai_proposal_qa",
]