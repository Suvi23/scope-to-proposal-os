from src.extractor import extract_requirements
from src.analyzer import analyze_risks
from src.discovery import (
    generate_discovery_questions,
    validate_discovery_question_set,
)


# ============================================================
# TEST CLIENT REQUEST
# ============================================================

client_request = """
We run a multi-specialty clinic. Patients message us for
doctor availability, fees, symptoms and appointment booking.

We want an AI that answers symptoms, tells patients what
disease they have, recommends medicines, books appointments,
sends reminders and follows up after visits.

It should integrate with our hospital system and support
Hindi, Marathi and English.

We want it to replace most front-desk work.
"""


# ============================================================
# STEP 1 — REQUIREMENT EXTRACTION
# ============================================================

print("=" * 70)
print("REQUIREMENT EXTRACTION")
print("=" * 70)

requirement_map = extract_requirements(
    client_request
)

print(
    requirement_map.model_dump_json(
        indent=2
    )
)


# ============================================================
# STEP 2 — RISK ANALYSIS
# ============================================================

print()
print("=" * 70)
print("RISK ANALYSIS")
print("=" * 70)

risks = analyze_risks(
    requirement_map
)

for risk in risks:
    print()
    print(
        f"[{risk.severity.value.upper()}] "
        f"{risk.type.value}"
    )
    print(
        f"Risk ID: {risk.risk_id}"
    )
    print(
        f"Requirement ID: {risk.requirement_id}"
    )
    print(
        f"Issue: {risk.issue}"
    )
    print(
        f"Evidence: {risk.evidence}"
    )
    print(
        f"Impact: {risk.impact}"
    )
    print(
        f"Confirmation required: "
        f"{risk.needs_confirmation}"
    )


# ============================================================
# STEP 3 — DISCOVERY QUESTION GENERATION
# ============================================================

print()
print("=" * 70)
print("DISCOVERY QUESTIONS")
print("=" * 70)

question_set = generate_discovery_questions(
    requirement_map,
    risks
)

questions = question_set.questions


# ============================================================
# STEP 4 — DISCOVERY CONTRACT VALIDATION
# ============================================================

print()
print("=" * 70)
print("DISCOVERY CONTRACT VALIDATION")
print("=" * 70)

validate_discovery_question_set(
    requirement_map=requirement_map,
    risks=risks,
    question_set=question_set,
)

print("PASS: Discovery contract is valid.")
print(
    f"PASS: {len(risks)} risks -> "
    f"{len(questions)} questions"
)


# ============================================================
# STEP 5 — DISPLAY QUESTIONS
# ============================================================

print()
print("=" * 70)
print("GENERATED DISCOVERY QUESTIONS")
print("=" * 70)

for index, question in enumerate(
    questions,
    start=1
):
    matching_risk = next(
        risk
        for risk in risks
        if risk.risk_id == question.risk_id
    )

    print()
    print(
        f"{index}. [{question.question_id}]"
    )

    print(
        f"   Risk: "
        f"{question.risk_id}"
    )

    print(
        f"   Requirement: "
        f"{question.requirement_id}"
    )

    print(
        f"   Severity: "
        f"{matching_risk.severity.value.upper()}"
    )

    print(
        f"   Risk type: "
        f"{matching_risk.type.value}"
    )

    print(
        f"   Requirement text: "
        f"{question.requirement}"
    )

    print(
        f"   Question: "
        f"{question.question}"
    )

    print(
        f"   Why ask: "
        f"{question.why_asking}"
    )


# ============================================================
# STEP 6 — EXPLICIT 1:1 MAPPING CHECK
# ============================================================

print()
print("=" * 70)
print("REQUIREMENT → RISK → QUESTION MAPPING")
print("=" * 70)

for risk in risks:
    matching_questions = [
        question
        for question in questions
        if question.risk_id == risk.risk_id
    ]

    assert len(matching_questions) == 1, (
        f"{risk.risk_id} does not have exactly "
        f"one discovery question."
    )

    question = matching_questions[0]

    assert (
        question.requirement_id
        == risk.requirement_id
    ), (
        f"Mapping error: {question.question_id} "
        f"requirement does not match risk."
    )

    print(
        f"{risk.requirement_id} "
        f"→ {risk.risk_id} "
        f"→ {question.question_id}"
    )


# ============================================================
# STEP 7 — HARD INVARIANTS
# ============================================================

print()
print("=" * 70)
print("HARD INVARIANTS")
print("=" * 70)

# 1. Exact count
assert len(questions) == len(risks)

print(
    f"PASS: len(questions) == len(risks) "
    f"== {len(risks)}"
)


# 2. Every risk has exactly one question
risk_question_counts = {}

for question in questions:
    risk_question_counts[question.risk_id] = (
        risk_question_counts.get(
            question.risk_id,
            0
        ) + 1
    )

assert all(
    count == 1
    for count in risk_question_counts.values()
)

print(
    "PASS: Every risk has exactly one question."
)


# 3. No duplicate question IDs
question_ids = [
    question.question_id
    for question in questions
]

assert len(question_ids) == len(
    set(question_ids)
)

print(
    "PASS: Question IDs are unique."
)


# 4. Every question maps to a valid risk
risk_ids = {
    risk.risk_id
    for risk in risks
}

assert {
    question.risk_id
    for question in questions
} == risk_ids

print(
    "PASS: Every question maps to a valid risk."
)


# 5. Every question maps to the correct requirement
for question in questions:
    risk = next(
        risk
        for risk in risks
        if risk.risk_id == question.risk_id
    )

    assert (
        question.requirement_id
        == risk.requirement_id
    )

print(
    "PASS: Risk → Requirement mappings are correct."
)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("DISCOVERY TEST RESULT")
print("=" * 70)

print(
    f"Requirements: {len(requirement_map.requirements)}"
)

print(
    f"Risks:        {len(risks)}"
)

print(
    f"Questions:    {len(questions)}"
)

print()
print(
    "SUCCESS: Discovery stage satisfies the "
    "one-risk → one-question contract."
)