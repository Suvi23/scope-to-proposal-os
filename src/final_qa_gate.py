"""
Final QA Gate
=============

Combines:

1. Deterministic Proposal QA
2. AI Proposal QA

into one final decision.

Decision rules:

FAIL
----
- deterministic QA has HIGH or CRITICAL issues
- OR deterministic QA fails due to a hard blocking condition

NEEDS_REVISION
--------------
- deterministic QA has no blocking issue
- but AI QA fails or AI score < 8

PASS
----
- deterministic QA passes
- AI QA passes
- AI score >= 8
- no blocking issue exists

Proposal delivery/download must happen ONLY after PASS.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .schemas import (
    AIProposalQAResult,
    FinalQADecision,
    FinalQAGateResult,
    FinalQAIssue,
    PitchDraft,
    ProposalDraft,
    ProposalQAResult,
    QAIssueSeverity,
    ValidatedScope,
)

from .proposal_qa import validate_proposal
from .ai_proposal_qa import run_ai_proposal_qa


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AI_PASS_THRESHOLD = 8.0


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


def _severity_value(
    severity: QAIssueSeverity | str,
) -> str:
    if isinstance(severity, QAIssueSeverity):
        return severity.value

    return str(severity).lower()


def _is_blocking(
    severity: QAIssueSeverity | str,
) -> bool:
    return _severity_value(severity) in {
        "high",
        "critical",
    }


# ---------------------------------------------------------------------------
# Scope gate
# ---------------------------------------------------------------------------

def _scope_gate(
    scope: ValidatedScope,
) -> List[FinalQAIssue]:
    """
    Convert scope-readiness problems into final QA issues.

    These are hard blockers because a proposal should never pass
    if the validated scope itself is unresolved.
    """
    issues: List[FinalQAIssue] = []

    if not scope.is_ready_for_proposal:
        issues.append(
            FinalQAIssue(
                source="scope_gate",
                severity=QAIssueSeverity.CRITICAL,
                issue="Validated scope is not ready for proposal.",
                evidence=(
                    f"overall_scope_status="
                    f"{scope.overall_scope_status.value}"
                ),
                recommendation=(
                    "Resolve the scope before allowing the proposal "
                    "to pass the final QA gate."
                ),
            )
        )

    if scope.unresolved_items:
        for item in scope.unresolved_items:
            issues.append(
                FinalQAIssue(
                    source="scope_gate",
                    severity=(
                        QAIssueSeverity.CRITICAL
                        if item.priority.value in {"high", "critical"}
                        else QAIssueSeverity.HIGH
                    ),
                    issue="Validated scope contains an unresolved item.",
                    evidence=(
                        f"Issue: {item.issue}; "
                        f"Reason: {item.reason}; "
                        f"Required for: {item.required_for}"
                    ),
                    recommendation=(
                        "Resolve this item before the proposal can "
                        "be considered client-ready."
                    ),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Deterministic issue conversion
# ---------------------------------------------------------------------------

def _convert_deterministic_issues(
    result: ProposalQAResult,
) -> List[FinalQAIssue]:
    """Convert canonical ProposalQAIssue objects."""
    converted: List[FinalQAIssue] = []

    for issue in result.issues:
        converted.append(
            FinalQAIssue(
                source="deterministic_qa",
                severity=issue.severity,
                issue=issue.issue,
                evidence=issue.evidence,
                recommendation=issue.recommendation,
            )
        )

    return converted


# ---------------------------------------------------------------------------
# AI issue conversion
# ---------------------------------------------------------------------------

def _convert_ai_issues(
    result: AIProposalQAResult,
) -> List[FinalQAIssue]:
    """Convert canonical AIProposalQAIssue objects."""
    converted: List[FinalQAIssue] = []

    for issue in result.issues:
        converted.append(
            FinalQAIssue(
                source="ai_qa",
                severity=issue.severity,
                issue=issue.issue,
                evidence=issue.evidence,
                recommendation=issue.recommendation,
            )
        )

    return converted


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _determine_final_decision(
    *,
    deterministic_result: ProposalQAResult,
    ai_result: AIProposalQAResult,
    scope_issues: List[FinalQAIssue],
) -> FinalQADecision:
    """
    Determine final QA decision.

    Deterministic hard blockers always take precedence.
    """
    all_deterministic_blockers = any(
        _is_blocking(issue.severity)
        for issue in scope_issues
    ) or any(
        _is_blocking(issue.severity)
        for issue in _convert_deterministic_issues(
            deterministic_result
        )
    )

    if all_deterministic_blockers:
        return FinalQADecision.FAIL

    if not deterministic_result.passed:
        return FinalQADecision.FAIL

    if not ai_result.passed:
        return FinalQADecision.NEEDS_REVISION

    if float(ai_result.score) < AI_PASS_THRESHOLD:
        return FinalQADecision.NEEDS_REVISION

    return FinalQADecision.PASS


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(
    *,
    decision: FinalQADecision,
    deterministic_result: ProposalQAResult,
    ai_result: AIProposalQAResult,
    blocking_count: int,
    revision_count: int,
) -> str:
    """Build concise final QA summary."""
    decision_text = decision.value.replace("_", " ").upper()

    return (
        f"Final QA decision: {decision_text}. "
        f"Deterministic QA: "
        f"{'PASS' if deterministic_result.passed else 'FAIL'} "
        f"({deterministic_result.score:.1f}/10). "
        f"AI QA: "
        f"{'PASS' if ai_result.passed else 'FAIL'} "
        f"({ai_result.score:.1f}/10). "
        f"Blocking issues: {blocking_count}. "
        f"Revision issues: {revision_count}."
    )


# ---------------------------------------------------------------------------
# Main final gate
# ---------------------------------------------------------------------------

def run_final_qa_gate(
    scope: ValidatedScope | Dict[str, Any],
    pitch: PitchDraft | Dict[str, Any],
    proposal: ProposalDraft | Dict[str, Any],
) -> FinalQAGateResult:
    """
    Run the complete final QA gate.

    Parameters
    ----------
    scope:
        ValidatedScope.

    pitch:
        PitchDraft.

    proposal:
        ProposalDraft.

    Returns
    -------
    FinalQAGateResult
    """
    scope_model = _to_scope(scope)
    pitch_model = _to_pitch(pitch)
    proposal_model = _to_proposal(proposal)

    # ---------------------------------------------------------------
    # 1. Scope hard gate
    # ---------------------------------------------------------------

    scope_issues = _scope_gate(scope_model)

    # ---------------------------------------------------------------
    # 2. Deterministic Proposal QA
    # ---------------------------------------------------------------

    deterministic_result = validate_proposal(
        scope=scope_model,
        proposal=proposal_model,
    )

    deterministic_issues = _convert_deterministic_issues(
        deterministic_result
    )

    # ---------------------------------------------------------------
    # 3. AI Proposal QA
    # ---------------------------------------------------------------

    if scope_model.is_ready_for_proposal:
        ai_result = run_ai_proposal_qa(
            validated_scope=scope_model,
            pitch=pitch_model,
            proposal=proposal_model,
        )
    else:
        ai_result = AIProposalQAResult(
            passed=False,
            score=0.0,
            issues=[],
            summary=(
                "AI Proposal QA was not executed because the validated "
                "scope is not ready for proposal."
            ),
        )

    ai_issues = _convert_ai_issues(ai_result)

    # ---------------------------------------------------------------
    # 4. Combine all issues
    # ---------------------------------------------------------------

    all_issues: List[FinalQAIssue] = [
        *scope_issues,
        *deterministic_issues,
        *ai_issues,
    ]

    blocking_issues: List[FinalQAIssue] = [
        issue
        for issue in all_issues
        if _is_blocking(issue.severity)
    ]

    revision_issues: List[FinalQAIssue] = [
        issue
        for issue in all_issues
        if not _is_blocking(issue.severity)
    ]

    # ---------------------------------------------------------------
    # 5. Final decision
    # ---------------------------------------------------------------

    decision = _determine_final_decision(
        deterministic_result=deterministic_result,
        ai_result=ai_result,
        scope_issues=scope_issues,
    )

    # ---------------------------------------------------------------
    # 6. Final result
    # ---------------------------------------------------------------

    summary = _build_summary(
        decision=decision,
        deterministic_result=deterministic_result,
        ai_result=ai_result,
        blocking_count=len(blocking_issues),
        revision_count=len(revision_issues),
    )

    return FinalQAGateResult(
        decision=decision,
        deterministic_passed=deterministic_result.passed,
        ai_passed=ai_result.passed,
        deterministic_score=float(deterministic_result.score),
        ai_score=float(ai_result.score),
        blocking_issues=blocking_issues,
        revision_issues=revision_issues,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

def final_qa_gate(
    scope: ValidatedScope | Dict[str, Any],
    pitch: PitchDraft | Dict[str, Any],
    proposal: ProposalDraft | Dict[str, Any],
) -> FinalQAGateResult:
    """Backward-compatible alias."""
    return run_final_qa_gate(
        scope=scope,
        pitch=pitch,
        proposal=proposal,
    )


def run_final_gate(
    scope: ValidatedScope | Dict[str, Any],
    pitch: PitchDraft | Dict[str, Any],
    proposal: ProposalDraft | Dict[str, Any],
) -> FinalQAGateResult:
    """Additional compatibility alias."""
    return run_final_qa_gate(
        scope=scope,
        pitch=pitch,
        proposal=proposal,
    )


__all__ = [
    "run_final_qa_gate",
    "final_qa_gate",
    "run_final_gate",
]