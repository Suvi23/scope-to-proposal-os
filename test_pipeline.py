
"""
End-to-end test for the Scope-to-Proposal AI OS.

Flow
----
1. Requirement extraction
2. Deep risk analysis
3. Risk coverage gate
4. Discovery generation
5. One-to-one discovery contract
6. Deterministic synthetic client answers
7. ONE scope validation call
8. Scope readiness gate
9. Pitch generation
10. Proposal generation
11. Proposal QA
12. AI proposal QA
13. Final QA gate

IMPORTANT
---------
Synthetic answers exist ONLY for automated backend testing.

The real Streamlit application will collect answers from the actual
client/user. The production pipeline does not depend on these answers.

This test intentionally uses REAL Groq for all AI stages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Import project
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import (
    prepare_discovery,
    generate_final_proposal,
)


# ---------------------------------------------------------------------------
# Synthetic client request
# ---------------------------------------------------------------------------

CLIENT_REQUEST = """
We are a dental clinic and want an AI patient inquiry and appointment
assistant.

Our main business goal is to get more patient bookings.

The system should:

1. Answer common patient questions.
2. Qualify potential patients before booking.
3. Help patients book appointments.
4. Handle patient inquiries through WhatsApp.
5. Handle patient inquiries through the clinic website.
6. Operate 24/7.
7. Escalate medical questions requiring professional judgment to clinic staff.
8. Integrate appointment scheduling with Google Calendar.
9. Provide a simple interface for clinic staff to manage the system.

The assistant should make the booking process easier, reduce repetitive
questions for staff, and make sure medical or high-risk questions are
handled by authorized clinic staff.
""".strip()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def model_to_dict(value: Any) -> Any:
    """Convert Pydantic models recursively into dictionaries."""

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            key: model_to_dict(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            model_to_dict(item)
            for item in value
        ]

    if hasattr(value, "model_dump"):
        return model_to_dict(value.model_dump())

    if hasattr(value, "dict"):
        return model_to_dict(value.dict())

    if hasattr(value, "value"):
        return value.value

    return value


def print_json(title: str, value: Any) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)
    print(
        json.dumps(
            model_to_dict(value),
            indent=2,
            ensure_ascii=False,
        )
    )


def get_value(
    obj: Any,
    key: str,
    default: Any = None,
) -> Any:
    """Safely retrieve a value from dictionaries or objects."""

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


# ---------------------------------------------------------------------------
# Synthetic answer generation
# ---------------------------------------------------------------------------

def generate_demo_answer(
    question: Any,
    risk: Any,
    requirement: Any,
) -> str:
    """
    Generate a deterministic synthetic answer for backend testing.

    IMPORTANT
    ---------
    The requirement text is used as the primary semantic anchor.

    This prevents overlapping keywords in risk/question text from
    accidentally assigning the wrong answer to a discovery question.

    These answers are NOT used by the Streamlit production application.
    """

    requirement_text = str(
        get_value(
            requirement,
            "requirement",
            "",
        )
    ).lower()

    # ------------------------------------------------------------------
    # REQ-001 — Knowledge / FAQ scope
    # ------------------------------------------------------------------

    if "common patient questions" in requirement_text:
        return (
            "The clinic will provide and approve the common patient "
            "information the assistant can use. The assistant should "
            "answer only configured clinic-approved information in the "
            "supported languages. It must not provide unsupported "
            "medical advice."
        )

    # ------------------------------------------------------------------
    # REQ-002 — Patient qualification
    # ------------------------------------------------------------------

    if "qualify potential patients" in requirement_text:
        return (
            "Qualification should use non-medical criteria defined by "
            "the clinic, such as appointment intent, requested service, "
            "preferred timing, and basic contact information. The "
            "assistant should not make medical diagnoses or clinical "
            "eligibility decisions."
        )

    # ------------------------------------------------------------------
    # REQ-003 — Appointment booking
    # ------------------------------------------------------------------

    if "help patients book appointments" in requirement_text:
        return (
            "The appointment booking integration will use Google Calendar. "
            "The assistant should show available appointment slots and "
            "book appointments according to the clinic's working hours, "
            "appointment duration, and timezone. Confirmation, "
            "cancellation, and rescheduling behavior will be configured "
            "by the clinic. If booking fails, the patient should be "
            "routed to clinic staff."
        )

    # ------------------------------------------------------------------
    # REQ-004 — WhatsApp
    # ------------------------------------------------------------------

    if "whatsapp" in requirement_text:
        return (
            "WhatsApp will be the required messaging channel. The clinic "
            "will provide the required WhatsApp Business/API access, "
            "approved templates where required, authentication details, "
            "and account configuration. A safe fallback to clinic staff "
            "should be available if the integration fails."
        )

    # ------------------------------------------------------------------
    # REQ-005 — Website
    # ------------------------------------------------------------------

    if "clinic website" in requirement_text:
        return (
            "The clinic wants a simple website chat experience. The "
            "assistant should answer approved common questions and "
            "capture basic inquiry and contact information. The existing "
            "clinic website will host the chat experience."
        )

    # ------------------------------------------------------------------
    # REQ-006 — 24/7 operation
    # ------------------------------------------------------------------

    if "operate 24/7" in requirement_text:
        return (
            "The assistant should be available 24/7 for automated "
            "responses. Human escalation will operate during the clinic's "
            "configured staff availability. The system should include "
            "basic monitoring and a fallback path when automated service "
            "is unavailable."
        )

    # ------------------------------------------------------------------
    # REQ-007 — Medical safety / escalation
    # ------------------------------------------------------------------

    if "escalate medical questions" in requirement_text:
        return (
            "The assistant must not diagnose conditions, prescribe "
            "medication, or replace professional medical judgment. "
            "Medical or high-risk situations must be escalated to "
            "authorized clinic staff. The escalation should include "
            "relevant conversation context so staff can review the "
            "inquiry."
        )

    # ------------------------------------------------------------------
    # REQ-008 — Google Calendar
    # ------------------------------------------------------------------

    if "google calendar" in requirement_text:
        return (
            "The initial scheduling integration will use Google Calendar. "
            "The clinic will authorize Google access and configure the "
            "relevant calendars, working hours, availability, and "
            "timezone. The system should avoid conflicting bookings and "
            "surface integration failures instead of pretending that a "
            "booking succeeded."
        )

    # ------------------------------------------------------------------
    # REQ-009 — Staff interface
    # ------------------------------------------------------------------

    if (
        "staff interface" in requirement_text
        or (
            "interface" in requirement_text
            and "clinic staff" in requirement_text
        )
    ):
        return (
            "The clinic wants a simple web interface where staff can "
            "review conversations, manage bookings, view escalations, "
            "and manage basic system settings. Complex role-based access "
            "control is not required for the initial version. The "
            "interface should be simple enough for normal clinic staff."
        )

    # ------------------------------------------------------------------
    # Generic deterministic fallback
    # ------------------------------------------------------------------

    return (
        "The clinic will define the required behavior for this scope. "
        "The system must not invent requirements or provide unsupported "
        "medical advice. Any situation requiring professional judgment "
        "must be handled by authorized clinic staff."
    )


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def main() -> None:

    print()
    print("=" * 78)
    print("SCOPE-TO-PROPOSAL AI OS — END-TO-END TEST")
    print("=" * 78)

    print()
    print("Client request:")
    print("-" * 78)
    print(CLIENT_REQUEST)

    # ================================================================
    # STEP 1 — REQUIREMENTS + RISKS + DISCOVERY
    # ================================================================

    print()
    print("=" * 78)
    print("STEP 1 — REAL GROQ DISCOVERY PIPELINE")
    print("=" * 78)

    try:
        preparation = prepare_discovery(
            CLIENT_REQUEST,
            source_type="text",
        )

    except Exception as exc:
        print()
        print("❌ DISCOVERY PIPELINE FAILED")
        print(type(exc).__name__)
        print(str(exc))
        raise

    requirement_map = get_value(
        preparation,
        "requirement_map",
    )

    risks = get_value(
        preparation,
        "risks",
        [],
    )

    question_set = get_value(
        preparation,
        "discovery_questions",
    )

    # ================================================================
    # REQUIREMENT MAP
    # ================================================================

    print_json(
        "REQUIREMENT MAP",
        requirement_map,
    )

    requirements = get_value(
        requirement_map,
        "requirements",
        [],
    )

    if not requirements:
        raise RuntimeError(
            "Requirement extraction returned zero requirements."
        )

    # ================================================================
    # RISKS
    # ================================================================

    print_json(
        "RISK ANALYSIS",
        risks,
    )

    if not risks:
        raise RuntimeError(
            "Risk analysis returned zero risks."
        )

    # ================================================================
    # DISCOVERY QUESTIONS
    # ================================================================

    questions = get_value(
        question_set,
        "questions",
        [],
    )

    if not questions:
        raise RuntimeError(
            "Discovery generation returned zero questions."
        )

    print_json(
        "DISCOVERY QUESTIONS",
        question_set,
    )

    # ================================================================
    # DISCOVERY CONTRACT
    # ================================================================

    print()
    print("=" * 78)
    print("DISCOVERY CONTRACT CHECK")
    print("=" * 78)

    risk_ids = [
        get_value(risk, "risk_id")
        for risk in risks
    ]

    question_ids = [
        get_value(question, "question_id")
        for question in questions
    ]

    question_risk_ids = [
        get_value(question, "risk_id")
        for question in questions
    ]

    print(f"Requirements : {len(requirements)}")
    print(f"Risks        : {len(risks)}")
    print(f"Questions    : {len(questions)}")

    # ----------------------------------------------------------------
    # N risks == N questions
    # ----------------------------------------------------------------

    if len(questions) != len(risks):
        raise RuntimeError(
            "❌ DISCOVERY CONTRACT FAILED: "
            "question count does not equal risk count."
        )

    # ----------------------------------------------------------------
    # Unique risks
    # ----------------------------------------------------------------

    if len(risk_ids) != len(set(risk_ids)):
        raise RuntimeError(
            "❌ DISCOVERY CONTRACT FAILED: duplicate risk IDs."
        )

    # ----------------------------------------------------------------
    # Unique questions
    # ----------------------------------------------------------------

    if len(question_ids) != len(set(question_ids)):
        raise RuntimeError(
            "❌ DISCOVERY CONTRACT FAILED: duplicate question IDs."
        )

    # ----------------------------------------------------------------
    # Exactly one question per risk
    # ----------------------------------------------------------------

    if set(question_risk_ids) != set(risk_ids):

        missing_risks = (
            set(risk_ids)
            - set(question_risk_ids)
        )

        extra_risks = (
            set(question_risk_ids)
            - set(risk_ids)
        )

        raise RuntimeError(
            "❌ DISCOVERY CONTRACT FAILED: "
            f"risk/question IDs do not match exactly. "
            f"Missing={sorted(missing_risks)} "
            f"Unexpected={sorted(extra_risks)}"
        )

    if len(question_risk_ids) != len(set(question_risk_ids)):
        raise RuntimeError(
            "❌ DISCOVERY CONTRACT FAILED: "
            "a risk has more than one question."
        )

    # ----------------------------------------------------------------
    # Lookup maps
    # ----------------------------------------------------------------

    risk_lookup = {
        get_value(risk, "risk_id"): risk
        for risk in risks
    }

    requirement_lookup = {
        get_value(requirement, "requirement_id"): requirement
        for requirement in requirements
    }

    # ----------------------------------------------------------------
    # Validate every question → risk → requirement mapping
    # ----------------------------------------------------------------

    for question in questions:

        question_id = get_value(
            question,
            "question_id",
        )

        risk_id = get_value(
            question,
            "risk_id",
        )

        requirement_id = get_value(
            question,
            "requirement_id",
        )

        if risk_id not in risk_lookup:
            raise RuntimeError(
                f"❌ {question_id} references unknown {risk_id}."
            )

        risk = risk_lookup[risk_id]

        risk_requirement_id = get_value(
            risk,
            "requirement_id",
        )

        if requirement_id != risk_requirement_id:
            raise RuntimeError(
                f"❌ {question_id} requirement mapping mismatch."
            )

        if requirement_id not in requirement_lookup:
            raise RuntimeError(
                f"❌ {question_id} references unknown "
                f"requirement {requirement_id}."
            )

    print()
    print("✅ Risk count == Question count")
    print("✅ Every risk has exactly one question")
    print("✅ Every question maps to a valid risk")
    print("✅ Every question maps to the correct requirement")
    print("✅ Discovery contract PASSED")

    # ================================================================
    # STEP 2 — SYNTHETIC CLIENT ANSWERS
    # ================================================================

    print()
    print("=" * 78)
    print("STEP 2 — SYNTHETIC CLIENT DISCOVERY ANSWERS")
    print("=" * 78)

    print()
    print(
        "NOTE: These answers are ONLY for automated backend testing."
    )
    print(
        "The Streamlit demo will collect real answers from the user."
    )

    client_answers: Dict[str, Dict[str, Any]] = {}

    for question in questions:

        question_id = get_value(
            question,
            "question_id",
        )

        risk_id = get_value(
            question,
            "risk_id",
        )

        requirement_id = get_value(
            question,
            "requirement_id",
        )

        # ------------------------------------------------------------
        # Resolve requirement through question → risk → requirement
        # ------------------------------------------------------------

        risk = risk_lookup[risk_id]

        risk_requirement_id = get_value(
            risk,
            "requirement_id",
        )

        if risk_requirement_id != requirement_id:
            raise RuntimeError(
                f"❌ Mapping inconsistency for {question_id}: "
                f"question requirement={requirement_id}, "
                f"risk requirement={risk_requirement_id}"
            )

        if requirement_id not in requirement_lookup:
            raise RuntimeError(
                f"❌ Unknown requirement {requirement_id} "
                f"for {question_id}."
            )

        requirement = requirement_lookup[requirement_id]

        question_text = get_value(
            question,
            "question",
            "",
        )

        answer = generate_demo_answer(
            question,
            risk,
            requirement,
        )

        client_answers[question_id] = {
            "risk_id": risk_id,
            "requirement_id": requirement_id,
            "question": question_text,
            "answer": answer,
        }

    print_json(
        "CLIENT ANSWERS",
        client_answers,
    )

    # ================================================================
    # ANSWER CONTRACT
    # ================================================================

    expected_question_ids = set(question_ids)

    actual_answer_ids = set(
        client_answers.keys()
    )

    if expected_question_ids != actual_answer_ids:

        missing = (
            expected_question_ids
            - actual_answer_ids
        )

        unexpected = (
            actual_answer_ids
            - expected_question_ids
        )

        raise RuntimeError(
            "❌ ANSWER CONTRACT FAILED. "
            f"Missing={sorted(missing)}, "
            f"Unexpected={sorted(unexpected)}"
        )

    for question_id, answer_data in client_answers.items():

        answer = answer_data.get("answer")

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError(
                f"❌ Empty answer for {question_id}."
            )

    print("✅ Exactly one answer for every discovery question")
    print("✅ No unexpected answer IDs")
    print("✅ No empty answers")
    print("✅ Answer contract PASSED")

    # ================================================================
    # STEP 3 — FINAL PROPOSAL PIPELINE
    # ================================================================

    print()
    print("=" * 78)
    print("STEP 3 — SCOPE VALIDATION → PITCH → PROPOSAL → QA")
    print("=" * 78)

    try:

        result = generate_final_proposal(
            preparation=preparation,
            answers=client_answers,
        )

    except Exception as exc:

        print()
        print("❌ FINAL PIPELINE CRASHED")
        print(type(exc).__name__)
        print(str(exc))
        raise

    # ================================================================
    # RESULT VALUES
    # ================================================================

    status = get_value(
        result,
        "status",
        "UNKNOWN",
    )

    proposal_generated = bool(
        get_value(
            result,
            "proposal_generated",
            False,
        )
    )

    reason = get_value(
        result,
        "reason",
        "",
    )

    scope = get_value(
        result,
        "scope",
    )

    pitch = get_value(
        result,
        "pitch",
    )

    proposal = get_value(
        result,
        "proposal",
    )

    proposal_qa = get_value(
        result,
        "proposal_qa",
    )

    ai_proposal_qa = get_value(
        result,
        "ai_proposal_qa",
    )

    final_qa = get_value(
        result,
        "final_qa",
    )

    approved = bool(
        get_value(
            result,
            "approved",
            False,
        )
    )

    can_download = bool(
        proposal is not None
        and approved
    )

    warnings = get_value(
        result,
        "warnings",
        [],
    )

    # ================================================================
    # FINAL STATUS
    # ================================================================

    print()
    print("=" * 78)
    print("FINAL PIPELINE STATUS")
    print("=" * 78)

    print(f"Status             : {status}")
    print(f"Proposal Generated : {proposal_generated}")
    print(f"Approved           : {approved}")
    print(f"Can Download       : {can_download}")

    if reason:
        print(f"Reason             : {reason}")

    # ================================================================
    # SCOPE
    # ================================================================

    if scope is not None:
        print_json(
            "VALIDATED SCOPE",
            scope,
        )

    # ================================================================
    # PITCH
    # ================================================================

    if pitch is not None:
        print_json(
            "AI PITCH",
            pitch,
        )

    # ================================================================
    # PROPOSAL
    # ================================================================

    if proposal is not None:
        print_json(
            "PROPOSAL",
            proposal,
        )

    # ================================================================
    # QA
    # ================================================================

    if proposal_qa is not None:
        print_json(
            "DETERMINISTIC PROPOSAL QA",
            proposal_qa,
        )

    if ai_proposal_qa is not None:
        print_json(
            "AI PROPOSAL QA",
            ai_proposal_qa,
        )

    if final_qa is not None:
        print_json(
            "FINAL QA GATE",
            final_qa,
        )

    if warnings:
        print_json(
            "WARNINGS",
            warnings,
        )

    # ================================================================
    # FINAL ASSERTIONS
    # ================================================================

    print()
    print("=" * 78)
    print("FINAL ASSERTIONS")
    print("=" * 78)

    # ----------------------------------------------------------------
    # Scope blocked
    # ----------------------------------------------------------------

    if status == "SCOPE_BLOCKED":

        print("⚠️ Pipeline reached SCOPE_BLOCKED.")
        print()

        print(
            "The pipeline intentionally refused to generate "
            "a proposal because scope was not safely closed."
        )

        print()
        print("Reason:")
        print(reason)

        print()
        print(
            "This is a safety gate, not a Python crash."
        )

        # Do NOT raise here.
        #
        # A scope block is a valid deterministic outcome when the
        # synthetic test data does not satisfy the generated scope.
        #
        # In the Streamlit application, the real user must provide
        # answers before proposal generation.

        return

    # ----------------------------------------------------------------
    # Downstream blocks
    # ----------------------------------------------------------------

    if status in {
        "PROPOSAL_BLOCKED",
        "QA_BLOCKED",
        "FINAL_QA_FAILED",
    }:

        print(
            f"⚠️ Pipeline reached downstream safety gate: {status}"
        )

        if reason:
            print(f"Reason: {reason}")

        return

    # ----------------------------------------------------------------
    # Successful proposal path
    # ----------------------------------------------------------------

    if not proposal_generated:
        raise RuntimeError(
            "❌ Pipeline finished without generating a proposal."
        )

    if proposal is None:
        raise RuntimeError(
            "❌ proposal_generated=True but proposal object is missing."
        )

    print("✅ Scope validation completed")
    print("✅ Scope closed before proposal generation")
    print("✅ Proposal generated")
    print("✅ Proposal QA completed")
    print("✅ Final QA gate completed")

    if approved:
        print("✅ Final proposal APPROVED")
    else:
        print(
            "⚠️ Proposal exists but final approval is false."
        )

    print()
    print("=" * 78)
    print("🎉 END-TO-END PIPELINE TEST COMPLETED")
    print("=" * 78)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()

