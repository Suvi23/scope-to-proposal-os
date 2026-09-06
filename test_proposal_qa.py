"""
Proposal QA Test Suite

Tests the deterministic Proposal QA layer against intentionally
bad and good proposals.

The QA layer must detect:

1. Rejected requirements leaking into deliverables
2. Unresolved requirements presented as confirmed scope
3. Unsupported guarantee language
4. Missing healthcare safety boundaries
5. Missing clinician escalation
6. Missing / weak Next Steps
7. Proposal status mismatch
8. Obsolete open_items field
9. Excessive repetition

No Groq/API calls are made in this test.
"""

from src.proposal_qa import validate_proposal
from src.schemas import (
    ProposalDraft,
    ValidatedScope,
)


# ============================================================
# SYNTHETIC VALIDATED SCOPE
# ============================================================

def build_validated_scope() -> ValidatedScope:
    """
    Build a representative validated scope for testing.

    This mirrors the healthcare scenario used throughout
    the project.
    """

    return ValidatedScope(
        business_goal="Replace most front-desk work",

        target_users=[
            "patients"
        ],

        confirmed_requirements=[

            # ------------------------------------------------
            # MODIFIED
            # ------------------------------------------------

            {
                "requirement": "Answer patient symptom questions",

                "original_requirement":
                    "Answer patient symptom questions",

                "status": "modified",

                "final_scope":
                    "Provide general health information about "
                    "possible conditions in response to symptom "
                    "questions, with escalation to a clinician "
                    "for serious or uncertain cases.",

                "client_evidence":
                    "DQ-001, DQ-002, DQ-006, DQ-008",

                "notes":
                    "Clarified that no autonomous diagnosis "
                    "is performed.",
            },

            # ------------------------------------------------
            # REJECTED
            # ------------------------------------------------

            {
                "requirement":
                    "Tell patients what disease they have",

                "original_requirement":
                    "Tell patients what disease they have",

                "status":
                    "rejected",

                "final_scope":
                    "Not included in scope.",

                "client_evidence":
                    "DQ-001, DQ-002, DQ-006, DQ-008",

                "notes":
                    "Client explicitly rejects autonomous "
                    "diagnosis.",
            },

            # ------------------------------------------------
            # MODIFIED
            # ------------------------------------------------

            {
                "requirement":
                    "Recommend medicines",

                "original_requirement":
                    "Recommend medicines",

                "status":
                    "modified",

                "final_scope":
                    "Provide medication information from an "
                    "approved database; prescribing decisions "
                    "remain with doctors.",

                "client_evidence":
                    "DQ-003",

                "notes":
                    "Clarified that no prescribing is performed.",
            },

            # ------------------------------------------------
            # CONFIRMED
            # ------------------------------------------------

            {
                "requirement":
                    "Book appointments",

                "original_requirement":
                    "Book appointments",

                "status":
                    "confirmed",

                "final_scope":
                    "Book appointments via WhatsApp using the "
                    "hospital system API for availability, "
                    "schedules, and patient information.",

                "client_evidence":
                    "DQ-004, DQ-007, DQ-009, DQ-010",

                "notes":
                    "Integration details pending.",
            },

            # ------------------------------------------------
            # UNRESOLVED
            # ------------------------------------------------

            {
                "requirement":
                    "Send reminders",

                "original_requirement":
                    "Send reminders",

                "status":
                    "unresolved",

                "final_scope":
                    "Send reminders via WhatsApp; timing and "
                    "scheduling rules are not defined.",

                "client_evidence":
                    "DQ-005",

                "notes":
                    "Missing reminder timing and rules.",
            },

            # ------------------------------------------------
            # CONFIRMED
            # ------------------------------------------------

            {
                "requirement":
                    "Follow up after visits",

                "original_requirement":
                    "Follow up after visits",

                "status":
                    "confirmed",

                "final_scope":
                    "Automated routine follow-ups via WhatsApp; "
                    "complex issues escalated to staff.",

                "client_evidence":
                    "DQ-009, DQ-010",

                "notes":
                    "Scope defined.",
            },

            # ------------------------------------------------
            # CONFIRMED
            # ------------------------------------------------

            {
                "requirement":
                    "Integrate with hospital system",

                "original_requirement":
                    "Integrate with hospital system",

                "status":
                    "confirmed",

                "final_scope":
                    "Integrate with the hospital system API for "
                    "appointment availability, schedules, and "
                    "patient information.",

                "client_evidence":
                    "DQ-004, DQ-007",

                "notes":
                    "Integration details pending.",
            },

            # ------------------------------------------------
            # UNRESOLVED
            # ------------------------------------------------

            {
                "requirement":
                    "Support Hindi, Marathi and English",

                "original_requirement":
                    "Support Hindi, Marathi and English",

                "status":
                    "unresolved",

                "final_scope":
                    "Support the specified languages.",

                "client_evidence":
                    "",

                "notes":
                    "No confirmation of language support "
                    "or quality criteria.",
            },
        ],

        scope_boundaries=[
            "No autonomous diagnosis",
            "No autonomous prescribing",
            "Escalate serious or uncertain cases to a qualified clinician",
            "Complex patient issues handled by front-desk staff or clinicians",
            "Initial deployment through WhatsApp",
        ],

        assumptions=[],

        unresolved_items=[

            {
                "issue":
                    "Reminder timing and scheduling rules for Send reminders",

                "reason":
                    "Client did not provide timing or scheduling rules.",

                "required_for":
                    "Send reminders",

                "priority":
                    "high",
            },

            {
                "issue":
                    "Multilingual quality acceptance criteria for Hindi, Marathi, English support",

                "reason":
                    "No confirmation of language support or quality criteria.",

                "required_for":
                    "Support Hindi, Marathi and English",

                "priority":
                    "medium",
            },

            {
                "issue":
                    "Hospital system API authentication details",

                "reason":
                    "Client confirmed API availability but did not provide authentication or specifications.",

                "required_for":
                    "Integrate with hospital system",

                "priority":
                    "high",
            },

            {
                "issue":
                    "Launch timeline",

                "reason":
                    "Client did not provide a target launch date.",

                "required_for":
                    "Project timeline",

                "priority":
                    "medium",
            },
        ],

        overall_scope_status="needs_more_discovery",
    )


# ============================================================
# BASE VALID PROPOSAL
# ============================================================

def build_valid_proposal() -> ProposalDraft:
    """
    Build a proposal that should pass QA.
    """

    return ProposalDraft(

        proposal_title=
            "WhatsApp Front-Desk Automation Proposal",

        executive_summary=(
            "This proposal outlines a WhatsApp-based "
            "front-desk automation solution for routine "
            "patient interactions, appointment workflows, "
            "and follow-up communication. Health information "
            "will remain within the validated safety boundaries "
            "with escalation to qualified clinicians where "
            "required."
        ),

        client_challenge=(
            "The client wants to replace most front-desk work "
            "through automated patient communication while "
            "maintaining appropriate clinician involvement "
            "for complex or uncertain cases."
        ),

        proposed_solution=(
            "The solution will provide general health "
            "information in response to symptom questions, "
            "with escalation to clinicians for serious or "
            "uncertain cases. It will provide medication "
            "information from an approved database while "
            "prescribing decisions remain with doctors. "
            "Patients will be able to book appointments "
            "through WhatsApp using the hospital system API. "
            "Routine post-visit follow-ups will also be "
            "supported through WhatsApp."
        ),

        scope_of_work=[

            "WhatsApp patient communication",

            "General health information with clinician escalation",

            "Medication information from an approved database",

            "Appointment booking using the hospital system API",

            "Routine post-visit follow-up communication",

            "Hospital system integration for appointment and patient information",
        ],

        key_benefits=[

            "Reduce routine front-desk work",

            "Support patient appointment workflows",

            "Provide general health information through WhatsApp",

            "Enable routine follow-up communication",

            "Keep clinicians involved in complex or uncertain cases",
        ],

        scope_boundaries=[

            "No autonomous diagnosis",

            "No autonomous prescribing",

            "Escalate serious or uncertain cases to a qualified clinician",

            "Complex patient issues handled by front-desk staff or clinicians",

            "Initial deployment through WhatsApp",
        ],

        assumptions=[],

        implementation_approach=[

            "Discovery and scope finalization",

            "Solution design",

            "Development and integration",

            "Testing and validation",

            "Deployment",
        ],

        next_steps=[

            "Finalize the remaining reminder workflow and language decisions with the client.",

            "Confirm hospital API specifications, authentication requirements, and required access.",

            "Agree on the project timeline and implementation dependencies.",

            "Review and approve the finalized scope.",

            "Proceed to implementation once the outstanding decisions and dependencies are resolved.",
        ],

        proposal_status="draft",
    )


# ============================================================
# HELPER
# ============================================================

def get_issue_types(result):
    """
    Return issue types from QA result.
    """

    return {
        issue.issue_type
        for issue in result.issues
    }


def print_result(test_name, result):
    """
    Print a readable QA result.
    """

    print()
    print("=" * 70)
    print(test_name)
    print("=" * 70)

    print(
        "PASSED:",
        result.passed
    )

    if result.issues:

        for issue in result.issues:

            print(
                f"- [{issue.severity.upper()}] "
                f"{issue.issue_type}: "
                f"{issue.message}"
            )

    else:

        print("- No QA issues detected.")


# ============================================================
# TEST 1
# REJECTED REQUIREMENT LEAK
# ============================================================

def test_rejected_requirement_leak():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.proposed_solution += (
        " The AI will tell patients what disease they have."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 1 - Rejected Requirement Leak",
        result,
    )

    assert not result.passed

    assert (
        "rejected_requirement"
        in get_issue_types(result)
    )

    print(
        "✓ Rejected requirement correctly detected"
    )


# ============================================================
# TEST 2
# UNRESOLVED REQUIREMENT PRESENTED AS CONFIRMED
# ============================================================

def test_unresolved_requirement_leak():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.scope_of_work.append(
        "Automated reminder scheduling with configurable "
        "timing rules."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 2 - Unresolved Requirement Leak",
        result,
    )

    assert not result.passed

    assert (
        "unresolved_requirement"
        in get_issue_types(result)
    )

    print(
        "✓ Unresolved requirement correctly detected"
    )


# ============================================================
# TEST 3
# GUARANTEE LANGUAGE
# ============================================================

def test_guarantee_language():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.key_benefits.append(
        "The system guarantees 100% accurate responses."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 3 - Unsupported Guarantee Language",
        result,
    )

    assert (
        "guarantee_language"
        in get_issue_types(result)
    )

    print(
        "✓ Unsupported guarantee language detected"
    )


# ============================================================
# TEST 4
# SEAMLESS / REAL-TIME GUARANTEE STYLE LANGUAGE
# ============================================================

def test_unsupported_strong_language():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.proposed_solution += (
        " The system will provide seamless real-time "
        "hospital integration and always deliver accurate "
        "results."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 4 - Unsupported Strong Claims",
        result,
    )

    assert (
        "guarantee_language"
        in get_issue_types(result)
    )

    print(
        "✓ Strong unsupported claims detected"
    )


# ============================================================
# TEST 5
# MISSING DIAGNOSIS SAFETY BOUNDARY
# ============================================================

def test_missing_diagnosis_boundary():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.scope_boundaries = [
        "Initial deployment through WhatsApp"
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 5 - Missing Diagnosis Safety Boundary",
        result,
    )

    assert not result.passed

    assert (
        "safety"
        in get_issue_types(result)
    )

    print(
        "✓ Missing diagnosis safety boundary detected"
    )


# ============================================================
# TEST 6
# MISSING PRESCRIBING SAFETY BOUNDARY
# ============================================================

def test_missing_prescribing_boundary():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.scope_boundaries = [
        "No autonomous diagnosis",
        "Initial deployment through WhatsApp",
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 6 - Missing Prescribing Safety Boundary",
        result,
    )

    assert not result.passed

    assert (
        "safety"
        in get_issue_types(result)
    )

    print(
        "✓ Missing prescribing safety boundary detected"
    )


# ============================================================
# TEST 7
# MISSING CLINICIAN ESCALATION
# ============================================================

def test_missing_clinician_escalation():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.executive_summary = (
        "This proposal describes a WhatsApp-based "
        "patient communication solution."
    )

    proposal.proposed_solution = (
        "The solution will provide general health "
        "information and appointment workflows."
    )

    proposal.scope_boundaries = [
        "No autonomous diagnosis",
        "No autonomous prescribing",
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 7 - Missing Clinician Escalation",
        result,
    )

    assert not result.passed

    assert (
        "safety"
        in get_issue_types(result)
    )

    print(
        "✓ Missing clinician escalation detected"
    )


# ============================================================
# TEST 8
# EMPTY NEXT STEPS
# ============================================================

def test_missing_next_steps():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.next_steps = []

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 8 - Missing Next Steps",
        result,
    )

    assert not result.passed

    assert (
        "missing_next_step"
        in get_issue_types(result)
    )

    print(
        "✓ Missing Next Steps correctly detected"
    )


# ============================================================
# TEST 9
# NEXT STEPS DO NOT ADDRESS UNRESOLVED ITEMS
# ============================================================

def test_next_steps_do_not_address_unresolved_items():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.next_steps = [
        "Review the proposal.",
        "Approve the proposal.",
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 9 - Next Steps Do Not Address Unresolved Items",
        result,
    )

    assert (
        "missing_next_step"
        in get_issue_types(result)
    )

    print(
        "✓ Unresolved items coverage problem detected"
    )


# ============================================================
# TEST 10
# WRONG PROPOSAL STATUS
# ============================================================

def test_wrong_proposal_status():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.proposal_status = "ready_for_client"

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 10 - Incorrect Proposal Status",
        result,
    )

    assert not result.passed

    assert (
        "status"
        in get_issue_types(result)
    )

    print(
        "✓ Incorrect proposal status detected"
    )


# ============================================================
# TEST 11
# READY_FOR_CLIENT WITH UNRESOLVED ITEMS
# ============================================================

def test_ready_for_client_with_unresolved_items():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.proposal_status = "ready_for_client"

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 11 - Ready For Client With Unresolved Items",
        result,
    )

    assert not result.passed

    assert (
        "status"
        in get_issue_types(result)
    )

    print(
        "✓ Ready-for-client status correctly rejected"
    )


# ============================================================
# TEST 12
# VALID PROPOSAL
# ============================================================

def test_valid_proposal():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 12 - Valid Proposal",
        result,
    )

    assert result.passed

    assert len(result.issues) == 0

    print(
        "✓ Valid proposal passed QA"
    )


# ============================================================
# TEST 13
# NO REJECTED REQUIREMENT LEAK THROUGH KEY BENEFITS
# ============================================================

def test_rejected_requirement_in_key_benefits():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.key_benefits.append(
        "Patients can receive a disease diagnosis "
        "from the AI."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 13 - Rejected Requirement In Key Benefits",
        result,
    )

    assert not result.passed

    assert (
        "rejected_requirement"
        in get_issue_types(result)
    )

    print(
        "✓ Rejected requirement in benefits detected"
    )


# ============================================================
# TEST 14
# NO PRESCRIBING LEAK THROUGH SCOPE OF WORK
# ============================================================

def test_prescribing_leak():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.scope_of_work.append(
        "AI-powered medicine prescribing for patients."
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 14 - Autonomous Prescribing Leak",
        result,
    )

    assert not result.passed

    # The QA may identify this through unsupported/rejected
    # wording depending on similarity. Safety is also expected
    # to remain preserved.
    assert (
        "safety" in get_issue_types(result)
        or "unsupported_claim" in get_issue_types(result)
        or "guarantee_language" in get_issue_types(result)
    )

    print(
        "✓ Autonomous prescribing risk detected"
    )


# ============================================================
# TEST 15
# VALID PROPOSAL MUST NOT CONTAIN OPEN_ITEMS
# ============================================================

def test_open_items_removed():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    # ProposalDraft intentionally has no open_items field.
    assert not hasattr(
        proposal,
        "open_items"
    )

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 15 - Open Items Removed",
        result,
    )

    assert "format" not in get_issue_types(result)

    print(
        "✓ Obsolete open_items field is absent"
    )


# ============================================================
# TEST 16
# EXCESSIVE REPETITION
# ============================================================

def test_excessive_repetition():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    repeated_sentence = (
        "The solution provides appointment booking "
        "through WhatsApp using the hospital system API "
        "for appointment availability and patient information."
    )

    proposal.executive_summary = repeated_sentence

    proposal.client_challenge = repeated_sentence

    proposal.proposed_solution = repeated_sentence

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 16 - Excessive Repetition",
        result,
    )

    assert (
        "repetition"
        in get_issue_types(result)
    )

    print(
        "✓ Excessive repetition detected"
    )


# ============================================================
# TEST 17
# NEXT STEPS MUST BE ACTION ORIENTED
# ============================================================

def test_non_actionable_next_steps():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.next_steps = [
        "Reminder timing.",
        "Language support.",
        "Hospital API.",
        "Launch timeline.",
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    print_result(
        "TEST 17 - Non-Actionable Next Steps",
        result,
    )

    assert (
        "missing_next_step"
        in get_issue_types(result)
    )

    print(
        "✓ Non-actionable Next Steps detected"
    )


# ============================================================
# TEST 18
# CONFIRMED REQUIREMENTS SHOULD REMAIN ALLOWED
# ============================================================

def test_confirmed_requirements_allowed():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    result = validate_proposal(
        proposal,
        scope,
    )

    rejected = [
        issue
        for issue in result.issues
        if issue.issue_type == "rejected_requirement"
    ]

    unresolved = [
        issue
        for issue in result.issues
        if issue.issue_type == "unresolved_requirement"
    ]

    assert len(rejected) == 0

    assert len(unresolved) == 0

    print(
        "✓ Confirmed and modified requirements remain allowed"
    )


# ============================================================
# TEST 19
# SAFETY BOUNDARIES SHOULD NOT BE FLAGGED AS LEAKS
# ============================================================

def test_safety_boundaries_are_not_requirement_leaks():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    proposal.scope_boundaries = [
        "No autonomous diagnosis",
        "No autonomous prescribing",
        "Escalate serious or uncertain cases to a qualified clinician",
        "Complex patient issues handled by front-desk staff or clinicians",
        "Initial deployment through WhatsApp",
    ]

    result = validate_proposal(
        proposal,
        scope,
    )

    rejected_issues = [
        issue
        for issue in result.issues
        if issue.issue_type == "rejected_requirement"
    ]

    assert len(rejected_issues) == 0

    print(
        "✓ Safety boundaries are not incorrectly flagged "
        "as rejected capabilities"
    )


# ============================================================
# TEST 20
# FINAL HEALTHCARE SAFETY CHECK
# ============================================================

def test_healthcare_safety_is_preserved():

    scope = build_validated_scope()

    proposal = build_valid_proposal()

    result = validate_proposal(
        proposal,
        scope,
    )

    safety_issues = [
        issue
        for issue in result.issues
        if issue.issue_type == "safety"
    ]

    assert len(safety_issues) == 0

    proposal_text = " ".join([
        proposal.executive_summary,
        proposal.proposed_solution,
        " ".join(proposal.scope_boundaries),
    ]).lower()

    assert (
        "no autonomous diagnosis"
        in proposal_text
    )

    assert (
        "no autonomous prescribing"
        in proposal_text
    )

    assert (
        "clinician"
        in proposal_text
    )

    print(
        "✓ Healthcare safety boundaries preserved"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("PROPOSAL QA TEST SUITE")
    print("=" * 70)

    print(
        "Running deterministic QA tests."
    )

    print(
        "No Groq API calls are used."
    )

    print()

    test_rejected_requirement_leak()

    test_unresolved_requirement_leak()

    test_guarantee_language()

    test_unsupported_strong_language()

    test_missing_diagnosis_boundary()

    test_missing_prescribing_boundary()

    test_missing_clinician_escalation()

    test_missing_next_steps()

    test_next_steps_do_not_address_unresolved_items()

    test_wrong_proposal_status()

    test_ready_for_client_with_unresolved_items()

    test_valid_proposal()

    test_rejected_requirement_in_key_benefits()

    test_prescribing_leak()

    test_open_items_removed()

    test_excessive_repetition()

    test_non_actionable_next_steps()

    test_confirmed_requirements_allowed()

    test_safety_boundaries_are_not_requirement_leaks()

    test_healthcare_safety_is_preserved()

    print()
    print("=" * 70)
    print("✓ ALL PROPOSAL QA TESTS PASSED")
    print("=" * 70)