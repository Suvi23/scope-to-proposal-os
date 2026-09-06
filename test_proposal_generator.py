"""
Isolated test for Proposal Generator.

This test uses a synthetic, fully validated ValidatedScope and PitchDraft.

Only the proposal generator's Groq call is exercised.

Run:

    python test_proposal_generator.py
"""

import json

from src.proposal_generator import generate_proposal
from src.schemas import PitchDraft, ValidatedScope, ValidationStatus


# ============================================================
# SYNTHETIC VALIDATED SCOPE
# ============================================================

validated_scope = ValidatedScope(
    business_goal="Reduce front-desk workload and improve patient booking",
    target_users=[
        "patients",
        "front-desk staff",
    ],
    confirmed_requirements=[
        ValidationStatus(
            requirement="Answer patient symptom questions",
            original_requirement="Answer patient symptom questions",
            status="modified",
            final_scope=(
                "Provide general health information in response to "
                "patient symptom questions, without diagnosing conditions, "
                "with escalation to a qualified clinician for serious, "
                "uncertain, or high-risk cases."
            ),
            client_evidence="DQ-001, DQ-002, DQ-006",
            notes=(
                "Medical information is informational only. "
                "No autonomous diagnosis."
            ),
        ),
        ValidationStatus(
            requirement="Tell patients what disease they have",
            original_requirement="Tell patients what disease they have",
            status="rejected",
            final_scope="",
            client_evidence="DQ-001, DQ-002, DQ-006",
            notes="Autonomous diagnosis is explicitly excluded.",
        ),
        ValidationStatus(
            requirement="Recommend medicines",
            original_requirement="Recommend medicines",
            status="modified",
            final_scope=(
                "Provide general medication information from an "
                "approved information source. Prescribing and treatment "
                "decisions remain with qualified doctors."
            ),
            client_evidence="DQ-003",
            notes="No autonomous prescribing or treatment decisions.",
        ),
        ValidationStatus(
            requirement="Book appointments",
            original_requirement="Book appointments",
            status="confirmed",
            final_scope=(
                "Book patient appointments through WhatsApp using the "
                "hospital scheduling system API for availability and "
                "appointment scheduling."
            ),
            client_evidence="DQ-004, DQ-007",
            notes="Appointment workflow confirmed.",
        ),
        ValidationStatus(
            requirement="Send reminders",
            original_requirement="Send reminders",
            status="confirmed",
            final_scope=(
                "Send appointment reminders to patients through WhatsApp "
                "using the confirmed appointment schedule."
            ),
            client_evidence="DQ-005",
            notes="Reminder workflow confirmed.",
        ),
        ValidationStatus(
            requirement="Follow up after visits",
            original_requirement="Follow up after visits",
            status="confirmed",
            final_scope=(
                "Send automated routine post-visit follow-ups through "
                "WhatsApp, with complex or clinically sensitive cases "
                "escalated to staff or clinicians."
            ),
            client_evidence="DQ-008, DQ-009",
            notes="Follow-up workflow confirmed.",
        ),
        ValidationStatus(
            requirement="Integrate with hospital system",
            original_requirement="Integrate with hospital system",
            status="confirmed",
            final_scope=(
                "Integrate with the hospital scheduling API for "
                "appointment availability and booking workflows."
            ),
            client_evidence="DQ-004, DQ-007",
            notes="Required integration is confirmed.",
        ),
        ValidationStatus(
            requirement="Support Hindi, Marathi and English",
            original_requirement="Support Hindi, Marathi and English",
            status="confirmed",
            final_scope=(
                "Support patient conversations in Hindi, Marathi, "
                "and English for the defined patient-support workflows."
            ),
            client_evidence="DQ-010",
            notes="Supported languages confirmed.",
        ),
    ],
    scope_boundaries=[
        "No autonomous diagnosis",
        "No autonomous prescribing",
        "No treatment decisions by the AI",
        "Escalate serious, uncertain, or clinically sensitive cases",
        "Complex patient issues are handled by staff or clinicians",
        "Appointment booking uses the confirmed hospital scheduling API",
        "Initial deployment through WhatsApp",
    ],
    assumptions=[
        "The hospital provides the required scheduling API access.",
        "The client provides approved patient-information content.",
        "Human staff are available for escalated cases.",
    ],
    unresolved_items=[],
    overall_scope_status="ready_for_proposal",
)


# ============================================================
# SYNTHETIC PITCH
# ============================================================

pitch = PitchDraft(
    title="WhatsApp-Based Patient Support and Appointment System",
    opening=(
        "Help patients get timely support and appointment assistance "
        "through WhatsApp while reducing routine front-desk workload."
    ),
    value_proposition=(
        "A multilingual WhatsApp patient-support workflow that provides "
        "general health information, appointment booking, reminders, "
        "and routine follow-ups while keeping clinicians responsible "
        "for diagnosis, prescribing, and treatment decisions."
    ),
    tailored_pitch=(
        "Patients can receive general health information, book "
        "appointments through the hospital scheduling API, receive "
        "WhatsApp reminders, and get routine post-visit follow-ups "
        "in Hindi, Marathi, or English. Serious, uncertain, or "
        "clinically sensitive cases are escalated to qualified staff "
        "or clinicians."
    ),
    key_benefits=[
        "Reduce routine front-desk workload",
        "Support multilingual patient communication through WhatsApp",
        "Automate appointment booking and reminders",
        "Enable structured post-visit follow-up",
        "Keep clinicians involved in complex and clinically sensitive cases",
    ],
    call_to_action=(
        "Let's review the proposed scope and implementation plan "
        "and proceed with the next project steps."
    ),
)


# ============================================================
# TEST
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("PROPOSAL GENERATOR TEST")
    print("=" * 70)

    print("\nValidated scope status:")
    print(validated_scope.overall_scope_status)

    print("\nUnresolved items:")
    print(len(validated_scope.unresolved_items))

    print("\nGenerating proposal...\n")

    proposal = generate_proposal(
        validated_scope=validated_scope,
        pitch=pitch,
    )

    # ========================================================
    # PRINT RESULT
    # ========================================================

    print("=" * 70)
    print("GENERATED PROPOSAL")
    print("=" * 70)

    print(
        json.dumps(
            proposal.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # BASIC STRUCTURAL CHECKS
    # ========================================================

    print("\n" + "=" * 70)
    print("STRUCTURAL CHECKS")
    print("=" * 70)

    assert proposal.title
    assert proposal.proposal_status

    assert proposal.executive_summary
    assert proposal.client_challenge
    assert proposal.proposed_solution

    assert isinstance(proposal.scope, list)
    assert proposal.scope

    assert isinstance(proposal.benefits, list)
    assert proposal.benefits

    assert isinstance(proposal.boundaries, list)
    assert proposal.boundaries

    assert isinstance(proposal.implementation, list)
    assert proposal.implementation

    assert isinstance(proposal.next_steps, list)
    assert proposal.next_steps

    assert isinstance(proposal.assumptions, list)

    assert isinstance(proposal.open_items, list)

    print("PASS: Proposal title exists.")
    print("PASS: Executive summary exists.")
    print("PASS: Client challenge exists.")
    print("PASS: Proposed solution exists.")
    print("PASS: Scope exists.")
    print("PASS: Benefits exist.")
    print("PASS: Boundaries exist.")
    print("PASS: Implementation exists.")
    print("PASS: Next steps exist.")
    print("PASS: Assumptions exist.")
    print("PASS: Open items exists.")

    # ========================================================
    # SCOPE READINESS CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("SCOPE READINESS CHECK")
    print("=" * 70)

    assert (
        validated_scope.overall_scope_status.value
        == "ready_for_proposal"
    )

    assert len(validated_scope.unresolved_items) == 0

    print("PASS: Scope is ready for proposal.")
    print("PASS: Scope contains zero unresolved items.")

    # ========================================================
    # REJECTED REQUIREMENT CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("REJECTED REQUIREMENT CHECK")
    print("=" * 70)

    proposal_text = json.dumps(
        proposal.model_dump(),
        ensure_ascii=False,
    ).lower()

    rejected_phrase = "tell patients what disease they have"

    assert rejected_phrase not in proposal_text, (
        "Rejected requirement leaked into proposal."
    )

    print(
        "PASS: Rejected diagnosis requirement did not "
        "leak into proposal."
    )

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("SAFETY CHECK")
    print("=" * 70)

    boundaries_text = " ".join(
        proposal.boundaries
    ).lower()

    assert "no autonomous diagnosis" in boundaries_text, (
        "Diagnosis safety boundary is missing."
    )

    assert "no autonomous prescribing" in boundaries_text, (
        "Prescribing safety boundary is missing."
    )

    print("PASS: Diagnosis safety boundary preserved.")
    print("PASS: Prescribing safety boundary preserved.")

    # ========================================================
    # UNSUPPORTED GUARANTEE CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("GUARANTEE LANGUAGE CHECK")
    print("=" * 70)

    forbidden_guarantees = [
        "guaranteed",
        "guarantee",
        "100%",
        "zero errors",
    ]

    for forbidden in forbidden_guarantees:
        assert forbidden not in proposal_text, (
            f"Unsupported guarantee language found: {forbidden}"
        )

    print("PASS: No unsupported guarantee language found.")

    # ========================================================
    # NEXT STEPS CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("NEXT STEPS CHECK")
    print("=" * 70)

    next_steps_text = " ".join(
        proposal.next_steps
    ).lower()

    expected_keywords = [
        "review",
        "confirm",
        "approve",
        "finalize",
        "implement",
        "proceed",
    ]

    assert any(
        keyword in next_steps_text
        for keyword in expected_keywords
    ), (
        "Next Steps do not appear to describe "
        "a clear path forward."
    )

    print("PASS: Next Steps provide a path forward.")

    # ========================================================
    # CONTENT CHECK
    # ========================================================

    print("\n" + "=" * 70)
    print("CONTENT CHECK")
    print("=" * 70)

    assert all(
        isinstance(item, str) and item.strip()
        for item in proposal.scope
    )

    assert all(
        isinstance(item, str) and item.strip()
        for item in proposal.benefits
    )

    assert all(
        isinstance(item, str) and item.strip()
        for item in proposal.boundaries
    )

    assert all(
        isinstance(item, str) and item.strip()
        for item in proposal.implementation
    )

    assert all(
        isinstance(item, str) and item.strip()
        for item in proposal.next_steps
    )

    print("PASS: Scope items contain content.")
    print("PASS: Benefits contain content.")
    print("PASS: Boundaries contain content.")
    print("PASS: Implementation items contain content.")
    print("PASS: Next Steps contain content.")

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("🎉 PROPOSAL GENERATOR TEST PASSED SUCCESSFULLY 🎉")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()