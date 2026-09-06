"""
Tests for the Final QA Gate.

These tests are intentionally offline:
- No Groq API calls
- AI QA is mocked
- Deterministic QA is mocked where needed

Run:
    pytest test_final_qa_gate.py -v
"""

from unittest.mock import patch

import pytest

from src.final_qa_gate import (
    AI_PASS_THRESHOLD,
    FinalQAGateResult,
    run_final_qa_gate,
)
from src.schemas import (
    ProposalDraft,
    ProposalQAResult,
    PitchDraft,
    ValidatedScope,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_scope():
    return ValidatedScope(
        business_goal="Replace most front-desk work",
        target_users=["patients"],
        confirmed_requirements=[
            {
                "requirement": "Answer patient symptom questions",
                "original_requirement": "Answer patient symptom questions",
                "status": "modified",
                "final_scope": (
                    "Provide general health information about possible "
                    "conditions, with escalation to a clinician for serious "
                    "or uncertain cases."
                ),
                "client_evidence": "DQ-001",
                "notes": "No autonomous diagnosis.",
            },
            {
                "requirement": "Book appointments",
                "original_requirement": "Book appointments",
                "status": "confirmed",
                "final_scope": (
                    "Book appointments via WhatsApp using the hospital "
                    "system API."
                ),
                "client_evidence": "DQ-004",
                "notes": "",
            },
        ],
        scope_boundaries=[
            "No autonomous diagnosis",
            "No autonomous prescribing",
            "Escalate serious or uncertain cases to a qualified clinician",
        ],
        assumptions=[],
        unresolved_items=[],
        overall_scope_status="ready_for_proposal",
    )


@pytest.fixture
def scope_with_unresolved_items(valid_scope):
    valid_scope.unresolved_items = [
        {
            "issue": "Reminder timing",
            "reason": "Timing has not been defined.",
            "required_for": "Send reminders",
            "priority": "high",
        }
    ]
    valid_scope.overall_scope_status = "needs_more_discovery"
    return valid_scope


@pytest.fixture
def valid_pitch():
    return PitchDraft(
        headline="Automate Routine Front-Desk Conversations",
        pitch=(
            "Use WhatsApp to handle routine patient interactions, "
            "appointment booking and follow-ups while escalating "
            "complex cases to staff."
        ),
        key_benefits=[
            "Reduce routine front-desk workload",
            "Support appointment booking through WhatsApp",
            "Provide consistent patient follow-up",
        ],
        safety_note=(
            "The system does not perform autonomous diagnosis or "
            "prescribing and escalates serious or uncertain cases."
        ),
        call_to_action=(
            "Finalize the remaining integration and workflow details "
            "before implementation."
        ),
    )


@pytest.fixture
def valid_proposal():
    return ProposalDraft(
        proposal_title="AI Front-Desk Assistant",
        executive_summary=(
            "A WhatsApp-based assistant to automate routine patient "
            "interactions, appointment booking and follow-ups."
        ),
        client_challenge=(
            "The clinic wants to replace most routine front-desk work "
            "with automated patient interactions."
        ),
        proposed_solution=(
            "Provide general health information, appointment booking "
            "and routine follow-ups through WhatsApp, with escalation "
            "to clinicians for serious or uncertain cases."
        ),
        scope_of_work=[
            "Answer patient symptom questions with general health information",
            "Book appointments through the hospital system API",
            "Send routine follow-ups through WhatsApp",
        ],
        key_benefits=[
            "Reduce routine front-desk workload",
            "Improve access to routine patient support",
            "Automate appointment and follow-up interactions",
        ],
        scope_boundaries=[
            "No autonomous diagnosis",
            "No autonomous prescribing",
            "Serious or uncertain cases are escalated to clinicians",
        ],
        assumptions=[],
        implementation_approach=[
            "Confirm integration requirements and access",
            "Configure patient interaction workflows",
            "Test workflows and prepare the deployment",
        ],
        next_steps=[
            "Confirm hospital API specifications and access requirements",
            "Finalize remaining workflow details",
            "Review and approve the finalized scope",
        ],
        proposal_status="ready_for_client",
    )


@pytest.fixture
def ai_pass_result():
    from src.ai_proposal_qa import AIProposalQAResult

    return AIProposalQAResult(
        passed=True,
        overall_score=9.2,
        grounding_score=9.5,
        scope_adherence_score=9.3,
        hallucination_score=9.4,
        safety_score=9.5,
        completeness_score=8.8,
        credibility_score=9.0,
        clarity_score=9.2,
        actionability_score=9.0,
        issues=[],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary=(
            "Proposal is well grounded and aligned with the validated scope."
        ),
    )


@pytest.fixture
def ai_low_score_result():
    from src.ai_proposal_qa import AIProposalQAResult

    return AIProposalQAResult(
        passed=False,
        overall_score=7.2,
        grounding_score=7.5,
        scope_adherence_score=7.0,
        hallucination_score=7.0,
        safety_score=8.5,
        completeness_score=6.8,
        credibility_score=7.0,
        clarity_score=8.0,
        actionability_score=7.0,
        issues=[],
        missing_requirements=[
            "Reminder workflow is not sufficiently addressed."
        ],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[
            "Clarify the unresolved reminder workflow before client delivery."
        ],
        summary="Proposal requires revision before client delivery.",
    )


@pytest.fixture
def deterministic_pass_result():
    return ProposalQAResult(
        passed=True,
        issues=[],
        checked_sections=[
            "executive_summary",
            "client_challenge",
            "proposed_solution",
            "scope_of_work",
            "key_benefits",
            "scope_boundaries",
            "assumptions",
            "implementation_approach",
            "next_steps",
        ],
        summary="Deterministic proposal QA passed.",
    )


@pytest.fixture
def deterministic_high_issue_result():
    from src.schemas import ProposalQAIssue

    return ProposalQAResult(
        passed=False,
        issues=[
            ProposalQAIssue(
                issue_type="rejected_requirement",
                severity="critical",
                section="scope_of_work",
                message=(
                    "Rejected autonomous diagnosis requirement appears "
                    "as a deliverable."
                ),
                recommendation=(
                    "Remove the rejected requirement from the proposal."
                ),
            )
        ],
        checked_sections=["scope_of_work"],
        summary="Critical deterministic QA issue detected.",
    )


# ============================================================================
# 1. VALID PROPOSAL -> PASS
# ============================================================================

def test_valid_proposal_passes_final_gate(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_pass_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert isinstance(result, FinalQAGateResult)
    assert result.decision == "PASS"
    assert result.passed is True
    assert result.deterministic_passed is True
    assert result.ai_passed is True
    assert result.ai_score >= AI_PASS_THRESHOLD
    assert result.blocking_issues == []


# ============================================================================
# 2. DETERMINISTIC CRITICAL ISSUE -> FAIL
# ============================================================================

def test_deterministic_critical_issue_fails_gate(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_high_issue_result,
    ai_pass_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_high_issue_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "FAIL"
    assert result.passed is False
    assert result.deterministic_passed is False
    assert result.ai_passed is True

    assert len(result.blocking_issues) >= 1

    assert any(
        "rejected" in issue.lower()
        or "diagnosis" in issue.lower()
        for issue in result.blocking_issues
    )


# ============================================================================
# 3. DETERMINISTIC HIGH ISSUE -> FAIL
# ============================================================================

def test_deterministic_high_issue_fails_gate(
    valid_scope,
    valid_pitch,
    valid_proposal,
    ai_pass_result,
):
    from src.schemas import ProposalQAIssue

    deterministic_result = ProposalQAResult(
        passed=False,
        issues=[
            ProposalQAIssue(
                issue_type="safety",
                severity="high",
                section="proposed_solution",
                message="Missing clinician escalation boundary.",
                recommendation="Add explicit clinician escalation.",
            )
        ],
        checked_sections=["proposed_solution"],
        summary="High-severity safety issue.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "FAIL"
    assert result.passed is False
    assert result.deterministic_passed is False


# ============================================================================
# 4. AI HIGH ISSUE -> NEEDS_REVISION
# ============================================================================

def test_ai_high_issue_requires_revision(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
):
    from src.ai_proposal_qa import (
        AIProposalQAResult,
        AIQAIssueType,
    )

    ai_result = AIProposalQAResult(
        passed=False,
        overall_score=8.8,
        grounding_score=9.0,
        scope_adherence_score=8.5,
        hallucination_score=7.5,
        safety_score=9.0,
        completeness_score=8.5,
        credibility_score=8.5,
        clarity_score=9.0,
        actionability_score=8.5,
        issues=[
            AIQAIssueType(
                category="hallucination",
                severity="high",
                section="proposed_solution",
                issue=(
                    "Proposal claims an unsupported hospital "
                    "integration capability."
                ),
                evidence=(
                    "The validated scope does not confirm this capability."
                ),
                recommendation=(
                    "Remove or qualify the unsupported integration claim."
                ),
            )
        ],
        missing_requirements=[],
        unsupported_claims=[
            "Unsupported hospital integration capability."
        ],
        safety_concerns=[],
        revision_recommendations=[
            "Remove unsupported integration claims."
        ],
        summary="High-severity AI QA issue detected.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "NEEDS_REVISION"
    assert result.passed is False
    assert result.deterministic_passed is True
    assert result.ai_passed is False
    assert result.ai_score >= AI_PASS_THRESHOLD
    assert len(result.revision_items) >= 1


# ============================================================================
# 5. AI SCORE BELOW THRESHOLD -> NEEDS_REVISION
# ============================================================================

def test_ai_score_below_threshold_requires_revision(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_low_score_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_low_score_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "NEEDS_REVISION"
    assert result.passed is False
    assert result.deterministic_passed is True
    assert result.ai_score == 7.2
    assert len(result.revision_items) >= 1


# ============================================================================
# 6. NON-BLOCKING AI ISSUE + HIGH SCORE -> PASS
# ============================================================================

def test_non_blocking_ai_issues_can_still_pass(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
):
    from src.ai_proposal_qa import (
        AIProposalQAResult,
        AIQAIssueType,
    )

    ai_result = AIProposalQAResult(
        passed=True,
        overall_score=8.7,
        grounding_score=9.0,
        scope_adherence_score=9.0,
        hallucination_score=9.0,
        safety_score=9.5,
        completeness_score=8.0,
        credibility_score=8.5,
        clarity_score=8.5,
        actionability_score=8.5,
        issues=[
            AIQAIssueType(
                category="clarity",
                severity="medium",
                section="executive_summary",
                issue="The summary could be more concise.",
                evidence=(
                    "The summary contains some redundant wording."
                ),
                recommendation="Shorten the summary slightly.",
            )
        ],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[
            "Consider shortening the executive summary."
        ],
        summary="Minor quality improvement recommended.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "PASS"
    assert result.passed is True
    assert result.ai_score == 8.7
    assert len(result.issues) >= 1


# ============================================================================
# 7. AI SCORE EXACTLY AT THRESHOLD -> PASS
# ============================================================================

def test_ai_score_exactly_at_threshold_passes(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
):
    from src.ai_proposal_qa import AIProposalQAResult

    ai_result = AIProposalQAResult(
        passed=True,
        overall_score=AI_PASS_THRESHOLD,
        grounding_score=8.0,
        scope_adherence_score=8.0,
        hallucination_score=8.0,
        safety_score=9.0,
        completeness_score=8.0,
        credibility_score=8.0,
        clarity_score=8.0,
        actionability_score=8.0,
        issues=[],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary="Meets the minimum AI QA score.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "PASS"
    assert result.passed is True
    assert result.ai_score == AI_PASS_THRESHOLD


# ============================================================================
# 8. DETERMINISTIC FAILURE OVERRIDES EXCELLENT AI
# ============================================================================

def test_deterministic_failure_overrides_excellent_ai_score(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_high_issue_result,
):
    from src.ai_proposal_qa import AIProposalQAResult

    excellent_ai_result = AIProposalQAResult(
        passed=True,
        overall_score=10.0,
        grounding_score=10.0,
        scope_adherence_score=10.0,
        hallucination_score=10.0,
        safety_score=10.0,
        completeness_score=10.0,
        credibility_score=10.0,
        clarity_score=10.0,
        actionability_score=10.0,
        issues=[],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary="Excellent proposal.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_high_issue_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=excellent_ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "FAIL"
    assert result.passed is False
    assert result.ai_score == 10.0
    assert result.deterministic_passed is False


# ============================================================================
# 9. UNRESOLVED SCOPE + AI REVISION ISSUE
# ============================================================================

def test_unresolved_scope_with_ai_revision_issue(
    scope_with_unresolved_items,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_low_score_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_low_score_result,
    ):
        result = run_final_qa_gate(
            validated_scope=scope_with_unresolved_items,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "NEEDS_REVISION"
    assert result.passed is False
    assert result.ai_score < AI_PASS_THRESHOLD


# ============================================================================
# 10. DICT INPUTS ARE SUPPORTED
# ============================================================================

def test_dict_inputs_are_supported(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_pass_result,
):
    scope_dict = valid_scope.model_dump()
    pitch_dict = valid_pitch.model_dump()
    proposal_dict = valid_proposal.model_dump()

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=scope_dict,
            pitch=pitch_dict,
            proposal=proposal_dict,
        )

    assert isinstance(result, FinalQAGateResult)
    assert result.decision == "PASS"
    assert result.passed is True


# ============================================================================
# 11. ISSUES NORMALIZED INTO FINAL SCHEMA
# ============================================================================

def test_issues_are_normalized_into_final_schema(
    valid_scope,
    valid_pitch,
    valid_proposal,
):
    from src.schemas import ProposalQAIssue
    from src.ai_proposal_qa import (
        AIProposalQAResult,
        AIQAIssueType,
    )

    deterministic_result = ProposalQAResult(
        passed=True,
        issues=[
            ProposalQAIssue(
                issue_type="scope",
                severity="medium",
                section="scope_of_work",
                message="Minor scope wording could be clearer.",
                recommendation="Clarify the wording.",
            )
        ],
        checked_sections=["scope_of_work"],
        summary="Minor deterministic issue.",
    )

    ai_result = AIProposalQAResult(
        passed=True,
        overall_score=8.5,
        grounding_score=9.0,
        scope_adherence_score=9.0,
        hallucination_score=9.0,
        safety_score=9.0,
        completeness_score=8.0,
        credibility_score=8.0,
        clarity_score=8.0,
        actionability_score=8.0,
        issues=[
            AIQAIssueType(
                category="clarity",
                severity="low",
                section="executive_summary",
                issue="Could be slightly clearer.",
                evidence="Minor wording issue.",
                recommendation="Simplify wording.",
            )
        ],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary="Minor quality suggestions.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert len(result.issues) == 2

    assert all(
        issue.source in {"deterministic", "ai"}
        for issue in result.issues
    )

    assert all(
        issue.severity in {"low", "medium", "high", "critical"}
        for issue in result.issues
    )


# ============================================================================
# 12. BLOCKING AND REVISION ITEMS ARE SEPARATED
# ============================================================================

def test_blocking_and_revision_items_are_separated(
    valid_scope,
    valid_pitch,
    valid_proposal,
):
    from src.ai_proposal_qa import (
        AIProposalQAResult,
        AIQAIssueType,
    )

    deterministic_result = ProposalQAResult(
        passed=True,
        issues=[],
        checked_sections=["scope_of_work"],
        summary="Deterministic QA passed.",
    )

    ai_result = AIProposalQAResult(
        passed=False,
        overall_score=7.5,
        grounding_score=8.0,
        scope_adherence_score=8.0,
        hallucination_score=8.0,
        safety_score=8.0,
        completeness_score=7.0,
        credibility_score=8.0,
        clarity_score=8.0,
        actionability_score=7.0,
        issues=[
            AIQAIssueType(
                category="completeness",
                severity="medium",
                section="next_steps",
                issue="One discovery dependency should be clarified.",
                evidence="An unresolved item remains.",
                recommendation="Add the dependency to next steps.",
            )
        ],
        missing_requirements=["Reminder timing"],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[
            "Clarify reminder timing."
        ],
        summary="Revision required due to low score.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "NEEDS_REVISION"
    assert result.blocking_issues == []
    assert len(result.revision_items) >= 1


# ============================================================================
# 13. ALIAS EXISTS
# ============================================================================

def test_final_qa_gate_alias_exists():
    from src.final_qa_gate import final_qa_gate

    assert callable(final_qa_gate)


# ============================================================================
# 14. VALID DECISION VALUES
# ============================================================================

def test_final_result_contains_valid_decision_values(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_pass_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision in {
        "PASS",
        "NEEDS_REVISION",
        "FAIL",
    }


# ============================================================================
# 15. PASS REQUIRES BOTH GATES
# ============================================================================

def test_pass_requires_both_gates_to_pass(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
):
    from src.ai_proposal_qa import AIProposalQAResult

    ai_result = AIProposalQAResult(
        passed=False,
        overall_score=7.9,
        grounding_score=8.0,
        scope_adherence_score=8.0,
        hallucination_score=8.0,
        safety_score=9.0,
        completeness_score=7.0,
        credibility_score=8.0,
        clarity_score=8.0,
        actionability_score=7.0,
        issues=[],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary="Below final acceptance threshold.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.deterministic_passed is True
    assert result.ai_passed is False
    assert result.passed is False
    assert result.decision == "NEEDS_REVISION"


# ============================================================================
# 16. CRITICAL DETERMINISTIC ISSUE IS ABSOLUTE BLOCKER
# ============================================================================

def test_critical_deterministic_issue_is_absolute_blocker(
    valid_scope,
    valid_pitch,
    valid_proposal,
):
    from src.schemas import ProposalQAIssue
    from src.ai_proposal_qa import AIProposalQAResult

    deterministic_result = ProposalQAResult(
        passed=False,
        issues=[
            ProposalQAIssue(
                issue_type="safety",
                severity="critical",
                section="scope_of_work",
                message="Unsafe autonomous medical capability.",
                recommendation="Remove the unsafe capability.",
            )
        ],
        checked_sections=["scope_of_work"],
        summary="Critical safety failure.",
    )

    ai_result = AIProposalQAResult(
        passed=True,
        overall_score=10.0,
        grounding_score=10.0,
        scope_adherence_score=10.0,
        hallucination_score=10.0,
        safety_score=10.0,
        completeness_score=10.0,
        credibility_score=10.0,
        clarity_score=10.0,
        actionability_score=10.0,
        issues=[],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=[],
        revision_recommendations=[],
        summary="AI QA passed.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "FAIL"
    assert result.passed is False
    assert result.blocking_issues


# ============================================================================
# 17. AI HIGH / CRITICAL ISSUE CANNOT PASS
# ============================================================================

@pytest.mark.parametrize("severity", ["high", "critical"])
def test_ai_high_or_critical_issue_cannot_pass(
    severity,
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
):
    from src.ai_proposal_qa import (
        AIProposalQAResult,
        AIQAIssueType,
    )

    ai_result = AIProposalQAResult(
        passed=False,
        overall_score=9.5,
        grounding_score=9.5,
        scope_adherence_score=9.5,
        hallucination_score=9.5,
        safety_score=9.5,
        completeness_score=9.5,
        credibility_score=9.5,
        clarity_score=9.5,
        actionability_score=9.5,
        issues=[
            AIQAIssueType(
                category="safety",
                severity=severity,
                section="scope_of_work",
                issue="Serious safety issue detected.",
                evidence=(
                    "Proposal contains a problematic capability."
                ),
                recommendation=(
                    "Remove or revise the problematic capability."
                ),
            )
        ],
        missing_requirements=[],
        unsupported_claims=[],
        safety_concerns=["Serious safety issue."],
        revision_recommendations=[
            "Remove the problematic capability."
        ],
        summary="Safety issue prevents approval.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "NEEDS_REVISION"
    assert result.passed is False
    assert result.ai_passed is False


# ============================================================================
# 18. NON-BLOCKING DETERMINISTIC ISSUE DOES NOT FAIL
# ============================================================================

def test_non_blocking_deterministic_issue_does_not_fail_gate(
    valid_scope,
    valid_pitch,
    valid_proposal,
    ai_pass_result,
):
    from src.schemas import ProposalQAIssue

    deterministic_result = ProposalQAResult(
        passed=True,
        issues=[
            ProposalQAIssue(
                issue_type="repetition",
                severity="medium",
                section="executive_summary",
                message="Some wording is repetitive.",
                recommendation="Reduce repeated phrasing.",
            )
        ],
        checked_sections=["executive_summary"],
        summary="Minor deterministic issue.",
    )

    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.decision == "PASS"
    assert result.passed is True
    assert result.deterministic_passed is True


# ============================================================================
# 19. AI SCORE IS PROPAGATED
# ============================================================================

def test_ai_score_is_propagated(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_pass_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert result.ai_score == ai_pass_result.overall_score


# ============================================================================
# 20. SUMMARY IS GENERATED
# ============================================================================

def test_final_result_contains_summary(
    valid_scope,
    valid_pitch,
    valid_proposal,
    deterministic_pass_result,
    ai_pass_result,
):
    with patch(
        "src.final_qa_gate.validate_proposal",
        return_value=deterministic_pass_result,
    ), patch(
        "src.final_qa_gate.run_ai_proposal_qa",
        return_value=ai_pass_result,
    ):
        result = run_final_qa_gate(
            validated_scope=valid_scope,
            pitch=valid_pitch,
            proposal=valid_proposal,
        )

    assert isinstance(result.summary, str)
    assert result.summary.strip() != ""
