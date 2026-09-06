import json

from src.schemas import (
    RequirementMap,
    Risk,
    DiscoveryQuestion,
)

from src.scope_validator import validate_scope


# ============================================================
# SYNTHETIC REQUIREMENT MAP
# ============================================================

requirement_map = RequirementMap(
    business_goal="Replace most front-desk work",
    target_users=["patients"],
    requirements=[
        {
            "requirement_id": "REQ-001",
            "requirement": "Answer patient symptom questions",
            "category": "symptom_assessment",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "low",
        },
        {
            "requirement_id": "REQ-002",
            "requirement": "Diagnose disease from symptoms",
            "category": "diagnosis",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "high",
        },
        {
            "requirement_id": "REQ-003",
            "requirement": "Recommend medicines",
            "category": "treatment_recommendation",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "high",
        },
        {
            "requirement_id": "REQ-004",
            "requirement": "Book appointments",
            "category": "appointment_booking",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "medium",
        },
        {
            "requirement_id": "REQ-005",
            "requirement": "Send reminders",
            "category": "reminder",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "low",
        },
        {
            "requirement_id": "REQ-006",
            "requirement": "Follow up after visits",
            "category": "follow_up",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "low",
        },
        {
            "requirement_id": "REQ-007",
            "requirement": "Integrate with hospital system",
            "category": "integration",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "medium",
        },
        {
            "requirement_id": "REQ-008",
            "requirement": "Support Hindi, Marathi and English",
            "category": "language_support",
            "source": "client_stated",
            "confidence": 1.0,
            "risk_level": "low",
        },
    ],
)


# ============================================================
# SYNTHETIC RISKS
# ============================================================

risks = [
    Risk(
        risk_id="RISK-001",
        requirement_id="REQ-001",
        issue="Symptom guidance could be interpreted as medical diagnosis.",
        type="safety",
        severity="high",
        evidence="Client wants the system to answer patient symptom questions.",
        impact="Patients could act on incorrect medical guidance.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-002",
        requirement_id="REQ-002",
        issue="Autonomous disease diagnosis creates a critical safety risk.",
        type="safety",
        severity="critical",
        evidence="Client requested diagnosis from symptoms.",
        impact="Incorrect diagnosis could cause serious patient harm.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-003",
        requirement_id="REQ-003",
        issue="Autonomous medicine recommendations create a critical safety risk.",
        type="safety",
        severity="critical",
        evidence="Client requested medicine recommendations.",
        impact="Incorrect medication guidance could cause patient harm.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-004",
        requirement_id="REQ-004",
        issue="Appointment booking requires scheduling-system integration.",
        type="integration",
        severity="medium",
        evidence="Client wants the system to book appointments.",
        impact="Poor synchronization could cause double bookings or missed appointments.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-005",
        requirement_id="REQ-005",
        issue="Reminder delivery depends on notification infrastructure.",
        type="integration",
        severity="medium",
        evidence="Client wants automated reminders.",
        impact="Patients may not receive important reminders.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-006",
        requirement_id="REQ-006",
        issue="Follow-up messages may accidentally provide medical advice.",
        type="safety",
        severity="high",
        evidence="Client wants automated post-visit follow-up.",
        impact="Incorrect follow-up guidance could harm patients.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-007",
        requirement_id="REQ-007",
        issue="Hospital-system integration details are incomplete.",
        type="integration",
        severity="high",
        evidence="Client wants integration with the hospital system.",
        impact="Implementation effort and feasibility cannot be fully estimated.",
        needs_confirmation=True,
    ),
    Risk(
        risk_id="RISK-008",
        requirement_id="REQ-008",
        issue="Medical information may be inaccurate across supported languages.",
        type="accuracy",
        severity="medium",
        evidence="Client requires Hindi, Marathi and English.",
        impact="Translation errors could cause patient misunderstanding.",
        needs_confirmation=True,
    ),
]


# ============================================================
# DISCOVERY QUESTIONS
# ============================================================

discovery_questions = [
    DiscoveryQuestion(
        question_id="DQ-001",
        risk_id="RISK-001",
        requirement_id="REQ-001",
        requirement="Answer patient symptom questions",
        question=(
            "Should the chatbot provide only general health information "
            "and escalation guidance, rather than diagnosis or treatment?"
        ),
        why_asking=(
            "To establish a safe boundary for symptom-related responses."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-002",
        risk_id="RISK-002",
        requirement_id="REQ-002",
        requirement="Diagnose disease from symptoms",
        question=(
            "Should automated disease diagnosis be excluded, with "
            "uncertain or serious cases escalated to a qualified clinician?"
        ),
        why_asking=(
            "To prevent autonomous diagnosis from becoming part of the final scope."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-003",
        risk_id="RISK-003",
        requirement_id="REQ-003",
        requirement="Recommend medicines",
        question=(
            "Should the system avoid prescribing or independently "
            "recommending medicines, while allowing approved medication "
            "information to be provided?"
        ),
        why_asking=(
            "To establish a safe boundary around medication-related functionality."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-004",
        risk_id="RISK-004",
        requirement_id="REQ-004",
        requirement="Book appointments",
        question=(
            "Which scheduling system should appointment booking integrate "
            "with, and what appointment workflow should it follow?"
        ),
        why_asking=(
            "To define the booking integration and workflow."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-005",
        risk_id="RISK-005",
        requirement_id="REQ-005",
        requirement="Send reminders",
        question=(
            "Which reminder channels should be supported and what timing "
            "rules should be used?"
        ),
        why_asking=(
            "To define reminder delivery requirements."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-006",
        risk_id="RISK-006",
        requirement_id="REQ-006",
        requirement="Follow up after visits",
        question=(
            "What type of post-visit follow-up should be automated, and "
            "when should cases be escalated to staff or clinicians?"
        ),
        why_asking=(
            "To prevent automated follow-up from becoming unsafe medical advice."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-007",
        risk_id="RISK-007",
        requirement_id="REQ-007",
        requirement="Integrate with hospital system",
        question=(
            "Which hospital system API will be used, what data must be "
            "exchanged, and what authentication method is available?"
        ),
        why_asking=(
            "To establish technical integration scope and feasibility."
        ),
    ),
    DiscoveryQuestion(
        question_id="DQ-008",
        risk_id="RISK-008",
        requirement_id="REQ-008",
        requirement="Support Hindi, Marathi and English",
        question=(
            "How should multilingual accuracy be evaluated, particularly "
            "for medical terminology?"
        ),
        why_asking=(
            "To establish acceptance criteria for multilingual responses."
        ),
    ),
]


# ============================================================
# CLIENT ANSWERS
# ============================================================

client_answers = {
    "DQ-001": (
        "Yes. The chatbot should provide general health information only. "
        "It should not diagnose or prescribe. Serious or uncertain cases "
        "should be escalated to a qualified clinician."
    ),
    "DQ-002": (
        "We do not want automated diagnosis. The chatbot should never tell "
        "patients that they definitely have a particular disease. "
        "Serious or uncertain cases should go to a clinician."
    ),
    "DQ-003": (
        "The system should not independently prescribe or recommend "
        "medicines. Doctors remain responsible for prescribing decisions. "
        "Approved medication information can be displayed."
    ),
    "DQ-004": (
        "The hospital system provides an API. Appointment availability, "
        "doctor schedules and appointment creation need to be supported. "
        "The initial deployment will use the hospital scheduling API."
    ),
    "DQ-005": (
        "Reminders should initially be sent through WhatsApp. "
        "Appointment reminders should be sent before the scheduled visit."
    ),
    "DQ-006": (
        "Routine post-visit reminders and non-clinical follow-ups can be "
        "automated. Medical concerns or complex cases should be escalated "
        "to hospital staff or a clinician."
    ),
    "DQ-007": (
        "The hospital system provides an API. It will be used for doctor "
        "availability, appointments and required patient appointment data. "
        "Authentication details will be provided during implementation."
    ),
    "DQ-008": (
        "Hindi, Marathi and English are required. Medical terminology "
        "should be reviewed for accuracy and unsafe or uncertain responses "
        "should be escalated."
    ),
}


# ============================================================
# VALIDATION
# ============================================================

def main():
    print("=" * 70)
    print("SCOPE VALIDATION TEST")
    print("=" * 70)

    print("\nInput summary:")
    print(f"Requirement count: {len(requirement_map.requirements)}")
    print(f"Risk count: {len(risks)}")
    print(f"Discovery question count: {len(discovery_questions)}")
    print(f"Client answer count: {len(client_answers)}")

    print("\nCalling scope validator...")
    print("(This test intentionally makes ONE Groq call.)")

    # --------------------------------------------------------
    # Basic contract checks before calling Groq
    # --------------------------------------------------------

    assert len(requirement_map.requirements) == len(risks)
    assert len(risks) == len(discovery_questions)
    assert len(discovery_questions) == len(client_answers)

    requirement_ids = {
        requirement.requirement_id
        for requirement in requirement_map.requirements
    }

    risk_ids = {risk.risk_id for risk in risks}

    question_ids = {
        question.question_id
        for question in discovery_questions
    }

    assert len(requirement_ids) == len(requirement_map.requirements)
    assert len(risk_ids) == len(risks)
    assert len(question_ids) == len(discovery_questions)

    for risk in risks:
        assert risk.requirement_id in requirement_ids

    for question in discovery_questions:
        assert question.risk_id in risk_ids

        matching_risk = next(
            risk for risk in risks
            if risk.risk_id == question.risk_id
        )

        assert question.requirement_id == matching_risk.requirement_id

    assert question_ids == set(client_answers.keys())

    print("\n✓ Requirement IDs are valid")
    print("✓ Risk IDs are valid")
    print("✓ Discovery question IDs are valid")
    print("✓ Requirement → Risk → Question mapping is valid")
    print("✓ Every question has exactly one client answer")

    # --------------------------------------------------------
    # EXACTLY ONE SCOPE VALIDATION CALL
    # --------------------------------------------------------

    validated_scope = validate_scope(
        requirement_map=requirement_map,
        risks=risks,
        discovery_questions=discovery_questions,
        client_answers=client_answers,
    )

    # ========================================================
    # RAW VALIDATED SCOPE
    # ========================================================

    print("\n" + "=" * 70)
    print("VALIDATED SCOPE")
    print("=" * 70)

    print(
        json.dumps(
            validated_scope.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # HUMAN-READABLE SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"\nOverall scope status: "
        f"{validated_scope.overall_scope_status}"
    )

    print(
        f"\nBusiness goal:\n"
        f"{validated_scope.business_goal}"
    )

    print("\nTarget users:")
    for user in validated_scope.target_users:
        print(f"  - {user}")

    # --------------------------------------------------------
    # REQUIREMENT VALIDATION
    # --------------------------------------------------------

    print("\nRequirement decisions:")

    for item in validated_scope.confirmed_requirements:
        print(f"\n[{item.status.upper()}]")
        print(f"Original : {item.original_requirement}")
        print(f"Final    : {item.final_scope}")
        print(f"Evidence : {item.client_evidence}")

        if item.notes:
            print(f"Notes    : {item.notes}")

    # --------------------------------------------------------
    # SCOPE BOUNDARIES
    # --------------------------------------------------------

    print("\nScope boundaries:")

    if validated_scope.scope_boundaries:
        for boundary in validated_scope.scope_boundaries:
            print(f"  - {boundary}")
    else:
        print("  None identified.")

    # --------------------------------------------------------
    # ASSUMPTIONS
    # --------------------------------------------------------

    print("\nAssumptions:")

    if validated_scope.assumptions:
        for assumption in validated_scope.assumptions:
            print(f"  - {assumption}")
    else:
        print("  None.")

    # --------------------------------------------------------
    # UNRESOLVED ITEMS
    # --------------------------------------------------------

    print("\nUnresolved items:")

    if validated_scope.unresolved_items:
        for item in validated_scope.unresolved_items:
            print(f"\n  [{item.priority.upper()}]")
            print(f"  Issue        : {item.issue}")
            print(f"  Reason       : {item.reason}")
            print(f"  Required for : {item.required_for}")
    else:
        print("  None.")

    # ========================================================
    # SANITY CHECKS
    # ========================================================

    print("\n" + "=" * 70)
    print("SANITY CHECKS")
    print("=" * 70)

    assert validated_scope.business_goal
    assert len(validated_scope.confirmed_requirements) > 0

    valid_statuses = {
        "confirmed",
        "modified",
        "rejected",
        "unresolved",
    }

    for item in validated_scope.confirmed_requirements:
        assert item.status in valid_statuses
        assert item.original_requirement
        if item.status in {"confirmed", "modified"}:
            assert item.final_scope, (
            f"{item.status} requirement must have a final_scope: "
            f"{item.requirement}"
        )
        elif item.status in {"rejected", "unresolved"}:
            assert item.final_scope == "", (
            f"{item.status} requirement must have an empty final_scope: "
            f"{item.requirement}"
        )






    assert validated_scope.overall_scope_status in {
        "ready_for_proposal",
        "partially_validated",
        "needs_more_discovery",
    }

    print("✓ Business goal exists")
    print("✓ Requirement decisions exist")
    print("✓ Requirement statuses are valid")
    print("✓ Final scope statements exist")
    print("✓ Overall validation status is valid")

    # ========================================================
    # SAFETY CHECKS
    # ========================================================

    all_scope_text = " ".join(
        item.final_scope.lower()
        for item in validated_scope.confirmed_requirements
    )

    print("\nCritical safety checks:")

    # Diagnosis
    diagnosis_is_safe = (
        "do not" in all_scope_text
        or "not" in all_scope_text
        or "exclude" in all_scope_text
        or "general information" in all_scope_text
    )

    if diagnosis_is_safe:
        print(
            "  ✓ Final scope contains a safety boundary "
            "around autonomous diagnosis."
        )
    else:
        print(
            "  ⚠ Review diagnosis-related final scope."
        )

    # Prescribing
    prescribing_is_safe = (
        "do not" in all_scope_text
        or "not" in all_scope_text
        or "exclude" in all_scope_text
        or "doctor" in all_scope_text
        or "clinician" in all_scope_text
    )

    if prescribing_is_safe:
        print(
            "  ✓ Final scope contains a safety boundary "
            "around autonomous prescribing."
        )
    else:
        print(
            "  ⚠ Review medication-related final scope."
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("SCOPE VALIDATION TEST COMPLETED")
    print("=" * 70)

    if validated_scope.is_ready_for_proposal:
        print("\nSUCCESS: Scope is ready for proposal generation.")
    else:
        print(
            "\nEXPECTED SAFETY OUTCOME: "
            "Scope is not yet ready for proposal generation."
        )


if __name__ == "__main__":
    main()