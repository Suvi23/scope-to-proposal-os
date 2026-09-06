"""
src/proposal_generator.py

Proposal Generator
------------------

Generates a professional client proposal from ValidatedScope
and optional PitchDraft.

Architecture rules:
- Uses REAL Groq AI (openai/gpt-oss-20b).
- ValidatedScope is the single source of truth.
- PitchDraft is supporting presentation context only.
- Confirmed/Modified requirements become committed scope.
- Rejected requirements are never capabilities.
- Unresolved requirements become open_items (never committed).
- No invented integrations, technologies, timelines, or guarantees.
- PARTIALLY_VALIDATED scopes are allowed to proceed.
- Final proposal structure must match ProposalDraft exactly.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import BadRequestError, Groq, RateLimitError

from src.schemas import (
    PitchDraft,
    ProposalDraft,
    ProposalStatus,
    ValidatedScope,
    extract_scope_open_items,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)

MAX_RETRIES = 3
BASE_RETRY_DELAY = 2
MAX_RETRY_DELAY = 10
MAX_COMPLETION_TOKENS = 2200

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured. "
        "Set the GROQ_API_KEY environment variable."
    )

client = Groq(api_key=API_KEY)


# ============================================================
# ENUM & TEXT HELPERS
# ============================================================

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


def _to_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


# ============================================================
# LANGUAGE SAFETY
# ============================================================

STRONG_CLAIM_REPLACEMENTS = {
    "100% accurate": "high-quality",
    "zero mistakes": "reduced errors",
    "error-free": "designed to reduce errors",
    "never fail": "designed for reliable operation",
    "never fails": "designed for reliable operation",
    "eliminates all manual work": "reduces manual work",
    "guaranteed bookings": "booking support",
    "guaranteed revenue": "revenue support",
    "guaranteed roi": "value-focused implementation",
    "real-time": "timely",
}

SAFE_LANGUAGE_REPLACEMENTS = {
    "seamlessly": "smoothly",
    "seamless": "streamlined",
    "effortlessly": "with a simple workflow",
    "flawlessly": "reliably",
    "instantly": "promptly",
    "instant": "prompt",
    "guaranteed": "intended",
    "guarantee": "aim",
    "always": "typically",
}


def _sanitize_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    for old, new in sorted(STRONG_CLAIM_REPLACEMENTS.items(), key=lambda x: len(x[0]), reverse=True):
        cleaned = re.sub(re.escape(old), new, cleaned, flags=re.IGNORECASE)
    for old, new in sorted(SAFE_LANGUAGE_REPLACEMENTS.items(), key=lambda x: len(x[0]), reverse=True):
        cleaned = re.sub(re.escape(old), new, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json_object(content: str) -> Dict[str, Any]:
    if not content:
        raise ValueError("LLM returned empty content.")
    text = content.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()
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
    raise ValueError(f"Could not parse valid JSON from output:\n{content}")


# ============================================================
# AUTHORITATIVE SCOPE BUILDER
# ============================================================

def _build_compact_payload(
    scope: ValidatedScope,
    pitch: Optional[PitchDraft] = None,
) -> str:
    confirmed = []
    unresolved = []

    for item in scope.confirmed_requirements:
        status = _enum_value(_safe_get(item, "status")).lower()
        orig = str(_safe_get(item, "original_requirement") or _safe_get(item, "requirement") or "").strip()
        final = str(_safe_get(item, "final_scope") or orig).strip()

        if status in ("confirmed", "modified") and final:
            confirmed.append(f"- {orig}: {final}")
        elif status == "unresolved":
            unresolved.append(f"- {orig} (pending confirmation)")
        elif status == "rejected":
            unresolved.append(f"- {orig} (explicitly excluded)")

    for u in scope.unresolved_items:
        issue = str(_safe_get(u, "issue") or "").strip()
        reason = str(_safe_get(u, "reason") or "").strip()
        if issue:
            unresolved.append(f"- {issue}: {reason}")

    lines = [
        f"BUSINESS_GOAL: {scope.business_goal}",
        f"TARGET_USERS: {', '.join(scope.target_users)}",
    ]

    if pitch:
        lines.append(f"PITCH: {_enum_value(_safe_get(pitch, 'headline'))}")

    lines.append("\nCONFIRMED SCOPE:")
    lines.extend(confirmed if confirmed else ["- Standard AI assistant workflow."])

    lines.append("\nOPEN_ITEMS:")
    lines.extend(unresolved if unresolved else ["- None"])

    lines.append("\nASSUMPTIONS:")
    lines.extend([f"- {a}" for a in scope.assumptions] if scope.assumptions else ["- Standard cooperation."])

    lines.append("\nBOUNDARIES:")
    lines.extend([f"- {b}" for b in scope.scope_boundaries] if scope.scope_boundaries else ["- Human escalation for unhandled inquiries."])

    return "\n".join(lines)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a senior proposal writer for a professional AI consultancy.

Generate a concise, professional client proposal grounded STRICTLY in the supplied scope.

RULES:
1. Only confirmed/modified requirements become committed scope.
2. Rejected requirements must appear in scope_exclusions, NEVER as features.
3. Unresolved items go into open_items, NEVER as confirmed capabilities.
4. SAFETY: For medical/legal/financial domains, explicitly include domain exclusions (e.g. no medical/legal advice).
5. Do NOT invent integrations, technologies, timelines, ROI, or guarantees.
6. Use careful language: "supports", "enables", "is designed to". Never "guarantees".

Return ONLY valid JSON:
{
  "title": "AI Solution Proposal",
  "executive_summary": "2-3 sentence overview",
  "business_goal": "Client objective",
  "target_users": ["Users"],
  "proposed_solution": "Solution description",
  "requirements": ["Key requirements"],
  "scope_inclusions": ["Confirmed deliverables"],
  "scope_exclusions": ["Out-of-scope items"],
  "assumptions": ["Baseline assumptions"],
  "open_items": ["Pending clarifications"],
  "implementation_approach": ["Phase 1: Setup", "Phase 2: Launch"],
  "integrations": ["Confirmed systems"],
  "security_and_safety": ["Human escalation", "Data privacy"],
  "deliverables": ["Configured assistant", "Training guide"],
  "success_metrics": ["Response time reduction"],
  "timeline": "Phase 1 (Weeks 1-2); Phase 2 (Weeks 3-4)",
  "next_steps": ["Approve scope", "Schedule kickoff"]
}
"""


# ============================================================
# OUTPUT NORMALIZATION
# ============================================================

def _normalize_proposal_output(
    data: Dict[str, Any],
    scope: ValidatedScope,
) -> ProposalDraft:
    # 1. Cleanly initialize exclusions list
    raw_exclusions = _to_list(data.get("scope_exclusions"))
    final_exclusions: List[str] = list(raw_exclusions)

    # 2. Cleanly deduplicate open items
    scope_open_items = extract_scope_open_items(scope)
    raw_open_items = _to_list(data.get("open_items"))
    
    seen_normalized = set()
    combined_open = []
    for item in (raw_open_items + scope_open_items):
        norm = re.sub(r"\s*\(pending confirmation\)\s*", "", item, flags=re.IGNORECASE).strip().lower()
        norm = re.sub(r"\s*—\s*final scope remains unresolved\.?\s*", "", norm, flags=re.IGNORECASE).strip()
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            combined_open.append(item.strip())

    # 3. Domain safety detection
    confirmed_req_texts = []
    for r in getattr(scope, "confirmed_requirements", []) or []:
        orig = _safe_get(r, "original_requirement") or _safe_get(r, "requirement") or ""
        final = _safe_get(r, "final_scope") or ""
        confirmed_req_texts.append(f"{orig} {final}")

    full_context = " ".join([
        str(data.get("title", "")),
        str(data.get("business_goal", "")),
        str(scope.business_goal),
        " ".join(scope.target_users or []),
        " ".join(confirmed_req_texts)
    ]).lower()

    # Medical guard
    if any(k in full_context for k in ["medical", "clinic", "patient", "dental", "doctor", "health", "diagnos", "prescri"]):
        medical_guard = "AI clinical diagnosis, medical treatment advice, and prescription issuance (escalated to clinic staff)"
        if not any("medical" in e.lower() or "diagnosis" in e.lower() for e in final_exclusions):
            final_exclusions.append(medical_guard)

    # Legal guard
    if any(k in full_context for k in ["legal", "law", "attorney", "immigration", "lawyer", "counsel"]):
        legal_guard = "Formal legal advice, legal representation, and case strategy decisions (must be provided directly by a licensed attorney)"
        if not any("legal" in e.lower() or "attorney" in e.lower() or "lawyer" in e.lower() for e in final_exclusions):
            final_exclusions.append(legal_guard)

    # Financial guard
    if any(k in full_context for k in ["financial", "accounting", "tax", "investment", "wealth"]):
        fin_guard = "Fiduciary financial advice, formal tax guidance, and investment guarantees"
        if not any("financial" in e.lower() or "tax" in e.lower() for e in final_exclusions):
            final_exclusions.append(fin_guard)

    return ProposalDraft(
        title=str(data.get("title") or "AI Solution Proposal").strip(),
        executive_summary=str(data.get("executive_summary") or "Executive Summary").strip(),
        business_goal=str(data.get("business_goal") or scope.business_goal).strip(),
        target_users=_to_list(data.get("target_users")) or scope.target_users,
        proposed_solution=str(data.get("proposed_solution") or "AI Assistant Solution").strip(),
        requirements=_to_list(data.get("requirements")),
        scope_inclusions=_to_list(data.get("scope_inclusions") or data.get("deliverables")),
        scope_exclusions=final_exclusions,
        assumptions=_to_list(data.get("assumptions")) or scope.assumptions,
        open_items=combined_open,
        implementation_approach=_to_list(data.get("implementation_approach")),
        integrations=_to_list(data.get("integrations")),
        security_and_safety=_to_list(data.get("security_and_safety")),
        deliverables=_to_list(data.get("deliverables")),
        success_metrics=_to_list(data.get("success_metrics")),
        timeline=str(data.get("timeline") or "Phase 1 (Weeks 1-2); Phase 2 (Weeks 3-4)").strip(),
        next_steps=_to_list(data.get("next_steps")),
        status=ProposalStatus.READY_FOR_CLIENT,
    )


# ============================================================
# PROPOSAL SANITIZATION
# ============================================================

def sanitize_proposal_language(proposal: ProposalDraft) -> ProposalDraft:
    proposal.title = _sanitize_text(proposal.title)
    proposal.executive_summary = _sanitize_text(proposal.executive_summary)
    proposal.business_goal = _sanitize_text(proposal.business_goal)
    proposal.proposed_solution = _sanitize_text(proposal.proposed_solution)
    proposal.requirements = [_sanitize_text(i) for i in proposal.requirements]
    proposal.scope_inclusions = [_sanitize_text(i) for i in proposal.scope_inclusions]
    proposal.scope_exclusions = [_sanitize_text(i) for i in proposal.scope_exclusions]
    proposal.assumptions = [_sanitize_text(i) for i in proposal.assumptions]
    proposal.open_items = [_sanitize_text(i) for i in proposal.open_items]
    proposal.implementation_approach = [_sanitize_text(i) for i in proposal.implementation_approach]
    proposal.integrations = [_sanitize_text(i) for i in proposal.integrations]
    proposal.security_and_safety = [_sanitize_text(i) for i in proposal.security_and_safety]
    proposal.deliverables = [_sanitize_text(i) for i in proposal.deliverables]
    proposal.success_metrics = [_sanitize_text(i) for i in proposal.success_metrics]
    proposal.timeline = _sanitize_text(proposal.timeline)
    proposal.next_steps = [_sanitize_text(i) for i in proposal.next_steps]
    return proposal


# ============================================================
# REJECTED REQUIREMENT LEAKAGE CHECK
# ============================================================

def _validate_no_rejected_leakage(
    proposal: ProposalDraft,
    scope: ValidatedScope,
) -> None:
    proposal_text = " ".join([
        proposal.title, proposal.executive_summary,
        proposal.proposed_solution,
        " ".join(proposal.scope_inclusions),
        " ".join(proposal.deliverables),
    ]).lower()

    for item in scope.confirmed_requirements:
        status = _enum_value(_safe_get(item, "status")).lower()
        if status != "rejected":
            continue
        orig = str(_safe_get(item, "original_requirement") or "").strip().lower()
        if len(orig) >= 10 and orig in proposal_text:
            raise RuntimeError(
                f"Rejected requirement leaked into proposal: '{orig}'"
            )


# ============================================================
# MAIN GENERATOR (POLYMORPHIC — pitch is OPTIONAL)
# ============================================================

def generate_proposal(*args, **kwargs) -> ProposalDraft:
    scope: Optional[ValidatedScope] = (
        kwargs.get("scope")
        or kwargs.get("validated_scope")
    )
    pitch: Optional[PitchDraft] = (
        kwargs.get("pitch")
        or kwargs.get("pitch_draft")
    )

    for arg in args:
        if isinstance(arg, ValidatedScope) or hasattr(arg, "confirmed_requirements"):
            scope = arg
        elif isinstance(arg, PitchDraft) or (hasattr(arg, "headline") and hasattr(arg, "pitch")):
            pitch = arg

    if scope is None:
        raise ValueError("generate_proposal: ValidatedScope is required.")

    scope_status = _enum_value(scope.overall_scope_status).lower()
    if scope_status == "needs_more_discovery":
        raise RuntimeError(
            "Proposal generation blocked: scope needs more discovery."
        )

    if not scope.confirmed_requirements:
        raise RuntimeError(
            "Proposal generation blocked: no confirmed requirements."
        )

    compact_payload = _build_compact_payload(scope, pitch)
    user_prompt = f"VALIDATED SCOPE:\n{compact_payload}\n\nGenerate the complete proposal JSON."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            # --- Attempt 1: Strict JSON mode ---
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"
            parsed = _extract_json_object(raw)
            proposal = _normalize_proposal_output(parsed, scope)
            proposal = sanitize_proposal_language(proposal)
            _validate_no_rejected_leakage(proposal, scope)
            return proposal

        except (BadRequestError, Exception) as exc:
            last_error = exc
            err_str = str(exc)

            # --- Attempt 2: Fallback raw text mode ---
            if "json_validate_failed" in err_str or isinstance(exc, BadRequestError):
                try:
                    fb_response = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT.strip() + "\nOutput MUST be valid JSON."},
                            {"role": "user", "content": user_prompt.strip()},
                        ],
                        temperature=0.1,
                        max_completion_tokens=MAX_COMPLETION_TOKENS,
                    )
                    raw = fb_response.choices[0].message.content or "{}"
                    parsed = _extract_json_object(raw)
                    proposal = _normalize_proposal_output(parsed, scope)
                    proposal = sanitize_proposal_language(proposal)
                    _validate_no_rejected_leakage(proposal, scope)
                    return proposal
                except Exception as fb_exc:
                    last_error = fb_exc

            if isinstance(exc, RateLimitError):
                time.sleep(BASE_RETRY_DELAY * (attempt + 1))
            else:
                time.sleep(BASE_RETRY_DELAY)

    raise RuntimeError(
        f"Proposal generation failed after {MAX_RETRIES} attempts: {last_error}"
    )


# ============================================================
# BACKWARD-COMPATIBLE ALIASES
# ============================================================

def generate_proposal_draft(*args, **kwargs) -> ProposalDraft:
    return generate_proposal(*args, **kwargs)


def create_proposal(*args, **kwargs) -> ProposalDraft:
    return generate_proposal(*args, **kwargs)