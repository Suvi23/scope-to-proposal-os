"""
Risk Analyzer
-------------

Real Groq-powered risk analysis for the Scope-to-Proposal AI OS.

Flow:

RequirementMap
    ↓
Groq Risk Analysis
    ↓
Remove obvious duplicate risks
    ↓
Apply simple healthcare safety rules
    ↓
Add fallback risk for missing requirements
    ↓
Stable RISK-### IDs
    ↓
Validated Risk objects
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.schemas import RequirementMap, Risk


# ============================================================
# CONFIG
# ============================================================

DEFAULT_GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. "
        "Please set your Groq API key before running the analyzer."
    )

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# ============================================================
# DEFENSIVE ENUM RESOLVER HELPER
# ============================================================

def _safe_enum_value(val: Any) -> str:
    """
    Safely extract the string value from an Enum or a plain string.
    Prevents 'str' object has no attribute 'value' crashes.
    """
    if val is None:
        return ""
    # If it's a Pydantic Enum member or custom Enum
    if hasattr(val, "value"):
        return str(val.value).strip()
    # If it's already a string or other primitive
    return str(val).strip()


# ============================================================
# HELPERS
# ============================================================

def _model_to_dict(value: Any) -> Dict[str, Any]:
    """Convert a Pydantic model or dict into a normal dictionary."""

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    raise TypeError(
        f"Expected dict or Pydantic model, got {type(value).__name__}"
    )


def _requirement_list(
    requirement_map: Any,
) -> List[Dict[str, Any]]:
    """Extract requirements from RequirementMap."""

    data = _model_to_dict(requirement_map)

    requirements = data.get("requirements")

    if not isinstance(requirements, list):
        raise ValueError(
            "RequirementMap.requirements must be a list."
        )

    return [
        _model_to_dict(requirement)
        for requirement in requirements
    ]


def _normalize_text(value: Any) -> str:
    """Normalize text for simple duplicate detection."""

    if value is None:
        return ""

    text = _safe_enum_value(value).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def _risk_type(value: Any) -> str:
    """Normalize risk type securely."""
    return _safe_enum_value(value).lower()


def _severity(value: Any) -> str:
    """Normalize severity securely."""
    return _safe_enum_value(value).lower()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json_object(
    content: str,
) -> Dict[str, Any]:
    """
    Extract a JSON object from Groq output.
    """

    if not content:
        raise ValueError(
            "Groq returned an empty risk analysis response."
        )

    text = content.strip()

    # 1. Direct JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Remove markdown fences
    cleaned = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.replace(
        "```",
        "",
    ).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. Find first JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end > start:
        candidate = cleaned[start:end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Groq returned invalid JSON.\n"
        f"Raw response:\n{content}"
    )


# ============================================================
# GROQ PROMPT
# ============================================================

def _build_risk_prompt(
    requirements_text: str,
    source_text: str,
) -> str:
    """Build the Groq risk-analysis prompt."""

    return f"""
You are a senior AI solution consultant performing risk analysis
before a client discovery call.

Analyze ONLY the supplied client requirements.

Identify important:
- ambiguities
- conflicts
- feasibility concerns
- safety concerns
- integration concerns
- timeline concerns
- accuracy concerns
- scope gaps

IMPORTANT RULES:

1. Only identify risks relevant to the supplied requirements.
2. Never invent requirements.
3. Do not generate discovery questions.
4. Do not propose solutions.
5. Do not write a proposal.
6. Every supplied requirement must have at least one risk.
7. Prefer one meaningful risk per requirement.
8. Multiple risks for one requirement are allowed only when
   genuinely different.
9. Every risk MUST reference one of the supplied requirement IDs.
10. Return a JSON object only.

HEALTHCARE SAFETY RULES:

- Diagnosing disease from symptoms = CRITICAL safety risk.
- Recommending medicines = CRITICAL safety risk.
- Prescribing medicines = CRITICAL safety risk.
- Treatment recommendations = CRITICAL safety risk.
- Unclear symptom guidance = HIGH safety risk.
- Medical follow-up involving medical advice = HIGH safety risk.

NORMAL BUSINESS RULES:

- Missing information → ambiguity.
- External system dependency → integration.
- Uncertain implementation → feasibility.
- Unclear boundaries → scope.
- Unclear timing → timeline.
- Accuracy/guarantee concerns → accuracy.

Allowed risk types:

ambiguity
conflict
feasibility
safety
integration
timeline
accuracy
scope

Allowed severities:

low
medium
high
critical

Return exactly this JSON structure:

{{
  "risks": [
    {{
      "requirement_id": "REQ-001",
      "issue": "Short description of the risk",
      "type": "ambiguity",
      "severity": "medium",
      "evidence": "Evidence from the requirement",
      "impact": "Potential impact",
      "needs_confirmation": true
    }}
  ]
}}

Do not return markdown.
Do not return explanations.
Do not return discovery questions.

CLIENT REQUIREMENTS:

{requirements_text}

ORIGINAL CLIENT REQUEST:

{source_text}
"""


# ============================================================
# GROQ RISK ANALYSIS
# ============================================================

def _call_groq_risk_analysis(
    requirement_map: RequirementMap,
    source_text: str = "",
) -> Dict[str, Any]:
    """
    Call real Groq to analyze requirement risks.
    """

    requirements = _requirement_list(
        requirement_map
    )

    requirements_text = json.dumps(
        requirements,
        indent=2,
        ensure_ascii=False,
    )

    prompt = _build_risk_prompt(
        requirements_text=requirements_text,
        source_text=source_text,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise senior risk analyst. "
                "Analyze only the supplied requirements. "
                "Return one JSON object containing a risks array."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    try:
        response = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={
                "type": "json_object"
            },
        )

        content = response.choices[0].message.content
        result = _extract_json_object(content or "")

        risks = result.get("risks")
        if not isinstance(risks, list):
            raise ValueError("Groq response must contain a 'risks' list.")

        return result

    except Exception as strict_error:
        try:
            fallback_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a precise senior risk analyst. "
                        "Return ONLY a JSON object with a 'risks' array. "
                        "No markdown. No explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]

            response = client.chat.completions.create(
                model=DEFAULT_GROQ_MODEL,
                messages=fallback_messages,
                temperature=0.1,
                max_tokens=3000,
            )

            content = response.choices[0].message.content
            result = _extract_json_object(content or "")

            risks = result.get("risks")
            if not isinstance(risks, list):
                raise ValueError("Groq response must contain a 'risks' list.")

            return result

        except Exception as fallback_error:
            raise RuntimeError(
                "Groq risk analysis failed.\n\n"
                f"Strict JSON attempt:\n{strict_error}\n\n"
                f"Fallback JSON parsing attempt:\n{fallback_error}"
            ) from fallback_error


# ============================================================
# SIMPLE DUPLICATE DETECTION
# ============================================================

def _is_obvious_duplicate(
    existing: Dict[str, Any],
    candidate: Dict[str, Any],
) -> bool:
    """
    Detect obvious duplicate risks.
    """

    existing_id = _safe_enum_value(existing.get("requirement_id") or existing.get("req_id"))
    candidate_id = _safe_enum_value(candidate.get("requirement_id") or candidate.get("req_id"))

    if existing_id != candidate_id:
        return False

    existing_issue = _normalize_text(existing.get("issue"))
    candidate_issue = _normalize_text(candidate.get("issue"))

    if not existing_issue or not candidate_issue:
        return False

    # Exact duplicate.
    if existing_issue == candidate_issue:
        return True

    # One issue contains the other.
    if existing_issue in candidate_issue or candidate_issue in existing_issue:
        return True

    stop_words = {
        "the", "a", "an", "and", "or", "of", "to", "for", "is", "are",
        "with", "from", "this", "that", "requirement", "details",
        "detailed", "scope", "unclear", "unspecified", "undefined",
    }

    existing_words = set(existing_issue.split()) - stop_words
    candidate_words = set(candidate_issue.split()) - stop_words

    if not existing_words or not candidate_words:
        return False

    overlap = existing_words.intersection(candidate_words)
    return len(overlap) >= 3


def _remove_duplicate_risks(
    risks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove obvious duplicate risks."""
    unique_risks: List[Dict[str, Any]] = []

    for risk in risks:
        duplicate = False
        for existing in unique_risks:
            if _is_obvious_duplicate(existing, risk):
                duplicate = True
                break
        if not duplicate:
            unique_risks.append(risk)

    return unique_risks


# ============================================================
# HEALTHCARE SAFETY RULES
# ============================================================

def _apply_safety_rules(
    risk: Dict[str, Any],
    requirement: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply deterministic safety overrides for clearly medical requirements.
    """
    requirement_text = _normalize_text(requirement.get("requirement", ""))
    issue_text = _normalize_text(risk.get("issue", ""))
    combined = f"{requirement_text} {issue_text}"

    diagnosis_terms = ["diagnose", "diagnosis", "diagnosing", "disease diagnosis"]
    medicine_terms = [
        "recommend medicine", "recommend medicines", "medicine recommendation",
        "medication recommendation", "prescribe", "prescription", "dosage",
        "drug recommendation", "recommend drugs"
    ]
    treatment_terms = ["recommend treatment", "treatment recommendation", "medical treatment"]

    if any(term in combined for term in diagnosis_terms):
        risk["type"] = "safety"
        risk["severity"] = "critical"
        risk["needs_confirmation"] = True

    elif any(term in combined for term in medicine_terms):
        risk["type"] = "safety"
        risk["severity"] = "critical"
        risk["needs_confirmation"] = True

    elif any(term in combined for term in treatment_terms):
        risk["type"] = "safety"
        risk["severity"] = "critical"
        risk["needs_confirmation"] = True

    return risk


# ============================================================
# FALLBACK RISK
# ============================================================

def _create_fallback_risk(
    requirement: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a minimal clarification risk when Groq fails
    to return a risk for an existing requirement.
    """
    requirement_id = _safe_enum_value(
        requirement.get("requirement_id") or requirement.get("req_id")
    )
    requirement_text = _safe_enum_value(
        requirement.get("requirement") or requirement.get("text")
    )

    return {
        "requirement_id": requirement_id,
        "issue": (
            "The implementation scope and acceptance criteria "
            "for this requirement are not fully defined."
        ),
        "type": "ambiguity",
        "severity": "medium",
        "evidence": f"The requirement is: {requirement_text}",
        "impact": (
            "The requirement may be interpreted differently "
            "by the client and implementation team."
        ),
        "needs_confirmation": True,
    }


def _ensure_requirement_coverage(
    risks: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Ensure every requirement has at least one risk.
    """
    covered_requirement_ids = {
        _safe_enum_value(risk.get("requirement_id") or risk.get("req_id"))
        for risk in risks
    }

    result = list(risks)

    for requirement in requirements:
        req_id = _safe_enum_value(
            requirement.get("requirement_id") or requirement.get("req_id")
        )
        if req_id not in covered_requirement_ids:
            result.append(_create_fallback_risk(requirement))

    return result


# ============================================================
# RISK NORMALIZATION
# ============================================================

def _normalize_risk(
    raw_risk: Dict[str, Any],
    requirement_lookup: Dict[str, Dict[str, Any]],
    index: int,
) -> Risk:
    """Convert Groq/fallback risk into the Risk schema."""

    if not isinstance(raw_risk, dict):
        raise ValueError(
            f"Risk must be a JSON object, got: {type(raw_risk).__name__}"
        )

    # Defensive key lookup supporting aliases
    requirement_id = _safe_enum_value(
        raw_risk.get("requirement_id") or raw_risk.get("req_id")
    )

    if requirement_id not in requirement_lookup:
        raise ValueError(
            f"Risk references unknown requirement_id: {requirement_id}"
        )

    requirement = requirement_lookup[requirement_id]

    issue = _safe_enum_value(
        raw_risk.get("issue") or raw_risk.get("description") or raw_risk.get("details")
    )
    evidence = _safe_enum_value(raw_risk.get("evidence"))
    impact = _safe_enum_value(raw_risk.get("impact"))

    if not issue:
        raise ValueError(f"Risk for {requirement_id} has no issue.")

    if not evidence:
        evidence = (
            "Risk identified from requirement: "
            f"{_safe_enum_value(requirement.get('requirement') or requirement.get('text'))}"
        )

    if not impact:
        impact = (
            "The requirement may be implemented incorrectly without clarification."
        )

    risk_type = _risk_type(raw_risk.get("type", "ambiguity"))
    severity = _severity(raw_risk.get("severity", "medium"))

    valid_types = {
        "ambiguity", "conflict", "feasibility", "safety",
        "integration", "timeline", "accuracy", "scope"
    }
    valid_severities = {"low", "medium", "high", "critical"}

    if risk_type not in valid_types:
        risk_type = "ambiguity"

    if severity not in valid_severities:
        severity = "medium"

    cleaned = {
        "risk_id": f"RISK-{index:03d}",
        "requirement_id": requirement_id,
        "issue": issue,
        "type": risk_type,
        "severity": severity,
        "evidence": evidence,
        "impact": impact,
        "needs_confirmation": bool(raw_risk.get("needs_confirmation", True)),
    }

    cleaned = _apply_safety_rules(cleaned, requirement)

    try:
        return Risk(**cleaned)
    except Exception as exc:
        raise ValueError(
            f"Invalid risk generated for {requirement_id}: {exc}"
        ) from exc


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_risks(
    requirement_map: RequirementMap,
    source_text: Optional[str] = None,
) -> List[Risk]:
    """
    Main public risk-analysis function.
    """
    requirements = _requirement_list(requirement_map)

    if not requirements:
        raise ValueError(
            "Cannot analyze risks because no requirements were provided."
        )

    requirement_lookup = {
        _safe_enum_value(req.get("requirement_id") or req.get("req_id")): req
        for req in requirements
    }

    # 1. REAL GROQ ANALYSIS
    ai_risk_data = _call_groq_risk_analysis(
        requirement_map=requirement_map,
        source_text=source_text or "",
    )

    raw_risk_list = ai_risk_data.get("risks")

    if not isinstance(raw_risk_list, list):
        raise ValueError("Groq risk analysis did not return a valid risks list.")

    # 2. BASIC VALIDATION
    valid_raw_risks: List[Dict[str, Any]] = []

    for raw_risk in raw_risk_list:
        if not isinstance(raw_risk, dict):
            continue

        requirement_id = _safe_enum_value(
            raw_risk.get("requirement_id") or raw_risk.get("req_id")
        )

        if requirement_id not in requirement_lookup:
            continue

        issue_str = _safe_enum_value(
            raw_risk.get("issue") or raw_risk.get("description")
        )
        if not issue_str:
            continue

        valid_raw_risks.append(raw_risk)

    # 3. REMOVE OBVIOUS DUPLICATES
    unique_raw_risks = _remove_duplicate_risks(valid_raw_risks)

    # 4. ENSURE EVERY REQUIREMENT HAS A RISK
    covered_raw_risks = _ensure_requirement_coverage(
        risks=unique_raw_risks,
        requirements=requirements,
    )

    # 5. NORMALIZE INTO SCHEMAS
    risks: List[Risk] = []

    for raw_risk in covered_raw_risks:
        risk = _normalize_risk(
            raw_risk=raw_risk,
            requirement_lookup=requirement_lookup,
            index=len(risks) + 1,
        )
        risks.append(risk)

    if not risks:
        raise ValueError("Risk analysis produced no valid risks.")

    return risks


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def analyze_requirements(
    requirement_map: RequirementMap,
    source_text: Optional[str] = None,
) -> List[Risk]:
    """
    Compatibility alias used by existing project code.
    """
    return analyze_risks(
        requirement_map=requirement_map,
        source_text=source_text,
    )


def validate_requirement_coverage(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> bool:
    """
    Validate that every extracted requirement has at least one associated risk.
    """
    requirements = _requirement_list(requirement_map)

    if not requirements:
        raise ValueError("Requirement map contains no requirements.")

    requirement_ids = {
        _safe_enum_value(req.get("requirement_id") or req.get("req_id"))
        for req in requirements
    }

    risk_requirement_ids = set()

    for risk in risks:
        if isinstance(risk, dict):
            req_id = risk.get("requirement_id") or risk.get("req_id")
        else:
            req_id = getattr(risk, "requirement_id", getattr(risk, "req_id", None))

        if req_id:
            risk_requirement_ids.add(_safe_enum_value(req_id))

    missing = requirement_ids - risk_requirement_ids

    if missing:
        raise ValueError(
            "Risk coverage missing for requirements: "
            + ", ".join(sorted(missing))
        )

    return True


def validate_risk_coverage(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> bool:
    """
    Backward-compatible alias.
    """
    return validate_requirement_coverage(
        requirement_map=requirement_map,
        risks=risks,
    )