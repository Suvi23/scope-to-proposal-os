"""
src/pitch_generator.py

Pitch Generator
---------------
Generates a concise, client-facing pitch from a ValidatedScope.
Supports both READY_FOR_PROPOSAL and PARTIALLY_VALIDATED scopes.

Uses a 2-tier resilient Groq strategy:
  1. Strict JSON mode
  2. Fallback to plain text mode with Python-side JSON extraction

This bypasses openai/gpt-oss-20b's occasional server-side json_validate_failed errors.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import BadRequestError, Groq, RateLimitError

from .schemas import (
    PitchDraft,
    ValidatedScope,
    ScopeStatus,
)

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_COMPLETION_TOKENS = 1400
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2
MAX_RETRY_DELAY = 8

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured.")

client = Groq(api_key=API_KEY)


FORBIDDEN_MARKETING_TERMS = [
    "seamless", "effortlessly", "instant", "instantly", "guaranteed",
    "guarantee", "always", "100%", "zero errors", "error-free",
    "fully automated", "eliminate", "maximize", "dramatically",
    "significantly", "boost", "increase", "improve", "save money",
    "reduce costs", "higher conversion", "more conversions", "more revenue",
    "roi", "best-in-class", "world-class", "safe and compliant"
]


# ============================================================
# HELPERS
# ============================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value).strip()
    return str(value).strip()


def _safe_get(obj: Any, key: str, fallback: Optional[str] = None) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        val = obj.get(key)
        if val is None and fallback:
            val = obj.get(fallback)
        return val
    val = getattr(obj, key, None)
    if val is None and fallback:
        val = getattr(obj, fallback, None)
    return val


def _sanitize_text(text: Any) -> str:
    text = _clean_text(text)
    replacements = {
        "seamless": "straightforward",
        "effortlessly": "with a simple workflow",
        "instant": "direct",
        "instantly": "directly",
        "guaranteed": "intended",
        "guarantee": "expectation",
        "fully automated": "automated where confirmed",
        "best-in-class": "practical",
        "world-class": "practical",
        "safe and compliant": "designed within the stated safety boundaries",
        "significantly": "measurably",
        "dramatically": "meaningfully",
        "maximize": "support",
        "boost": "support",
    }
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text, flags=re.IGNORECASE)
    return text.strip()


def _remove_unsupported_24_7_claim(text: str) -> str:
    text = re.sub(r"\b24\s*/\s*7\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b24\s*hours?\s*a\s*day\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bround[-\s]?the[-\s]?clock\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,;.")


# ============================================================
# JSON EXTRACTION (auto-repair + salvage)
# ============================================================

def _repair_truncated_json(text: str) -> str:
    """
    Auto-heals incomplete JSON by closing unterminated strings,
    arrays, and objects. Prevents crashes when Groq's completion is cut off.
    """
    text = text.strip()
    if not text:
        return "{}"

    in_quote = False
    escape = False
    chars = []
    for c in text:
        if escape:
            escape = False
            chars.append(c)
            continue
        if c == "\\":
            escape = True
            chars.append(c)
            continue
        if c == '"':
            in_quote = not in_quote
            chars.append(c)
            continue
        chars.append(c)
    repaired = "".join(chars)
    if in_quote:
        repaired += '"'

    stack = []
    in_quote = False
    escape = False
    for c in repaired:
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_quote = not in_quote
            continue
        if not in_quote:
            if c in "{[":
                stack.append(c)
            elif c == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
            elif c == "]":
                if stack and stack[-1] == "[":
                    stack.pop()

    for opener in reversed(stack):
        repaired += "}" if opener == "{" else "]"

    return repaired


def _extract_json_object(content: str) -> Dict[str, Any]:
    """
    Extracts a JSON object from LLM output — handles markdown fences,
    surrounding commentary, and truncation.
    """
    if not content:
        raise ValueError("LLM returned empty content.")

    text = content.strip()
    repaired = _repair_truncated_json(text)

    # 1. Direct parse
    try:
        parsed = json.loads(repaired)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", repaired, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. Search outermost braces
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

    # 4. Try raw text
    try:
        return json.loads(text)
    except Exception:
        pass

    raise ValueError(f"Could not parse valid JSON from output:\n{content}")


# ============================================================
# AUTHORITATIVE SCOPE BUILDER
# ============================================================

def _build_authoritative_scope(scope: ValidatedScope) -> Dict[str, Any]:
    pitchable_requirements: List[Dict[str, Any]] = []
    unresolved_items: List[Dict[str, Any]] = []

    for item in scope.confirmed_requirements:
        status = _enum_value(getattr(item, "status", "")).lower().strip()
        orig = _clean_text(getattr(item, "original_requirement", "") or getattr(item, "requirement", ""))
        final = _clean_text(getattr(item, "final_scope", "") or getattr(item, "requirement", ""))

        if status in {"confirmed", "modified"} and final:
            pitchable_requirements.append({
                "requirement": orig,
                "scope": final,
                "status": status,
            })
        elif status == "unresolved":
            unresolved_items.append({
                "requirement": orig,
                "status": "pending_confirmation",
            })

    # If nothing pitchable, use requirements as provisional scope
    if not pitchable_requirements:
        for item in scope.confirmed_requirements:
            status = _enum_value(getattr(item, "status", "")).lower().strip()
            if status != "rejected":
                orig = _clean_text(getattr(item, "original_requirement", "") or getattr(item, "requirement", ""))
                pitchable_requirements.append({
                    "requirement": orig,
                    "scope": orig,
                    "status": "provisional",
                })

    for u in scope.unresolved_items:
        unresolved_items.append({
            "issue": getattr(u, "issue", ""),
            "reason": getattr(u, "reason", ""),
        })

    return {
        "business_goal": _clean_text(scope.business_goal),
        "target_users": [_clean_text(u) for u in scope.target_users if _clean_text(u)],
        "pitchable_scope": pitchable_requirements,
        "assumptions": [_clean_text(a) for a in scope.assumptions if _clean_text(a)],
        "open_items": unresolved_items,
    }


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an expert AI solution consultant. Generate a concise, tailored client pitch
strictly grounded in the provided scope. Do not invent capabilities or guarantee
unproven outcomes.

Return ONLY valid JSON matching this exact format (no markdown, no commentary):
{
  "headline": "Punchy one-line value proposition",
  "pitch": "2-3 concise paragraphs connecting their business goal to the solution",
  "value_points": ["Key benefit 1", "Key benefit 2", "Key benefit 3"],
  "assumptions": ["Key baseline assumption"]
}

RULES:
- All four keys are required.
- value_points must be an array of 3-5 strings.
- assumptions must be an array of strings (can be empty).
- No trailing commas.
- No comments.
- Return exactly one complete JSON object.
"""


# ============================================================
# OUTPUT NORMALIZATION
# ============================================================

def _normalize_pitch(payload: Dict[str, Any], authoritative_scope: Dict[str, Any], scope: ValidatedScope) -> PitchDraft:
    """
    Sanitize raw payload and build a PitchDraft with minimum safety guards.
    """
    headline = _sanitize_text(
        payload.get("headline") or payload.get("title") or "Tailored AI Solution Pitch"
    )
    pitch_text = _sanitize_text(
        payload.get("pitch") or payload.get("value_proposition") or "Tailored AI solution."
    )

    raw_points = payload.get("value_points") or payload.get("key_benefits") or []
    if isinstance(raw_points, str):
        raw_points = [raw_points]
    if not isinstance(raw_points, list):
        raw_points = []
    value_points = [_sanitize_text(p) for p in raw_points if _clean_text(p)][:5]

    if len(value_points) < 3:
        value_points.extend([
            "Directly addresses the client's stated business goals",
            "Grounded strictly in validated scope commitments",
            "Preserves human oversight and safety boundaries",
        ])
        value_points = value_points[:3]

    # 24/7 guard
    confirmed_text = json.dumps(authoritative_scope.get("pitchable_scope", [])).lower()
    if "24/7" not in confirmed_text:
        headline = _remove_unsupported_24_7_claim(headline)
        pitch_text = _remove_unsupported_24_7_claim(pitch_text)
        value_points = [
            _remove_unsupported_24_7_claim(p)
            for p in value_points
            if _remove_unsupported_24_7_claim(p)
        ]

    # Ensure minimum text
    if not headline or len(headline) < 4:
        headline = "Tailored AI Solution Pitch"
    if not pitch_text or len(pitch_text) < 10:
        pitch_text = (
            f"This solution is designed around the client's stated goal: "
            f"{scope.business_goal}. It focuses on the confirmed scope while "
            f"preserving human oversight for any items outside the validated boundary."
        )

    assumptions = [_clean_text(a) for a in (payload.get("assumptions") or scope.assumptions) if _clean_text(a)]

    return PitchDraft(
        headline=headline,
        pitch=pitch_text,
        value_points=value_points,
        assumptions=assumptions,
    )


# ============================================================
# MAIN PUBLIC FUNCTION
# ============================================================

def generate_pitch(validated_scope: ValidatedScope) -> PitchDraft:
    """
    Generates a pitch strictly aligned with ValidatedScope using openai/gpt-oss-20b.
    Uses a 2-tier resilient Groq strategy to bypass server-side JSON validation errors.
    """
    if not isinstance(validated_scope, ValidatedScope):
        raise TypeError("generate_pitch() requires a ValidatedScope object.")

    scope_status = _enum_value(validated_scope.overall_scope_status).lower().strip()
    if scope_status == ScopeStatus.NEEDS_MORE_DISCOVERY.value:
        raise RuntimeError("Pitch generation blocked: scope status is 'needs_more_discovery'.")

    authoritative_scope = _build_authoritative_scope(validated_scope)
    scope_json = json.dumps(authoritative_scope, ensure_ascii=False)

    user_prompt = (
        f"CLIENT SCOPE DATA:\n{scope_json}\n\n"
        "Generate the tailored pitch as a single valid JSON object."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_prompt},
    ]

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            # -------- Attempt 1: strict JSON mode --------
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = _extract_json_object(raw_content)
            return _normalize_pitch(parsed, authoritative_scope, validated_scope)

        except (BadRequestError, Exception) as exc:
            last_error = exc
            err_str = str(exc)

            # -------- Attempt 2: fallback to plain text mode --------
            if "json_validate_failed" in err_str or isinstance(exc, BadRequestError):
                try:
                    fallback_response = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    SYSTEM_PROMPT.strip()
                                    + "\n\nCRITICAL: Return ONLY a single valid JSON object. "
                                    "No markdown, no explanations, no code fences."
                                ),
                            },
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.1,
                        max_completion_tokens=MAX_COMPLETION_TOKENS,
                    )
                    raw_content = fallback_response.choices[0].message.content or "{}"
                    parsed = _extract_json_object(raw_content)
                    return _normalize_pitch(parsed, authoritative_scope, validated_scope)
                except Exception as fb_exc:
                    last_error = fb_exc

            if isinstance(exc, RateLimitError):
                time.sleep(min(BASE_RETRY_DELAY * (attempt + 1), MAX_RETRY_DELAY))
            else:
                time.sleep(BASE_RETRY_DELAY)

    # -------- Attempt 3: deterministic fallback --------
    # If Groq is completely refusing to cooperate, generate a minimal safe pitch
    # from the validated scope directly. This prevents the entire pipeline from crashing.
    try:
        return _deterministic_fallback_pitch(authoritative_scope, validated_scope)
    except Exception:
        pass

    raise RuntimeError(
        f"Pitch generation failed after {MAX_RETRIES} attempts: {last_error}"
    )


# ============================================================
# DETERMINISTIC FALLBACK (never crashes)
# ============================================================

def _deterministic_fallback_pitch(
    authoritative_scope: Dict[str, Any],
    scope: ValidatedScope,
) -> PitchDraft:
    """
    Generates a minimal, safe pitch entirely in Python if Groq fails repeatedly.
    Ensures the pipeline can still proceed to proposal generation.
    """
    goal = _clean_text(scope.business_goal) or "the client's stated objective"
    users = ", ".join(scope.target_users) if scope.target_users else "the intended users"

    pitchable = authoritative_scope.get("pitchable_scope", [])
    top_scope = [item.get("scope", "") for item in pitchable[:3] if item.get("scope")]

    headline = f"A tailored AI solution focused on {goal}"

    pitch_text = (
        f"This proposal outlines a tailored AI solution designed around {goal}. "
        f"The system will serve {users} through the confirmed scope commitments "
        f"gathered during the discovery call, while preserving human oversight "
        f"and safety boundaries for any items outside the validated scope. "
        f"All capabilities are grounded strictly in what was confirmed with the client."
    )

    value_points = []
    for scope_text in top_scope:
        if scope_text:
            value_points.append(scope_text)

    while len(value_points) < 3:
        value_points.append("Grounded strictly in validated scope commitments")
        value_points.append("Preserves human oversight for critical decisions")
        value_points.append("Focused on the client's stated business goal")
        value_points = list(dict.fromkeys(value_points))[:3]

    value_points = value_points[:5]

    assumptions = [_clean_text(a) for a in scope.assumptions if _clean_text(a)]

    return PitchDraft(
        headline=headline,
        pitch=pitch_text,
        value_points=value_points,
        assumptions=assumptions,
    )