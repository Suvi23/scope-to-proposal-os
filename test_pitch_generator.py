from pprint import pprint

from src.pitch_generator import generate_pitch
from src.schemas import ValidatedScope, ValidationStatus


def build_test_scope() -> ValidatedScope:
    """Build a fully validated synthetic scope for pitch testing."""

    return ValidatedScope(
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


def main():
    print("\n========== PITCH GENERATOR TEST ==========\n")

    validated_scope = build_test_scope()

    print("Validated scope status:")
    print(validated_scope.overall_scope_status)

    print("\nUnresolved items:")
    print(len(validated_scope.unresolved_items))

    print("\nGenerating pitch...\n")

    result = generate_pitch(validated_scope)

    print("========== GENERATED PITCH ==========\n")
    pprint(result, sort_dicts=False)

    # ---------------------------------------------------------
    # HUMAN-READABLE OUTPUT
    # ---------------------------------------------------------

    print("\n========== HUMAN-READABLE OUTPUT ==========\n")

    print(f"TITLE:\n{result.title}\n")

    print(f"OPENING:\n{result.opening}\n")

    print(f"VALUE PROPOSITION:\n{result.value_proposition}\n")

    print(f"TAILORED PITCH:\n{result.tailored_pitch}\n")

    print("KEY BENEFITS:")

    for index, benefit in enumerate(result.key_benefits, start=1):
        print(f"{index}. {benefit}")

    print(f"\nCALL TO ACTION:\n{result.call_to_action}\n")

    # ---------------------------------------------------------
    # SANITY CHECKS
    # ---------------------------------------------------------

    print("========== SANITY CHECKS ==========\n")

    assert validated_scope.overall_scope_status == "ready_for_proposal"
    assert len(validated_scope.unresolved_items) == 0

    assert result.title
    assert result.opening
    assert result.value_proposition
    assert result.tailored_pitch
    assert result.call_to_action

    assert isinstance(result.key_benefits, list)
    assert len(result.key_benefits) >= 3

    print("PASS: Scope is ready for proposal.")
    print("PASS: Scope contains zero unresolved items.")
    print("PASS: Required pitch fields exist.")
    print("PASS: At least 3 benefits generated.")

    # ---------------------------------------------------------
    # SAFETY CHECKS
    # ---------------------------------------------------------

    print("\n========== SAFETY CHECKS ==========\n")

    pitch_text = (
        f"{result.title} "
        f"{result.opening} "
        f"{result.value_proposition} "
        f"{result.tailored_pitch} "
        f"{' '.join(result.key_benefits)} "
        f"{result.call_to_action}"
    ).lower()

    forbidden_phrases = [
        "diagnose patients",
        "diagnose diseases",
        "tell patients what disease they have",
        "autonomous diagnosis",
        "prescribe medicines",
        "prescribe medication",
        "autonomous prescribing",
        "make treatment decisions",
        "provide treatment decisions",
    ]

    for phrase in forbidden_phrases:
        assert phrase not in pitch_text, (
            f"Unsafe/rejected capability leaked into pitch: {phrase}"
        )

    print("PASS: Rejected diagnosis capability did not leak into pitch.")
    print("PASS: Autonomous prescribing did not leak into pitch.")

    # ---------------------------------------------------------
    # SCOPE TAILORING CHECK
    # ---------------------------------------------------------

    print("\n========== SCOPE TAILORING CHECK ==========\n")

    expected_signals = [
        "appointment",
        "patient",
        "whatsapp",
        "follow",
    ]

    signal_found = any(
        signal in pitch_text
        for signal in expected_signals
    )

    assert signal_found, (
        "Pitch does not appear tailored to the validated scope."
    )

    print("PASS: Pitch contains validated patient/workflow signals.")

    # ---------------------------------------------------------
    # CONTENT CHECK
    # ---------------------------------------------------------

    print("\n========== CONTENT CHECK ==========\n")

    assert all(
        isinstance(benefit, str) and benefit.strip()
        for benefit in result.key_benefits
    )

    print("PASS: All generated benefits contain content.")

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    print("\n==============================================")
    print("🎉 PITCH GENERATOR TEST PASSED SUCCESSFULLY 🎉")
    print("==============================================\n")


if __name__ == "__main__":
    main()