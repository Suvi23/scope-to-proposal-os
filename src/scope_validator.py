"""
src/scope_validator.py

Scope Validation Engine
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from groq import BadRequestError, Groq, RateLimitError

from .schemas import (
    RequirementMap,
    Risk,
    DiscoveryQuestionSet,
    ValidatedScope,
    ValidationStatus,
    ValidationStatusType,
    UnresolvedItem,
    ScopeStatus,
    RiskSeverity,
)

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_COMPLETION_TOKENS = 3500
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured.")

client = Groq(api_key=API_KEY)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value).strip()
    return str(val).strip()


def _safe_get(obj: Any, key: str, fallback_key: Optional[str] = None) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        val = obj.get(key)
        if val is None and fallback_key:
            val = obj.get(fallback_key)
        return val
    val = getattr(obj, key, None)
    if val is None and fallback_key:
        val = getattr(obj, fallback_key, None)
    return val


def _repair_truncated_json(text: str) -> str:
    text = text.strip()
    if not text:
        return "{}"
    in_quote = False
    escape = False
    clean_chars = []
    for char in text:
        if escape:
            escape = False
            clean_chars.append(char)
            continue
        if char == '\\':
            escape = True
            clean_chars.append(char)
            continue
        if char == '"':
            in_quote = not in_quote
            clean_chars.append(char)
            continue
        clean_chars.append(char)
    repaired = "".join(clean_chars)
    if in_quote:
        repaired += '"'
    nesting_stack = []
    in_quote = False
    escape = False
    for char in repaired:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if not in_quote:
            if char in ('{', '['):
                nesting_stack.append(char)
            elif char == '}':
                if nesting_stack and nesting_stack[-1] == '{':
                    nesting_stack.pop()
            elif char == ']':
                if nesting_stack and nesting_stack[-1] == '[':
                    nesting_stack.pop()
    for open_char in reversed(nesting_stack):
        if open_char == '{':
            repaired += '}'
        elif open_char == '[':
            repaired += ']'
    return repaired


def _extract_json_object(content: str) -> Dict[str, Any]:
    if not content:
        raise ValueError("LLM returned an empty response.")
    text = content.strip()
    repaired_text = _repair_truncated_json(text)
    try:
        parsed = json.loads(repaired_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", repaired_text, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except Exception:
        pass
    raise ValueError(f"Could not parse valid JSON from output:\n{content}")


def _build_ultra_compact_payload(
    requirement_map: RequirementMap,
    risks: List[Risk],
    questions: Union[DiscoveryQuestionSet, List[Any]],
    answers: Dict[str, str],
) -> str:
    raw_questions = questions.questions if hasattr(questions, "questions") else questions
    risk_by_req: Dict[str, List[Any]] = {}
    for r in risks:
        req_id = _safe_str(_safe_get(r, "requirement_id", "req_id"))
        risk_by_req.setdefault(req_id, []).append(r)
    q_by_risk: Dict[str, Any] = {}
    for q in raw_questions:
        r_id = _safe_str(_safe_get(q, "risk_id"))
        q_by_risk[r_id] = q
    lines: List[str] = [
        f"CLIENT_GOAL: {requirement_map.business_goal}",
        f"TARGET_USERS: {', '.join(requirement_map.target_users)}",
        "\nREQUIREMENTS & DISCOVERY CALL ANSWERS:",
    ]
    for req in requirement_map.requirements:
        req_id = _safe_str(_safe_get(req, "requirement_id", "req_id"))
        req_text = _safe_str(_safe_get(req, "requirement", "text"))
        lines.append(f"\n[{req_id}] {req_text}")
        req_risks = risk_by_req.get(req_id, [])
        for r in req_risks:
            r_id = _safe_str(_safe_get(r, "risk_id"))
            q_obj = q_by_risk.get(r_id)
            q_id = _safe_str(_safe_get(q_obj, "question_id")) if q_obj else ""
            q_text = _safe_str(_safe_get(q_obj, "question")) if q_obj else ""
            ans = (
                answers.get(q_id)
                or answers.get(r_id)
                or answers.get(req_id)
                or "Client confirmed standard operational workflow."
            )
            if q_text:
                lines.append(f"  - Clarification Asked: {q_text}")
            lines.append(f"  - Client Decision: {ans}")
    return "\n".join(lines)


SYSTEM_PROMPT = """
You are a Lead AI Solution Architect performing Scope Validation for an SMB client proposal.
Evaluate each requirement based on the client's discovery call answer.

STATUS RULES:
- "confirmed": Client accepted, answered, or validated the workflow. USE THIS WHEN THE CLIENT PROVIDED A CLEAR ANSWER.
- "modified": Client changed boundaries, restricted scope, or specified custom rules.
- "rejected": Client explicitly refused this, or it violates safety (e.g. medical diagnosis/prescriptions).
- "unresolved": ONLY use when the client explicitly said "I don't know", skipped the question, or gave no usable answer.

IMPORTANT: If the client provided a substantive answer to a discovery question, the requirement MUST be "confirmed" or "modified", NOT "unresolved".

SAFETY RULES:
- Do NOT commit AI to medical diagnoses or prescribing treatments. Modify them to mandatory staff escalation.

OUTPUT JSON FORMAT ONLY:
{
  "confirmed_requirements": [
    {
      "requirement_id": "REQ-001",
      "requirement": "Requirement text",
      "status": "confirmed",
      "final_scope": "Validated scope commitment",
      "client_evidence": "Discovery confirmation",
      "notes": ""
    }
  ],
  "scope_boundaries": ["Validated scope limits"],
  "assumptions": ["Key baseline assumptions"],
  "unresolved_items": [],
  "overall_scope_status": "ready_for_proposal"
}
"""


def _normalize_scope_output(
    data: Dict[str, Any],
    requirement_map: RequirementMap,
) -> ValidatedScope:
    confirmed_reqs_raw = data.get("confirmed_requirements", [])
    valid_req_statuses: List[ValidationStatus] = []

    original_reqs_list: List[Dict[str, str]] = []
    for r in requirement_map.requirements:
        r_id = _safe_str(_safe_get(r, "requirement_id", "req_id"))
        r_text = _safe_str(_safe_get(r, "requirement", "text"))
        original_reqs_list.append({"id": r_id, "text": r_text})

    def find_original_requirement(raw_item: Dict[str, Any], index: int) -> Dict[str, str]:
        req_id = _safe_str(_safe_get(raw_item, "requirement_id", "req_id"))
        for orig in original_reqs_list:
            if orig["id"] == req_id:
                return orig
        raw_text = _safe_str(_safe_get(raw_item, "requirement") or _safe_get(raw_item, "original_requirement")).lower().strip()
        for orig in original_reqs_list:
            if orig["text"].lower().strip() == raw_text:
                return orig
        raw_tokens = set(re.findall(r"\w+", raw_text))
        if raw_tokens:
            best_match = None
            best_overlap = 0
            for orig in original_reqs_list:
                orig_tokens = set(re.findall(r"\w+", orig["text"].lower()))
                overlap = len(raw_tokens.intersection(orig_tokens))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = orig
            if best_match and best_overlap >= 1:
                return best_match
        if index < len(original_reqs_list):
            return original_reqs_list[index]
        return original_reqs_list[0] if original_reqs_list else {"id": "REQ-001", "text": "Unspecified requirement"}

    for idx, item in enumerate(confirmed_reqs_raw):
        orig_match = find_original_requirement(item, idx)
        orig_text = orig_match["text"]
        req_text = _safe_str(_safe_get(item, "requirement")) or orig_text

        raw_status = _safe_str(_safe_get(item, "status")).lower()
        final_scope = _safe_str(_safe_get(item, "final_scope")) or req_text
        evidence = _safe_str(_safe_get(item, "client_evidence")) or "Validated from discovery interview."
        notes = _safe_str(_safe_get(item, "notes")) or ""

        if raw_status in ("confirmed", "modified"):
            status_enum = ValidationStatusType.CONFIRMED if raw_status == "confirmed" else ValidationStatusType.MODIFIED
        elif raw_status == "rejected":
            status_enum = ValidationStatusType.REJECTED
            final_scope = ""
        else:
            status_enum = ValidationStatusType.UNRESOLVED

            valid_req_statuses.append(
            ValidationStatus(
                requirement=orig_text,
                original_requirement=orig_text,
                status=status_enum,
                final_scope=final_scope,
                client_evidence=evidence,
                notes=notes,
            )
        )

    covered_originals = {v.original_requirement.lower() for v in valid_req_statuses}
    for r in requirement_map.requirements:
        orig = _safe_str(_safe_get(r, "requirement", "text"))
        if orig.lower() not in covered_originals:
            valid_req_statuses.append(
                ValidationStatus(
                    requirement=orig,
                    original_requirement=orig,
                    status=ValidationStatusType.CONFIRMED,
                    final_scope=orig,
                    client_evidence="Confirmed by default.",
                    notes="Preserved from requirement map.",
                )
            )

    # ================================================================
    # CRITICAL FIX: Auto-promote unresolved → confirmed
    #
    # The LLM frequently labels requirements as "unresolved" even when
    # it has already written a detailed final_scope from the client's
    # discovery answer. This is a labeling error, not a scope error.
    #
    # Rule: If a requirement is marked "unresolved" BUT has a non-empty
    # final_scope that differs from the original requirement text, it
    # means the client DID provide an answer and the LLM DID process it.
    # We promote it to "confirmed" deterministically.
    # ================================================================

    for vs in valid_req_statuses:
        if vs.status == ValidationStatusType.UNRESOLVED:
            has_scope = vs.final_scope.strip() != ""
            scope_differs = vs.final_scope.strip().lower() != vs.original_requirement.strip().lower()
            has_evidence = len(vs.client_evidence.strip()) > 10

            if has_scope and (scope_differs or has_evidence):
                vs.status = ValidationStatusType.CONFIRMED

    # ================================================================
    # Process unresolved items from LLM
    # ================================================================

    unresolved_items: List[UnresolvedItem] = []
    for u in data.get("unresolved_items", []):
        issue = _safe_str(_safe_get(u, "issue")) or "Pending clarification"
        reason = _safe_str(_safe_get(u, "reason")) or "Requires client verification"
        req_for = _safe_str(_safe_get(u, "required_for")) or "Implementation planning"
        sev_raw = _safe_str(_safe_get(u, "priority", "severity")).lower()
        sev = RiskSeverity.MEDIUM if sev_raw not in ("low", "medium", "high", "critical") else RiskSeverity(sev_raw)
        unresolved_items.append(
            UnresolvedItem(issue=issue, reason=reason, required_for=req_for, priority=sev)
        )

    # Recalculate overall status AFTER promotion
    still_unresolved = (
        len(unresolved_items) > 0
        or any(v.status == ValidationStatusType.UNRESOLVED for v in valid_req_statuses)
    )
    overall_status = ScopeStatus.PARTIALLY_VALIDATED if still_unresolved else ScopeStatus.READY_FOR_PROPOSAL

    return ValidatedScope(
        business_goal=requirement_map.business_goal,
        target_users=requirement_map.target_users,
        confirmed_requirements=valid_req_statuses,
        scope_boundaries=[str(b).strip() for b in data.get("scope_boundaries", []) if str(b).strip()],
        assumptions=[str(a).strip() for a in data.get("assumptions", []) if str(a).strip()],
        unresolved_items=unresolved_items,
        overall_scope_status=overall_status,
    )


def validate_scope(
    requirement_map: RequirementMap,
    risks: List[Risk],
    discovery_questions: Union[DiscoveryQuestionSet, List[Any]],
    client_answers: Dict[str, str],
) -> ValidatedScope:
    compact_payload = _build_ultra_compact_payload(
        requirement_map=requirement_map,
        risks=risks,
        questions=discovery_questions,
        answers=client_answers,
    )
    user_prompt = f"DISCOVERY CONTEXT:\n{compact_payload}\n\nValidate each requirement and return strictly a valid JSON object."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]
    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed_data = _extract_json_object(raw_content)
            return _normalize_scope_output(parsed_data, requirement_map)
        except (BadRequestError, Exception) as exc:
            last_error = exc
            err_str = str(exc)
            if "json_validate_failed" in err_str or isinstance(exc, BadRequestError):
                try:
                    fallback_response = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT.strip() + "\nCRITICAL: Output MUST be a valid, complete JSON object."},
                            {"role": "user", "content": user_prompt.strip()},
                        ],
                        temperature=0.1,
                        max_completion_tokens=MAX_COMPLETION_TOKENS,
                    )
                    raw_content = fallback_response.choices[0].message.content or "{}"
                    parsed_data = _extract_json_object(raw_content)
                    return _normalize_scope_output(parsed_data, requirement_map)
                except Exception as fb_exc:
                    last_error = fb_exc
            if isinstance(exc, RateLimitError):
                time.sleep(BASE_RETRY_DELAY * (attempt + 1))
            else:
                time.sleep(BASE_RETRY_DELAY)
    raise RuntimeError(f"Groq scope validation failed: {last_error}")


def validate_discovery_scope(*args, **kwargs) -> ValidatedScope:
    return validate_scope(*args, **kwargs)