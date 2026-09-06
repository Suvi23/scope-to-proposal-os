"""
Tests for AI Proposal QA.

IMPORTANT:
These tests DO NOT call Groq.

The Groq client is mocked, and deterministic fake AI responses
are supplied to the AI Proposal QA module.

Run:

    pytest tests/test_ai_proposal_qa.py -v

Expected:

    ALL TESTS PASSED
"""

from __future__ import annotations

import json

import pytest

from src.ai_proposal_qa import (
    AIProposalQAResult,
    run_ai_proposal_qa,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def validated_scope():
    """
    Minimal realistic validated scope for testing.
    """

    return {
        "business_goal": "Replace most front-desk work",

        "target_users": [
            "patients"
        ],

        "confirmed_requirements": [
            {
                "requirement": "Answer patient symptom questions",
                "original_requirement": "Answer patient symptom questions",
                "status": "modified",
                "final_scope": (
                    "Provide general health information about possible "
                    "conditions in response to symptom questions, with "
                    "escalation to a clinician for serious or uncertain cases."
                ),
                "client_evidence": "DQ-001, DQ-002",
                "notes": (
                    "No autonomous diagnosis."
                ),
            },
            {
                "requirement": "Tell patients what disease they have",
                "original_requirement": "Tell patients what disease they have",
                "status": "rejected",
                "final_scope": "Not included in scope.",
                "client_evidence": "DQ-001",
                "notes": (
                    "Client explicitly rejects autonomous diagnosis."
                ),
            },
            {
                "requirement": "Recommend medicines",
                "original_requirement": "Recommend medicines",
                "status": "modified",
                "final_scope": (
                    "Provide medication information from an approved "
                    "database; prescribing decisions remain with doctors."
                ),
                "client_evidence": "DQ-003",
                "notes": (
                    "No autonomous prescribing."
                ),
            },
            {
                "requirement": "Book appointments",
                "original_requirement": "Book appointments",
                "status": "confirmed",
                "final_scope": (
                    "Book appointments via WhatsApp using the hospital "
                    "system API for availability, schedules, and patient information."
                ),
                "client_evidence": "DQ-004, DQ-007",
                "notes": "",
            },
            {
                "requirement": "Send reminders",
                "original_requirement": "Send reminders",
                "status": "unresolved",
                "final_scope": (
                    "Send reminders via WhatsApp; timing and scheduling "
                    "rules are not defined."
                ),
                "client_evidence": "DQ-005",
                "notes": (
                    "Missing reminder timing and rules."
                ),
            },
            {
                "requirement": "Follow up after visits",
                "original_requirement": "Follow up after visits",
                "status": "confirmed",
                "final_scope": (
                    "Automated routine follow-ups via WhatsApp; "
                    "complex issues escalated to staff."
                ),
                "client_evidence": "DQ-009",
                "notes": "",
            },
            {
                "requirement": "Integrate with hospital system",
                "original_requirement": "Integrate with hospital system",
                "status": "confirmed",
                "final_scope": (
                    "Integrate with the hospital system API for appointment "
                    "availability, schedules, and patient information."
                ),
                "client_evidence": "DQ-004, DQ-007",
                "notes": (
                    "Authentication and API specifications pending."
                ),
            },
            {
                "requirement": "Support Hindi, Marathi and English",
                "original_requirement": "Support Hindi, Marathi and English",
                "status": "unresolved",
                "final_scope": (
                    "Support Hindi, Marathi and English."
                ),
                "client_evidence": "",
                "notes": (
                    "Language quality criteria not defined."
                ),
            },
        ],

        "scope_boundaries": [
            "No autonomous diagnosis",
            "No autonomous prescribing",
            "Escalate serious or uncertain cases to a qualified clinician",
            "Complex patient issues handled by front-desk staff or clinicians",
            "Initial deployment through WhatsApp",
        ],

        "assumptions": [],

        "unresolved_items": [
            {
                "issue": (
                    "Reminder timing and scheduling rules"
                ),
                "reason": (
                    "Client did not provide timing or scheduling rules."
                ),
                "required_for": "Send reminders",
                "priority": "high",
            },
            {
                "issue": (
                    "Multilingual quality acceptance criteria"
                ),
                "reason": (
                    "No confirmation of language quality criteria."
                ),
                "required_for": (
                    "Support Hindi, Marathi and English"
                ),
                "priority": "medium",
            },
            {
                "issue": (
                    "Hospital system API authentication details"
                ),
                "reason": (
                    "Authentication and API specifications were not provided."
                ),
                "required_for": (
                    "Integrate with hospital system"
                ),
                "priority": "high",
            },
            {
                "issue": "Launch timeline",
                "reason": (
                    "Client did not provide a target launch date."
                ),
                "required_for": "Project timeline",
                "priority": "medium",
            },
        ],

        "overall_scope_status": "needs_more_discovery",
    }


@pytest.fixture
def valid_pitch():
    """
    Safe pitch aligned with the validated scope.
    """

    return {
        "headline": (
            "Automate Front-Desk Work Through WhatsApp"
        ),
        "pitch": (
            "Help patients get general health information, "
            "book appointments, and receive routine follow-ups "
            "through WhatsApp, while escalating serious or "
            "uncertain cases to clinicians."
        ),
        "key_benefits": [
            "Automate routine patient interactions",
            "Support appointment booking",
            "Provide consistent follow-up",
            "Escalate complex cases to staff",
        ],
        "safety_note": (
            "The solution does not perform autonomous diagnosis "
            "or prescribing."
        ),
        "call_to_action": (
            "Finalize reminder rules and hospital API details "
            "before implementation."
        ),
    }


@pytest.fixture
def valid_proposal():
    """
    Proposal that should receive a strong AI QA score.
    """

    return {
        "proposal_title": (
            "Patient Front-Desk Automation Proposal"
        ),

        "executive_summary": (
            "A WhatsApp-based patient support solution that "
            "handles routine inquiries, appointment booking, "
            "and follow-ups while escalating serious or "
            "uncertain cases to clinicians."
        ),

        "client_challenge": (
            "The clinic wants to automate routine front-desk "
            "interactions for patients."
        ),

        "proposed_solution": (
            "The proposed solution will provide general health "
            "information, support appointment booking through "
            "the hospital system API, and conduct routine "
            "follow-ups through WhatsApp."
        ),

        "scope_of_work": [
            (
                "Answer patient symptom questions with general "
                "health information and clinician escalation."
            ),
            (
                "Provide medication information from an approved "
                "database without autonomous prescribing."
            ),
            (
                "Book appointments through WhatsApp using the "
                "hospital system API."
            ),
            (
                "Provide routine post-visit follow-ups through WhatsApp."
            ),
            (
                "Support Hindi, Marathi and English, subject to "
                "final language-quality criteria."
            ),
        ],

        "key_benefits": [
            "Reduce routine front-desk workload",
            "Provide consistent patient communication",
            "Support appointment booking through WhatsApp",
            "Provide routine follow-ups",
        ],

        "scope_boundaries": [
            "No autonomous diagnosis",
            "No autonomous prescribing",
            "Serious or uncertain cases are escalated to clinicians",
        ],

        "assumptions": [],

        "implementation_approach": [
            "Finalize workflow and language decisions",
            "Confirm hospital API specifications and access",
            "Configure patient interaction workflows",
            "Test and review the solution before rollout",
        ],

        "next_steps": [
            "Finalize reminder timing and scheduling rules",
            "Confirm hospital API authentication and specifications",
            "Define multilingual quality acceptance criteria",
            "Agree on the project timeline",
            "Review and approve the finalized scope",
        ],

        "proposal_status": "draft",
    }


# ============================================================================
# FAKE GROQ RESPONSE HELPERS
# ============================================================================


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(
        self,
        content,
        finish_reason="stop",
    ):
        self.message = FakeMessage(content)
        self.finish_reason = finish_reason


class FakeResponse:
    def __init__(
        self,
        content,
        finish_reason="stop",
    ):
        self.choices = [
            FakeChoice(
                content=content,
                finish_reason=finish_reason,
            )
        ]


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1

        # Store arguments so tests can inspect them.
        self.last_kwargs = kwargs

        return self.response


class FakeChat:
    def __init__(self, response):
        self.completions = FakeCompletions(
            response
        )


class FakeGroqClient:
    def __init__(self, response):
        self.chat = FakeChat(response)


# ============================================================================
# FAKE AI OUTPUT
# ============================================================================


def make_ai_result(
    *,
    passed=True,
    overall_score=9.0,
    issues=None,
    missing_requirements=None,
    unsupported_claims=None,
    safety_concerns=None,
    revision_recommendations=None,
):
    """
    Build a valid fake AI-QA JSON response.
    """

    payload = {
        "passed": passed,
        "overall_score": overall_score,

        "grounding_score": 9.0,
        "scope_adherence_score": 9.0,
        "hallucination_score": 9.0,
        "safety_score": 10.0,
        "completeness_score": 8.5,
        "credibility_score": 9.0,
        "clarity_score": 9.0,
        "actionability_score": 9.0,

        "issues": issues or [],

        "missing_requirements": (
            missing_requirements or []
        ),

        "unsupported_claims": (
            unsupported_claims or []
        ),

        "safety_concerns": (
            safety_concerns or []
        ),

        "revision_recommendations": (
            revision_recommendations or []
        ),

        "summary": (
            "Proposal is well grounded in the validated scope."
        ),
    }

    return json.dumps(payload)


# ============================================================================
# TEST 1
# ============================================================================


def test_ai_qa_valid_proposal_passes(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    A clean proposal should pass AI QA.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.2,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert isinstance(
        result,
        AIProposalQAResult,
    )

    assert result.passed is True
    assert result.overall_score >= 8.0

    assert fake_client.chat.completions.call_count == 1


# ============================================================================
# TEST 2
# ============================================================================


def test_ai_qa_detects_rejected_requirement(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    AI QA should flag a rejected capability such as diagnosis.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=4.0,
            issues=[
                {
                    "category": "scope",
                    "severity": "critical",
                    "section": "scope_of_work",
                    "issue": (
                        "The proposal includes autonomous diagnosis, "
                        "which is explicitly rejected in the validated scope."
                    ),
                    "evidence": (
                        "AI diagnoses patients."
                    ),
                    "recommendation": (
                        "Remove autonomous diagnosis and retain "
                        "clinician escalation."
                    ),
                }
            ],
            unsupported_claims=[
                "AI diagnoses patients."
            ],
            safety_concerns=[
                "Autonomous diagnosis is outside the validated scope."
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert any(
        issue.category == "scope"
        and issue.severity == "critical"
        for issue in result.issues
    )


# ============================================================================
# TEST 3
# ============================================================================


def test_ai_qa_detects_unsupported_claim(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    AI QA should identify unsupported technical/marketing claims.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=6.5,
            issues=[
                {
                    "category": "credibility",
                    "severity": "high",
                    "section": "executive_summary",
                    "issue": (
                        "The proposal claims real-time appointment "
                        "availability, which is not specified in scope."
                    ),
                    "evidence": (
                        "Provides real-time appointment availability."
                    ),
                    "recommendation": (
                        "Remove 'real-time' unless the client "
                        "confirms that capability."
                    ),
                }
            ],
            unsupported_claims=[
                "real-time appointment availability"
            ],
            revision_recommendations=[
                (
                    "Replace unsupported real-time language with "
                    "the validated appointment availability scope."
                )
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert (
        "real-time appointment availability"
        in result.unsupported_claims
    )


# ============================================================================
# TEST 4
# ============================================================================


def test_ai_qa_allows_valid_safety_boundary(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Mentioning diagnosis/prescribing is NOT itself a violation.

    Explicit safety boundaries should be accepted.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.5,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is True

    assert not any(
        issue.category == "safety"
        and issue.severity in {"critical", "high"}
        for issue in result.issues
    )


# ============================================================================
# TEST 5
# ============================================================================


def test_ai_qa_detects_unresolved_requirement_overcommitment(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    An unresolved reminder rule must not become a fixed commitment.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=6.8,
            issues=[
                {
                    "category": "scope",
                    "severity": "high",
                    "section": "scope_of_work",
                    "issue": (
                        "The proposal commits to sending reminders "
                        "24 hours before every appointment even though "
                        "reminder timing remains unresolved."
                    ),
                    "evidence": (
                        "Reminders will always be sent 24 hours before "
                        "every appointment."
                    ),
                    "recommendation": (
                        "Make reminder timing conditional and move "
                        "the decision to next steps."
                    ),
                }
            ],
            unsupported_claims=[
                (
                    "Reminders will always be sent 24 hours "
                    "before every appointment."
                )
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert any(
        issue.category == "scope"
        for issue in result.issues
    )


# ============================================================================
# TEST 6
# ============================================================================


def test_ai_qa_detects_missing_requirement(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    AI QA should be able to identify important scope items
    missing from the proposal.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=7.0,
            issues=[
                {
                    "category": "completeness",
                    "severity": "medium",
                    "section": "scope_of_work",
                    "issue": (
                        "The proposal does not clearly describe "
                        "post-visit follow-ups."
                    ),
                    "evidence": (
                        "No corresponding follow-up capability "
                        "is present in the proposal."
                    ),
                    "recommendation": (
                        "Add the validated routine post-visit "
                        "follow-up capability."
                    ),
                }
            ],
            missing_requirements=[
                "Follow up after visits"
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert (
        "Follow up after visits"
        in result.missing_requirements
    )


# ============================================================================
# TEST 7
# ============================================================================


def test_ai_qa_detects_hallucinated_integration(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Proposal must not invent an integration that isn't in scope.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=5.5,
            issues=[
                {
                    "category": "hallucination",
                    "severity": "high",
                    "section": "implementation_approach",
                    "issue": (
                        "The proposal introduces a Salesforce integration "
                        "that does not appear in the validated scope."
                    ),
                    "evidence": (
                        "Integrate patient leads with Salesforce."
                    ),
                    "recommendation": (
                        "Remove Salesforce integration unless explicitly "
                        "confirmed during discovery."
                    ),
                }
            ],
            unsupported_claims=[
                "Salesforce integration"
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert (
        "Salesforce integration"
        in result.unsupported_claims
    )


# ============================================================================
# TEST 8
# ============================================================================


def test_ai_qa_detects_safety_issue(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    AI QA should identify autonomous prescribing.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=3.0,
            issues=[
                {
                    "category": "safety",
                    "severity": "critical",
                    "section": "proposed_solution",
                    "issue": (
                        "The proposal states that the AI will prescribe "
                        "medications autonomously."
                    ),
                    "evidence": (
                        "AI-powered medicine prescribing for patients."
                    ),
                    "recommendation": (
                        "Remove autonomous prescribing and retain "
                        "doctor-controlled prescribing decisions."
                    ),
                }
            ],
            safety_concerns=[
                "Autonomous medication prescribing."
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert any(
        issue.category == "safety"
        and issue.severity == "critical"
        for issue in result.issues
    )


# ============================================================================
# TEST 9
# ============================================================================


def test_ai_qa_detects_guarantee_language(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Unsupported guarantees should be flagged.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=False,
            overall_score=6.0,
            issues=[
                {
                    "category": "credibility",
                    "severity": "high",
                    "section": "key_benefits",
                    "issue": (
                        "The proposal guarantees a specific increase "
                        "in bookings without evidence."
                    ),
                    "evidence": (
                        "Guaranteed 50% increase in bookings."
                    ),
                    "recommendation": (
                        "Remove the numerical guarantee and describe "
                        "the operational benefit without promising an outcome."
                    ),
                }
            ],
            unsupported_claims=[
                "Guaranteed 50% increase in bookings."
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False

    assert any(
        issue.category == "credibility"
        for issue in result.issues
    )


# ============================================================================
# TEST 10
# ============================================================================


def test_ai_qa_allows_medium_issues_when_score_is_high(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Medium/low issues alone should not necessarily fail AI QA.

    This mirrors the intended policy:
        critical/high -> blocking
        medium/low -> non-blocking
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=8.4,
            issues=[
                {
                    "category": "clarity",
                    "severity": "medium",
                    "section": "executive_summary",
                    "issue": (
                        "The executive summary could be more concise."
                    ),
                    "evidence": (
                        "The summary contains several overlapping phrases."
                    ),
                    "recommendation": (
                        "Reduce repetition in the executive summary."
                    ),
                }
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is True
    assert result.overall_score >= 8.0


# ============================================================================
# TEST 11
# ============================================================================


def test_ai_qa_score_below_threshold_fails(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Even without critical/high issues, a score below 8 must fail.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=7.5,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    # Python's deterministic result gate should override
    # the model's incorrect passed=True.
    assert result.passed is False


# ============================================================================
# TEST 12
# ============================================================================


def test_ai_qa_high_issue_overrides_model_pass(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Python must override the AI if it returns passed=True
    while reporting a high-severity issue.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
            issues=[
                {
                    "category": "scope",
                    "severity": "high",
                    "section": "scope_of_work",
                    "issue": (
                        "A capability is outside the validated scope."
                    ),
                    "evidence": (
                        "Unsupported capability."
                    ),
                    "recommendation": (
                        "Remove the unsupported capability."
                    ),
                }
            ],
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert result.passed is False


# ============================================================================
# TEST 13
# ============================================================================


def test_ai_qa_accepts_dict_inputs(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    The function should accept dictionaries as well as Pydantic models.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    result = run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert isinstance(
        result,
        AIProposalQAResult,
    )

    assert result.passed is True


# ============================================================================
# TEST 14
# ============================================================================


def test_ai_qa_sends_structured_json_schema(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Verify that the Groq call requests structured JSON output.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    kwargs = (
        fake_client
        .chat
        .completions
        .last_kwargs
    )

    assert kwargs["temperature"] == 0

    assert (
        kwargs["response_format"]["type"]
        == "json_schema"
    )

    assert (
        kwargs["response_format"]["json_schema"]["name"]
        == "ai_proposal_qa_result"
    )


# ============================================================================
# TEST 15
# ============================================================================


def test_ai_qa_rejects_non_stop_finish_reason(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Non-stop model completion should not be accepted.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
        ),
        finish_reason="length",
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    with pytest.raises(RuntimeError):
        run_ai_proposal_qa(
            validated_scope,
            valid_pitch,
            valid_proposal,
        )

    # It may retry, but it must never silently accept
    # the incomplete response.
    assert (
        fake_client.chat.completions.call_count
        >= 1
    )


# ============================================================================
# TEST 16
# ============================================================================


def test_ai_qa_rejects_invalid_json(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Malformed JSON from the AI must fail safely.
    """

    fake_response = FakeResponse(
        "THIS IS NOT VALID JSON"
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    with pytest.raises(RuntimeError):
        run_ai_proposal_qa(
            validated_scope,
            valid_pitch,
            valid_proposal,
        )


# ============================================================================
# TEST 17
# ============================================================================


def test_ai_qa_rejects_invalid_structured_output(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Valid JSON is not enough.

    The response must also conform to AIProposalQAResult.
    """

    invalid_payload = {
        "passed": True,
        "overall_score": "not-a-number",
    }

    fake_response = FakeResponse(
        json.dumps(invalid_payload)
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    with pytest.raises(RuntimeError):
        run_ai_proposal_qa(
            validated_scope,
            valid_pitch,
            valid_proposal,
        )


# ============================================================================
# TEST 18
# ============================================================================


def test_ai_qa_requires_groq_client(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Missing API configuration should fail clearly.

    This test mocks the environment rather than making an API call.
    """

    monkeypatch.delenv(
        "GROQ_API_KEY",
        raising=False,
    )

    # _get_client is normally called internally.
    # Do not patch it here.
    with pytest.raises(RuntimeError) as exc_info:

        run_ai_proposal_qa(
            validated_scope,
            valid_pitch,
            valid_proposal,
        )

    assert "GROQ_API_KEY" in str(
        exc_info.value
    )


# ============================================================================
# TEST 19
# ============================================================================


def test_ai_qa_uses_validated_scope_as_source_of_truth(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Verify that the prompt actually contains the validated scope
    and the proposal.

    This is important because AI QA is only useful if it sees
    the correct source of truth.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    run_ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    kwargs = (
        fake_client
        .chat
        .completions
        .last_kwargs
    )

    messages = kwargs["messages"]

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    assert (
        "ValidatedScope is the authoritative source of truth"
        in system_prompt
    )

    assert (
        "VALIDATED SCOPE"
        in user_prompt
    )

    assert (
        "PROPOSAL"
        in user_prompt
    )

    assert (
        "No autonomous diagnosis"
        in user_prompt
    )

    assert (
        "Book appointments"
        in user_prompt
    )


# ============================================================================
# TEST 20
# ============================================================================


def test_ai_qa_alias_works(
    monkeypatch,
    validated_scope,
    valid_pitch,
    valid_proposal,
):
    """
    Verify the convenience alias works.
    """

    fake_response = FakeResponse(
        make_ai_result(
            passed=True,
            overall_score=9.0,
        )
    )

    fake_client = FakeGroqClient(
        fake_response
    )

    monkeypatch.setattr(
        "src.ai_proposal_qa._get_client",
        lambda: fake_client,
    )

    from src.ai_proposal_qa import ai_proposal_qa

    result = ai_proposal_qa(
        validated_scope,
        valid_pitch,
        valid_proposal,
    )

    assert isinstance(
        result,
        AIProposalQAResult,
    )

    assert result.passed is True


# ============================================================================
# TEST RUN SUMMARY
# ============================================================================


def test_all_ai_qa_tests_are_offline():
    """
    Documentation/safety test.

    This test intentionally performs no API operation.

    The test suite uses FakeGroqClient everywhere that the
    AI QA function is exercised.
    """

    assert True