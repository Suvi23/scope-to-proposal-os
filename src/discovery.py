"""
src/discovery.py

Discovery Question Generation
-----------------------------

Pipeline contract:

    Requirement
        ↓
    Risk
        ↓
    Exactly ONE Discovery Question
        ↓
    Client Answer
        ↓
    Scope Validation

Hard invariants:
    1. len(discovery_questions) == len(risks)
    2. Every risk gets exactly one question
    3. Every question maps to exactly one risk
    4. Every question maps to exactly one requirement
    5. No follow-up questions
    6. No combining multiple risks into one question
    7. Groq generates wording; Python enforces structure
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import ValidationError

from .schemas import (
    DiscoveryQuestion,
    DiscoveryQuestionSet,
    RequirementMap,
    Risk,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

MAX_RETRIES = 2


# ============================================================
# DEFENSIVE LOOKUP HELPERS (Enum & Property Resilient)
# ============================================================

def _safe_enum_value(val: Any) -> str:
    """
    Safely extract the string representation from an Enum or plain string.
    Prevents 'str' object has no attribute 'value' crashes.
    """
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value).strip()
    return str(val).strip()


def _safe_get_attr(obj: Any, attr_name: str, fallback_name: Optional[str] = None) -> Any:
    """
    Safely retrieve property/key values from Pydantic models, classes, or dicts.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        val = obj.get(attr_name)
        if val is None and fallback_name:
            val = obj.get(fallback_name)
        return val
    
    val = getattr(obj, attr_name, None)
    if val is None and fallback_name:
        val = getattr(obj, fallback_name, None)
    return val


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the Discovery Question Generator inside a consultancy
Scope-to-Proposal AI system.

Your job is NOT to discover new risks.

The Risk Analyzer has already identified the risks.

Your ONLY job is to convert each supplied risk into exactly ONE
clear client-facing discovery question.

STRICT RULES:

1. EXACTLY ONE QUESTION PER RISK.
2. NEVER combine two risks into one question.
3. NEVER create extra questions.
4. NEVER omit a supplied risk.
5. NEVER create a new risk.
6. NEVER create a follow-up question.
7. NEVER ask a second question for the same risk.
8. Each question must address the specific risk supplied.
9. The question must be answerable by the client during discovery.
10. Do not invent facts about the client.
11. Do not assume missing scope.
12. Do not turn a risk into a generic sales question.
13. Do not ask about unrelated requirements.
14. Preserve the supplied requirement_id and risk_id exactly.
15. The Python application will enforce all structural constraints.

QUESTION QUALITY:

A good question should:

- directly resolve the identified ambiguity/risk
- ask for the missing business rule, constraint, behavior,
  integration, acceptance criterion, boundary, or decision
- be concise enough for a live discovery call
- be specific enough that the client's answer can become
  implementable scope
- avoid technical jargon unless the risk itself is technical
- avoid asking multiple independent questions
- avoid yes/no questions when a specific business rule is needed

IMPORTANT:

The client answer will later be used by a Scope Validator.

Therefore, questions must collect information that allows the
Scope Validator to determine whether the original requirement
should be:

    confirmed
    modified
    rejected
    unresolved

For healthcare-related requirements, explicitly clarify safety
boundaries, human escalation, clinical vs non-clinical behavior,
and what the system must NOT do when relevant.

For qualification/eligibility requirements, clarify the actual
criteria used to determine qualification and the expected action
when a person does not qualify.

Return ONLY valid JSON.

Required output:

{
  "questions": [
    {
      "risk_id": "RISK-001",
      "question": "...",
      "why_asking": "..."
    }
  ]
}

Do not return markdown.
Do not return commentary.
"""


# ============================================================
# GROQ CLIENT
# ============================================================

def _get_client() -> Groq:
    """
    Create the real Groq client.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "Discovery generation requires the real Groq API."
        )

    return Groq(api_key=api_key)


# ============================================================
# JSON HELPERS
# ============================================================

def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from a Groq response.
    """
    if not text:
        raise ValueError("Groq returned an empty response.")

    cleaned = text.strip()

    # Remove markdown fences.
    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.strip()

    # Direct parse first.
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try extracting the first JSON object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Could not find a valid JSON object in Groq response."
        )

    candidate = cleaned[start : end + 1]

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON returned by Groq: {exc}"
        ) from exc


# ============================================================
# PROMPT BUILDING
# ============================================================

def _build_user_prompt(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> str:
    """
    Build the discovery-generation prompt.
    """
    requirements_payload = []

    for requirement in requirement_map.requirements:
        requirements_payload.append(
            {
                "requirement_id": _safe_enum_value(_safe_get_attr(requirement, "requirement_id", "req_id")),
                "requirement": _safe_enum_value(_safe_get_attr(requirement, "requirement", "text")),
                "category": _safe_enum_value(_safe_get_attr(requirement, "category")),
                "source": _safe_enum_value(_safe_get_attr(requirement, "source")),
                "confidence": float(_safe_get_attr(requirement, "confidence") or 1.0),
                "risk_level": _safe_enum_value(_safe_get_attr(requirement, "risk_level", "priority")),
            }
        )

    risks_payload = []

    for risk in risks:
        risks_payload.append(
            {
                "risk_id": _safe_enum_value(_safe_get_attr(risk, "risk_id")),
                "requirement_id": _safe_enum_value(_safe_get_attr(risk, "requirement_id", "req_id")),
                "issue": _safe_enum_value(_safe_get_attr(risk, "issue", "description")),
                "type": _safe_enum_value(_safe_get_attr(risk, "type")),
                "severity": _safe_enum_value(_safe_get_attr(risk, "severity")),
                "evidence": _safe_enum_value(_safe_get_attr(risk, "evidence")),
                "impact": _safe_enum_value(_safe_get_attr(risk, "impact")),
                "needs_confirmation": bool(_safe_get_attr(risk, "needs_confirmation")),
            }
        )

    payload = {
        "requirements": requirements_payload,
        "risks": risks_payload,
        "instruction": (
            "Generate exactly one discovery question for every "
            "supplied risk. Do not create, remove, merge, or split risks."
        ),
    }

    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# DETERMINISTIC FALLBACK QUESTIONS
# ============================================================

def _fallback_question(risk: Risk) -> str:
    """
    Deterministic fallback when Groq output is incomplete.
    """
    issue = _safe_enum_value(_safe_get_attr(risk, "issue", "description")).strip()
    issue_lower = issue.lower()

    if any(term in issue_lower for term in ("qualif", "eligib", "screening criteria", "qualification criteria")):
        return (
            "What specific criteria should the system use to "
            "determine whether a potential patient is qualified, "
            "and what should happen when the patient does not "
            "meet those criteria?"
        )

    if any(term in issue_lower for term in ("appointment", "booking", "book")):
        return (
            "What appointment types, availability rules, and "
            "booking constraints should the system follow, and "
            "what should happen when the requested slot is unavailable?"
        )

    if any(term in issue_lower for term in ("crm", "integration", "api", "integrat")):
        return (
            "Which system should this integrate with, what data "
            "should be exchanged, and what should happen if the "
            "integration is unavailable or fails?"
        )

    if any(term in issue_lower for term in ("follow", "reminder", "non-responder", "non responder")):
        return (
            "When should the follow-up or reminder be sent, through "
            "which channel, how many attempts should be made, and "
            "when should follow-up stop?"
        )

    if any(term in issue_lower for term in ("phone", "voice", "call")):
        return (
            "What types of calls should the system handle, what "
            "actions should it be allowed to perform during a call, "
            "and when should the call be transferred to a human?"
        )

    if any(term in issue_lower for term in ("accur", "mistake", "guarantee", "never fail", "100%")):
        return (
            "What measurable accuracy or quality standard should "
            "the system meet, and what should happen when it is "
            "not confident enough to provide an answer?"
        )

    if any(term in issue_lower for term in ("medical", "clinical", "diagnos", "healthcare", "patient safety", "treatment")):
        return (
            "What healthcare-related actions should the system be "
            "allowed to perform, what must it explicitly avoid, "
            "and when should a case be escalated to a human?"
        )

    if any(term in issue_lower for term in ("timeline", "deadline", "feasib", "launch")):
        return (
            "What is the required launch deadline and which parts "
            "of this requirement are mandatory for the initial "
            "launch versus acceptable for a later phase?"
        )

    if any(term in issue_lower for term in ("scope", "boundary", "out of scope")):
        return (
            "What should be explicitly included in this requirement "
            "for the initial scope, and what should be considered "
            "out of scope?"
        )

    return (
        "What specific behavior, constraints, and success criteria "
        "should the system follow for this requirement so that the "
        "scope can be implemented without assumptions?"
    )


# ============================================================
# GROQ QUESTION GENERATION
# ============================================================

def _call_groq_discovery_generation(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> Dict[str, dict]:
    """
    Ask Groq to generate one question per risk.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(
        requirement_map=requirement_map,
        risks=risks,
    )

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format={
                    "type": "json_object",
                },
            )

            content = response.choices[0].message.content
            parsed = _extract_json(content)
            raw_questions = parsed.get("questions")

            if not isinstance(raw_questions, list):
                raise ValueError(
                    "Groq response must contain a 'questions' list."
                )

            result: Dict[str, dict] = {}

            for item in raw_questions:
                if not isinstance(item, dict):
                    continue

                risk_id = _safe_enum_value(item.get("risk_id"))
                if not risk_id:
                    continue

                result[risk_id] = {
                    "question": str(item.get("question", "")).strip(),
                    "why_asking": str(item.get("why_asking", "")).strip(),
                }

            return result

        except Exception as exc:
            last_error = exc
            if attempt >= MAX_RETRIES:
                break

    raise RuntimeError(
        "Groq discovery question generation failed after "
        f"{MAX_RETRIES + 1} attempts: {last_error}"
    )


# ============================================================
# QUESTION CLEANING
# ============================================================

def _clean_question_text(question: str) -> str:
    """
    Normalize a generated question without changing its meaning.
    """
    if not question:
        return ""

    text = question.strip()

    # Remove accidental numbering.
    text = re.sub(
        r"^\s*(?:question\s*)?\d+[\.\):-]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove surrounding quotes.
    if (
        len(text) >= 2
        and text[0] == '"'
        and text[-1] == '"'
    ):
        text = text[1:-1].strip()

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    # Ensure question punctuation.
    if text and text[-1] not in "?!":
        text += "?"

    return text


def _clean_why_text(
    why_asking: str,
    risk: Risk,
) -> str:
    """
    Clean the rationale.
    """
    text = (why_asking or "").strip()
    text = re.sub(r"\s+", " ", text)

    if len(text) < 10:
        risk_issue = _safe_enum_value(_safe_get_attr(risk, "issue", "description"))
        return (
            f"This question is needed to resolve the identified risk: {risk_issue}"
        )

    return text


# ============================================================
# QUESTION VALIDATION
# ============================================================

def _validate_question_text(question: str) -> None:
    """
    Basic deterministic quality checks.
    """
    if not question:
        raise ValueError(
            "Discovery question cannot be empty."
        )

    if len(question.strip()) < 10:
        raise ValueError(
            "Discovery question is too short."
        )

    if not question.rstrip().endswith(("?", "!")):
        raise ValueError(
            "Discovery question must end with '?' or '!'."
        )


def _validate_one_to_one_mapping(
    questions: List[DiscoveryQuestion],
    risks: List[Risk],
) -> None:
    """
    Hard gate: N risks == N questions, exactly 1-to-1.
    """
    if len(questions) != len(risks):
        raise ValueError(
            "DISCOVERY_CONTRACT_VIOLATION: "
            f"expected exactly {len(risks)} questions for "
            f"{len(risks)} risks, but received {len(questions)}."
        )

    risk_ids = [_safe_enum_value(_safe_get_attr(risk, "risk_id")) for risk in risks]
    question_risk_ids = [
        _safe_enum_value(_safe_get_attr(q, "risk_id"))
        for q in questions
    ]

    if len(set(question_risk_ids)) != len(question_risk_ids):
        raise ValueError(
            "DISCOVERY_CONTRACT_VIOLATION: "
            "a risk is mapped to more than one discovery question."
        )

    if set(question_risk_ids) != set(risk_ids):
        missing = sorted(set(risk_ids) - set(question_risk_ids))
        extra = sorted(set(question_risk_ids) - set(risk_ids))
        raise ValueError(
            "DISCOVERY_CONTRACT_VIOLATION: "
            f"missing risks={missing}, extra risks={extra}."
        )

    question_ids = [
        _safe_enum_value(_safe_get_attr(q, "question_id"))
        for q in questions
    ]

    if len(set(question_ids)) != len(question_ids):
        raise ValueError(
            "DISCOVERY_CONTRACT_VIOLATION: duplicate discovery question IDs detected."
        )

    risk_to_requirement = {
        _safe_enum_value(_safe_get_attr(risk, "risk_id")): _safe_enum_value(_safe_get_attr(risk, "requirement_id", "req_id"))
        for risk in risks
    }

    for question in questions:
        q_question_id = _safe_enum_value(_safe_get_attr(question, "question_id"))
        q_risk_id = _safe_enum_value(_safe_get_attr(question, "risk_id"))
        q_req_id = _safe_enum_value(_safe_get_attr(question, "requirement_id", "req_id"))

        expected_requirement_id = risk_to_requirement.get(q_risk_id)

        if expected_requirement_id is None:
            raise ValueError(
                "DISCOVERY_CONTRACT_VIOLATION: "
                f"question {q_question_id} references "
                f"unknown risk {q_risk_id}."
            )

        if q_req_id != expected_requirement_id:
            raise ValueError(
                "DISCOVERY_CONTRACT_VIOLATION: "
                f"question {q_question_id} has requirement "
                f"{q_req_id}, but risk "
                f"{q_risk_id} belongs to "
                f"{expected_requirement_id}."
            )


# ============================================================
# REQUIREMENT & RISK LOOKUPS
# ============================================================

def _build_requirement_lookup(
    requirement_map: RequirementMap,
) -> Dict[str, object]:
    return {
        _safe_enum_value(_safe_get_attr(req, "requirement_id", "req_id")): req
        for req in requirement_map.requirements
    }


def _build_risk_lookup(
    risks: List[Risk],
) -> Dict[str, Risk]:
    return {
        _safe_enum_value(_safe_get_attr(risk, "risk_id")): risk
        for risk in risks
    }


# ============================================================
# QUESTION CONSTRUCTION
# ============================================================

def _build_question(
    question_index: int,
    risk: Risk,
    requirement: object,
    generated: Optional[dict],
) -> DiscoveryQuestion:
    generated = generated or {}

    question_text = _clean_question_text(
        str(generated.get("question", ""))
    )

    if not question_text:
        question_text = _fallback_question(risk)

    question_text = _clean_question_text(question_text)
    _validate_question_text(question_text)

    why_asking = _clean_why_text(
        str(generated.get("why_asking", "")),
        risk,
    )

    question_id = f"DQ-{question_index:03d}"
    req_id = _safe_enum_value(_safe_get_attr(risk, "requirement_id", "req_id"))
    req_text = _safe_enum_value(_safe_get_attr(requirement, "requirement", "text"))
    risk_id = _safe_enum_value(_safe_get_attr(risk, "risk_id"))

    return DiscoveryQuestion(
        question_id=question_id,
        risk_id=risk_id,
        requirement_id=req_id,
        requirement=req_text,
        question=question_text,
        why_asking=why_asking,
    )


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_discovery_questions(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> DiscoveryQuestionSet:
    """
    Generate exactly one discovery question for every risk.
    """
    if not isinstance(requirement_map, RequirementMap):
        raise TypeError(
            "requirement_map must be a RequirementMap."
        )

    if risks is None:
        raise ValueError(
            "risks cannot be None."
        )

    if not isinstance(risks, list):
        raise TypeError(
            "risks must be a list."
        )

    if len(risks) == 0:
        raise ValueError(
            "DISCOVERY_BLOCKED: no risks were supplied. "
            "Run the risk analysis and coverage gate first."
        )

    risk_ids = [_safe_enum_value(_safe_get_attr(r, "risk_id")) for r in risks]
    if len(set(risk_ids)) != len(risk_ids):
        raise ValueError(
            "DISCOVERY_CONTRACT_VIOLATION: duplicate risk IDs."
        )

    requirement_lookup = _build_requirement_lookup(requirement_map)

    for risk in risks:
        r_req_id = _safe_enum_value(_safe_get_attr(risk, "requirement_id", "req_id"))
        r_risk_id = _safe_enum_value(_safe_get_attr(risk, "risk_id"))
        if r_req_id not in requirement_lookup:
            raise ValueError(
                "DISCOVERY_CONTRACT_VIOLATION: "
                f"{r_risk_id} references unknown "
                f"requirement_id={r_req_id}."
            )

    generated_questions = _call_groq_discovery_generation(
        requirement_map=requirement_map,
        risks=risks,
    )

    questions: List[DiscoveryQuestion] = []

    for index, risk in enumerate(risks, start=1):
        r_req_id = _safe_enum_value(_safe_get_attr(risk, "requirement_id", "req_id"))
        r_risk_id = _safe_enum_value(_safe_get_attr(risk, "risk_id"))
        
        requirement = requirement_lookup[r_req_id]
        generated = generated_questions.get(r_risk_id)

        question = _build_question(
            question_index=index,
            risk=risk,
            requirement=requirement,
            generated=generated,
        )

        questions.append(question)

    _validate_one_to_one_mapping(
        questions=questions,
        risks=risks,
    )

    try:
        result = DiscoveryQuestionSet(questions=questions)
    except ValidationError as exc:
        raise ValueError(
            f"DISCOVERY_SCHEMA_VALIDATION_FAILED: {exc}"
        ) from exc

    return result


# ============================================================
# EXPLICIT CONTRACT GATE (POLYMORPHIC & CALLER RESILIENT)
# ============================================================

def validate_discovery_question_set(*args, **kwargs) -> None:
    """
    Polymorphic hard gate for pipeline.py and external callers.
    Accepts (question_set), (question_set, risks), or (requirement_map, risks, question_set)
    in any order.
    """
    question_set: Optional[DiscoveryQuestionSet] = kwargs.get("question_set") or kwargs.get("questions")
    risks: Optional[List[Risk]] = kwargs.get("risks")
    requirement_map: Optional[RequirementMap] = kwargs.get("requirement_map")

    # Resolve positional arguments
    for arg in args:
        if isinstance(arg, DiscoveryQuestionSet) or hasattr(arg, "questions"):
            question_set = arg
        elif isinstance(arg, RequirementMap) or hasattr(arg, "requirements"):
            requirement_map = arg
        elif isinstance(arg, list):
            risks = arg

    if question_set is None:
        raise ValueError("validate_discovery_question_set: Missing DiscoveryQuestionSet.")

    questions = question_set.questions if hasattr(question_set, "questions") else question_set

    # 1. Basic question validation
    question_ids = []
    for question in questions:
        q_text = _safe_get_attr(question, "question") or ""
        _validate_question_text(q_text)
        question_ids.append(_safe_enum_value(_safe_get_attr(question, "question_id")))

    if len(question_ids) != len(set(question_ids)):
        raise ValueError("DISCOVERY_CONTRACT_VIOLATION: duplicate question IDs.")

    # 2. Risk mapping validation (if risks passed)
    if risks is not None:
        if len(questions) != len(risks):
            raise ValueError(
                "DISCOVERY_CONTRACT_VIOLATION: "
                f"{len(risks)} risks require exactly {len(risks)} questions, received {len(questions)}."
            )

        risk_ids = {_safe_enum_value(_safe_get_attr(r, "risk_id")) for r in risks}
        question_risk_ids = {_safe_enum_value(_safe_get_attr(q, "risk_id")) for q in questions}

        if risk_ids != question_risk_ids:
            raise ValueError("DISCOVERY_CONTRACT_VIOLATION: question/risk ID sets do not match.")

        counts: Dict[str, int] = {}
        for q in questions:
            q_risk_id = _safe_enum_value(_safe_get_attr(q, "risk_id"))
            counts[q_risk_id] = counts.get(q_risk_id, 0) + 1

        for r_id in risk_ids:
            if counts.get(r_id, 0) != 1:
                raise ValueError(
                    f"DISCOVERY_CONTRACT_VIOLATION: {r_id} has {counts.get(r_id, 0)} questions; expected exactly 1."
                )

        _validate_one_to_one_mapping(questions=questions, risks=risks)

    # 3. Requirement mapping validation (if requirement_map passed)
    if requirement_map is not None:
        requirement_ids = {
            _safe_enum_value(_safe_get_attr(req, "requirement_id", "req_id"))
            for req in requirement_map.requirements
        }
        for q in questions:
            q_req_id = _safe_enum_value(_safe_get_attr(q, "requirement_id", "req_id"))
            q_qid = _safe_enum_value(_safe_get_attr(q, "question_id"))
            if q_req_id not in requirement_ids:
                raise ValueError(
                    f"DISCOVERY_CONTRACT_VIOLATION: {q_qid} references unknown requirement {q_req_id}."
                )


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def generate_questions(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> DiscoveryQuestionSet:
    return generate_discovery_questions(
        requirement_map=requirement_map,
        risks=risks,
    )


def validate_discovery_questions(*args, **kwargs) -> None:
    return validate_discovery_question_set(*args, **kwargs)


def validate_questions(*args, **kwargs) -> None:
    return validate_discovery_question_set(*args, **kwargs)