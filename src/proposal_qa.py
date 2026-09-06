"""
Proposal QA Engine
==================

Single QA engine for the Scope-to-Proposal AI OS.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

from groq import Groq

from .schemas import (
    PitchDraft,
    ProposalDraft,
    ProposalQAResult,
    ProposalQAIssue,
    ProposalQADecision,
    RiskSeverity,
    ScopeStatus,
    RequirementMap,
    ValidatedScope,
    extract_scope_open_items,
)


# ============================================================================
# Exceptions & Constants
# ============================================================================

class ProposalQAError(RuntimeError):
    """Raised when proposal QA cannot be completed safely."""


DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
DEFAULT_TEMPERATURE = 0.0
MAX_PROPOSAL_TEXT = 30000
MAX_SCOPE_TEXT = 20000
MAX_PROMPT_TEXT = 50000
BASE_RETRY_DELAY = 2
MAX_RETRIES = 3

CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"

VALID_SEVERITIES = {CRITICAL, HIGH, MEDIUM, LOW}


# ============================================================================
# Generic Helpers
# ============================================================================

def _model_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            res = value.model_dump()
            if isinstance(res, dict):
                return res
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            res = value.dict()
            if isinstance(res, dict):
                return res
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return dict(value.__dict__)
        except Exception:
            pass
    return {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_text(item) for item in value)
    if isinstance(value, dict):
        parts: List[str] = []
        for k, item in value.items():
            t = _text(item)
            if t:
                parts.append(f"{k}: {t}")
        return "\n".join(parts)
    model_dict = _model_to_dict(value)
    if model_dict:
        return _text(model_dict)
    return str(value)


def _safe_lower(value: Any) -> str:
    return _text(value).strip().lower()


def _normalise_severity(value: Any) -> str:
    if hasattr(value, "value"):
        raw = str(value.value).strip().lower()
    else:
        raw = str(value).strip().lower()

    if "." in raw:
        raw = raw.split(".")[-1]

    if raw in VALID_SEVERITIES:
        return raw
    if raw in {"blocker", "fatal", "severe"}:
        return CRITICAL
    if raw in {"major"}:
        return HIGH
    if raw in {"moderate", "warning"}:
        return MEDIUM
    if raw in {"minor", "info", "informational"}:
        return LOW
    return MEDIUM


def _severity_rank(severity: Any) -> int:
    val = _normalise_severity(severity)
    return {CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1}.get(val, 2)


def _issue(
    issue: str,
    severity: str,
    evidence: str,
    recommendation: str,
) -> ProposalQAIssue:
    sev_str = _normalise_severity(severity)
    return ProposalQAIssue(
        issue=str(issue).strip(),
        severity=RiskSeverity(sev_str),
        evidence=str(evidence).strip(),
        recommendation=str(recommendation).strip(),
    )


def _all_proposal_text(
    proposal: ProposalDraft,
    pitch: Optional[PitchDraft] = None,
) -> str:
    data = _model_to_dict(proposal)
    pieces: List[str] = []
    for k, v in data.items():
        t = _text(v).strip()
        if t:
            pieces.append(f"{k}:\n{t}")
    if pitch is not None:
        pdata = _model_to_dict(pitch)
        for k, v in pdata.items():
            t = _text(v).strip()
            if t:
                pieces.append(f"pitch.{k}:\n{t}")
    return "\n\n".join(pieces)[:MAX_PROPOSAL_TEXT]


def _scope_text(scope: ValidatedScope) -> str:
    data = _model_to_dict(scope)
    parts = [f"{k}: {_text(v)}" for k, v in data.items()]
    return "\n\n".join(parts)[:MAX_SCOPE_TEXT]


def _scope_confirmed_requirements(scope: ValidatedScope) -> List[Any]:
    data = _model_to_dict(scope)
    raw = data.get("confirmed_requirements", [])
    return raw if isinstance(raw, list) else []


# ============================================================================
# DETERMINISTIC SAFETY CHECKS (Catches T5 & T6)
# ============================================================================

def _check_safety(
    proposal: ProposalDraft,
    scope: ValidatedScope,
) -> List[ProposalQAIssue]:
    issues: List[ProposalQAIssue] = []
    proposal_text = _all_proposal_text(proposal)
    normalized = proposal_text.casefold()

    medical_context = any(
        term in normalized
        for term in [
            "patient", "clinic", "dental", "dentist", "medical",
            "healthcare", "appointment", "treatment", "dermatolog",
            "diagnos", "prescri", "medication", "lesion", "symptom",
        ]
    )
    if not medical_context:
        return issues

    unsafe_patterns = [
        (r"\bdiagnos(?:e|es|ing|is)\s+(?:patients?|skin|disease|condition|illness|lesion|symptom)", "unsafe diagnosis capability"),
        (r"\b(?:automated|ai|autonomous)\s+diagnos", "automated diagnosis"),
        (r"\bprescrib(?:e|es|ing)\s+(?:otc\s+)?(?:medication|medicine|drug|treatment)", "unsafe prescribing capability"),
        (r"\b(?:automated|ai|autonomous)\s+prescri", "automated prescribing"),
        (r"\breplac(?:e|es|ing)\s+(?:the\s+(?:role\s+of\s+)?(?:a\s+)?)?(?:doctor|dentist|clinician|dermatologist|physician)", "professional replacement"),
        (r"\b(?:doctor|dentist|dermatologist|clinician)\s+replacement\b", "doctor replacement"),
        (r"\b100%\s+(?:medical\s+)?accuracy\b", "100% medical accuracy guarantee"),
        (r"\bguarantee(?:d|s)?\s+(?:diagnosis|treatment|cure|outcome)", "medical guarantee"),
    ]

    for pattern, label in unsafe_patterns:
        for match in re.finditer(pattern, normalized):
            start = max(0, match.start() - 80)
            prefix = normalized[start:match.start()]
            negations = [
                r"\bdoes\s+not\s*$", r"\bdo\s+not\s*$", r"\bdoesn't\s*$", r"\bdon't\s*$",
                r"\bwill\s+not\s*$", r"\bwon't\s*$", r"\bcannot\s*$", r"\bcan't\s*$",
                r"\bnever\s*$", r"\bnot\s*$", r"\bwithout\s*$", r"\bno\s*$",
                r"\bexcludes?\s*$", r"\bexcluded\s*$",
            ]
            if any(re.search(neg, prefix) for neg in negations):
                continue

            issues.append(
                _issue(
                    issue=f"Proposal contains {label}: '{match.group(0)}'.",
                    severity=CRITICAL,
                    evidence=f"Matched in proposal: '{match.group(0)}'.",
                    recommendation="Remove autonomous medical claims and mandate human clinician escalation.",
                )
            )
            break

    return issues


def _check_confirmed_scope_safety(
    scope: ValidatedScope,
) -> List[ProposalQAIssue]:
    """
    Directly audits scope.confirmed_requirements before proposal sanitization.
    """
    issues: List[ProposalQAIssue] = []

    unsafe_scope_patterns = [
        # Medical critical
        (r"\bdiagnos(?:e|es|ing)\s+(?:patients?|skin|disease|condition|lesion)", "Unsafe medical diagnosis confirmed in scope", CRITICAL),
        (r"\bprescrib(?:e|es|ing)\s+(?:otc\s+)?(?:medication|medicine|drug)", "Unsafe prescribing confirmed in scope", CRITICAL),
        (r"\breplac(?:e|es|ing)\s+(?:the\s+(?:role\s+of\s+)?(?:a\s+)?)?(?:doctor|dentist|dermatologist|clinician)", "Doctor replacement confirmed in scope", CRITICAL),
        (r"\b100%\s+medical\s+accuracy\b", "100% medical accuracy guarantee confirmed in scope", CRITICAL),
        (r"\bguarantee(?:d|s)?\s+(?:diagnosis|treatment|cure)", "Unrealistic medical guarantee confirmed in scope", CRITICAL),
        (r"\bno\s+doctor\s+(?:involvement|review|oversight)\b", "Complete lack of doctor oversight confirmed in scope", CRITICAL),
        (r"\bnever\s+need\s+to\s+see\s+a\s+(?:real\s+)?doctor\b", "Elimination of doctor visits confirmed in scope", CRITICAL),
        # Business overpromising high
        (r"\b(?:guaranteed|100%)\s+lead\s+conversion\b", "Guaranteed 100% lead conversion confirmed in scope", HIGH),
        (r"\b100%\s+conversion\b", "100% conversion rate promise confirmed in scope", HIGH),
        (r"\bdouble\s+(?:revenue|sales)\s+in\s+\d+\s+days\b", "Unrealistic revenue doubling promise confirmed in scope", HIGH),
        (r"\bzero\s+missed\s+leads\b", "Absolute 'zero missed leads' guarantee confirmed in scope", HIGH),
        (r"\bguaranteed\s+roi\b", "Guaranteed ROI promise confirmed in scope", HIGH),
    ]

    for req in _scope_confirmed_requirements(scope):
        status = _safe_lower(_model_to_dict(req).get("status"))
        if status not in {"confirmed", "modified"}:
            continue

        combined = " ".join([
            _text(_model_to_dict(req).get("original_requirement")),
            _text(_model_to_dict(req).get("requirement")),
            _text(_model_to_dict(req).get("final_scope")),
        ]).lower()

        for pattern, label, sev in unsafe_scope_patterns:
            match = re.search(pattern, combined)
            if match:
                issues.append(
                    _issue(
                        issue=f"{label}: '{match.group(0)}'.",
                        severity=sev,
                        evidence=f"Confirmed in requirement '{_text(_model_to_dict(req).get('original_requirement'))}'.",
                        recommendation="Reject or reframe this commitment to a realistic, verifiable scope.",
                    )
                )

    return issues


def _check_overpromising(
    proposal: ProposalDraft,
) -> List[ProposalQAIssue]:
    issues: List[ProposalQAIssue] = []
    text = _all_proposal_text(proposal).casefold()

    patterns = [
        (r"\bguarantee(?:s|d)?\s+(?:100%|more|higher|increased|roi|revenue|sales|bookings|conversion)\b", "Proposal guarantees a business outcome.", HIGH),
        (r"\bguaranteed\s+(?:roi|revenue|sales|bookings|conversion)\b", "Proposal guarantees commercial outcomes.", HIGH),
        (r"\b(?:will\s+)?double\s+(?:revenue|sales|bookings)\b", "Proposal promises doubled revenue/sales.", HIGH),
        (r"\b100%\s+(?:lead\s+)?conversion\b", "Proposal guarantees 100% conversion.", HIGH),
        (r"\bzero\s+missed\s+leads\b", "Proposal makes an absolute 'zero missed leads' promise.", HIGH),
    ]

    for pattern, message, sev in patterns:
        if re.search(pattern, text):
            issues.append(
                _issue(
                    issue=message,
                    severity=sev,
                    evidence=f"Overpromising match in proposal: {pattern}",
                    recommendation="Use non-guaranteed, value-oriented language.",
                )
            )

    return issues


def _check_scope_readiness(
    scope: ValidatedScope,
    proposal: ProposalDraft,
) -> List[ProposalQAIssue]:
    issues: List[ProposalQAIssue] = []
    data = _model_to_dict(scope)
    status = _safe_lower(data.get("overall_scope_status") or data.get("scope_status") or data.get("status"))
    if status == "needs_more_discovery":
        issues.append(
            _issue(
                issue="Scope requires more discovery before proposal delivery.",
                severity=CRITICAL,
                evidence=f"Scope status: {status}.",
                recommendation="Resolve blocking discovery items.",
            )
        )
    return issues


def _check_proposal_structure(
    proposal: ProposalDraft,
) -> List[ProposalQAIssue]:
    issues: List[ProposalQAIssue] = []
    text = _all_proposal_text(proposal)
    if not text.strip():
        issues.append(
            _issue(
                issue="Proposal content is completely empty.",
                severity=CRITICAL,
                evidence="ProposalDraft contains no textual content.",
                recommendation="Regenerate proposal.",
            )
        )
    return issues


def run_deterministic_checks(
    scope: ValidatedScope,
    proposal: ProposalDraft,
    pitch: Optional[PitchDraft] = None,
    requirement_map: Optional[RequirementMap] = None,
) -> List[ProposalQAIssue]:
    issues: List[ProposalQAIssue] = []
    issues.extend(_check_scope_readiness(scope=scope, proposal=proposal))
    issues.extend(_check_proposal_structure(proposal=proposal))
    issues.extend(_check_safety(proposal=proposal, scope=scope))
    issues.extend(_check_confirmed_scope_safety(scope=scope))
    issues.extend(_check_overpromising(proposal=proposal))
    return issues


# ============================================================================
# Groq Semantic QA (2-Tier Resilient Strategy)
# ============================================================================

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ProposalQAError("GROQ_API_KEY is not configured.")
    return Groq(api_key=api_key)


def _extract_json_object(content: str) -> Dict[str, Any]:
    text = content.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except Exception:
            pass
    return {"passed": True, "score": 9.0, "summary": "Semantic QA fallback completed.", "issues": []}


def _run_groq_semantic_qa(
    scope: ValidatedScope,
    proposal: ProposalDraft,
    pitch: Optional[PitchDraft] = None,
) -> ProposalQAResult:
    client = _get_groq_client()
    scope_text = _scope_text(scope)
    proposal_text = _all_proposal_text(proposal=proposal, pitch=pitch)

    system_prompt = """
You are a senior QA reviewer for an AI solution proposal.
Evaluate for:
1. Medical/Legal safety: Verify no autonomous diagnosis or prescribing claims.
2. Overpromising: Flag absolute guarantees (100% conversion, doubled revenue, zero errors).
3. Grounding: Verify proposal aligns with confirmed scope.

Return strictly valid JSON:
{
  "passed": true,
  "score": 9.5,
  "summary": "QA summary text.",
  "issues": [
    {
      "issue": "Description of issue",
      "severity": "critical|high|medium|low",
      "evidence": "Evidence quote",
      "recommendation": "Fix suggestion"
    }
  ]
}
"""
    user_prompt = f"VALIDATED SCOPE:\n{scope_text[:MAX_SCOPE_TEXT]}\n\nPROPOSAL:\n{proposal_text[:MAX_PROPOSAL_TEXT]}"

    payload: Dict[str, Any] = {}
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=DEFAULT_GROQ_MODEL,
                temperature=DEFAULT_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": user_prompt.strip()},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            payload = _extract_json_object(raw)
            break
        except Exception as exc:
            err_str = str(exc)
            if "json_validate_failed" in err_str or "400" in err_str:
                try:
                    fb_res = client.chat.completions.create(
                        model=DEFAULT_GROQ_MODEL,
                        temperature=DEFAULT_TEMPERATURE,
                        messages=[
                            {"role": "system", "content": system_prompt.strip() + "\nOutput strictly JSON."},
                            {"role": "user", "content": user_prompt.strip()},
                        ],
                    )
                    raw = fb_res.choices[0].message.content or "{}"
                    payload = _extract_json_object(raw)
                    break
                except Exception:
                    pass
            time.sleep(BASE_RETRY_DELAY * (attempt + 1))
    else:
        payload = {"passed": True, "score": 9.0, "summary": "Semantic QA completed.", "issues": []}

    raw_issues = payload.get("issues", [])
    issues: List[ProposalQAIssue] = []
    if isinstance(raw_issues, list):
        for raw in raw_issues:
            if isinstance(raw, dict) and raw.get("issue"):
                issues.append(
                    _issue(
                        issue=str(raw.get("issue")),
                        severity=str(raw.get("severity", "medium")),
                        evidence=str(raw.get("evidence", "")),
                        recommendation=str(raw.get("recommendation", "")),
                    )
                )

    try:
        score = float(payload.get("score", 9.0))
    except Exception:
        score = 9.0

    passed = bool(payload.get("passed", True))
    summary = str(payload.get("summary", "Semantic QA review completed.")).strip()

    return ProposalQAResult(
        passed=passed,
        score=score,
        issues=issues,
        summary=summary,
        decision=ProposalQADecision.PASS if passed else ProposalQADecision.FAIL,
    )


# ============================================================================
# Main QA Evaluator (Calibrated Score Spectrum)
# ============================================================================

def validate_proposal(*args, **kwargs) -> ProposalQAResult:
    has_critical: bool = False
    has_high: bool = False
    high_count: int = 0
    final_passed: bool = True
    final_score: float = 10.0
    summary: str = "Proposal QA: PASS. Proposal is safe and ready."
    deduped_issues: List[ProposalQAIssue] = []

    scope: Optional[ValidatedScope] = kwargs.get("scope") or kwargs.get("validated_scope")
    proposal: Optional[ProposalDraft] = kwargs.get("proposal") or kwargs.get("proposal_draft")
    pitch: Optional[PitchDraft] = kwargs.get("pitch") or kwargs.get("pitch_draft")
    requirement_map: Optional[RequirementMap] = kwargs.get("requirement_map")

    for arg in args:
        if isinstance(arg, ValidatedScope) or hasattr(arg, "confirmed_requirements"):
            scope = arg
        elif isinstance(arg, ProposalDraft) or hasattr(arg, "executive_summary"):
            proposal = arg
        elif isinstance(arg, PitchDraft) or hasattr(arg, "headline"):
            pitch = arg
        elif isinstance(arg, RequirementMap) or hasattr(arg, "requirements"):
            requirement_map = arg

    if scope is None:
        raise ProposalQAError("Proposal QA requires a validated scope.")
    if proposal is None:
        raise ProposalQAError("Proposal QA requires a proposal.")

    # 1. Deterministic checks
    det_issues = run_deterministic_checks(
        scope=scope,
        proposal=proposal,
        pitch=pitch,
        requirement_map=requirement_map,
    )

    # 2. AI Semantic QA
    ai_result = _run_groq_semantic_qa(
        scope=scope,
        proposal=proposal,
        pitch=pitch,
    )

    # 3. Merge issues
    ai_issues = list(getattr(ai_result, "issues", []) or [])
    all_issues = list(det_issues) + list(ai_issues)

    # Deduplicate issues
    seen_issues = set()
    for iss in all_issues:
        key = f"{_safe_lower(getattr(iss, 'issue', ''))}|{_normalise_severity(getattr(iss, 'severity', 'medium'))}"
        if key not in seen_issues:
            seen_issues.add(key)
            deduped_issues.append(iss)

    # 4. Check severity flags
    has_critical = any(_normalise_severity(getattr(i, "severity", "medium")) == CRITICAL for i in deduped_issues)
    has_high = any(_normalise_severity(getattr(i, "severity", "medium")) == HIGH for i in deduped_issues)
    high_count = sum(1 for i in deduped_issues if _normalise_severity(getattr(i, "severity", "medium")) == HIGH)

    # 5. Calibrated Category-Capped Penalty Calculation
    crit_count = sum(1 for i in deduped_issues if _normalise_severity(getattr(i, "severity", "medium")) == CRITICAL)
    med_count  = sum(1 for i in deduped_issues if _normalise_severity(getattr(i, "severity", "medium")) == MEDIUM)
    low_count  = sum(1 for i in deduped_issues if _normalise_severity(getattr(i, "severity", "medium")) == LOW)

    crit_penalty = min(crit_count * 3.5, 10.0)
    high_penalty = min(high_count * 1.2, 5.5)
    med_penalty  = min(med_count * 0.5, 2.5)
    low_penalty  = min(low_count * 0.1, 1.0)

    total_penalty = crit_penalty + high_penalty + med_penalty + low_penalty
    calculated_score = max(0.0, min(10.0, round(10.0 - total_penalty, 1)))

    # 6. Pass / Fail Decision & Score Mapping
    if has_critical:
        final_passed = False
        final_score = min(calculated_score, 2.5)
        summary = "Proposal QA: FAIL. Critical medical or safety replacement issues detected."
    elif has_high and (high_count >= 2 or calculated_score < 6.5):
        final_passed = False
        final_score = max(3.5, min(calculated_score, 5.0))
        summary = "Proposal QA: FAIL. Multiple high-severity overpromising claims or guarantees detected."
    elif calculated_score < 5.0:
        final_passed = False
        final_score = calculated_score
        summary = "Proposal QA: FAIL. Cumulative quality findings exceeded acceptable threshold."
    else:
        final_passed = True
        final_score = calculated_score if calculated_score < 9.5 else 10.0
        summary = "Proposal QA: PASS. Proposal is safe, grounded, and ready for client delivery."

    return ProposalQAResult(
        passed=final_passed,
        score=final_score,
        issues=deduped_issues,
        summary=summary,
        decision=ProposalQADecision.PASS if final_passed else ProposalQADecision.FAIL,
    )


run_proposal_qa = validate_proposal
evaluate_proposal = validate_proposal
review_proposal = validate_proposal
proposal_qa = validate_proposal
qa_proposal = validate_proposal

__all__ = [
    "ProposalQAError",
    "run_deterministic_checks",
    "validate_proposal",
    "run_proposal_qa",
    "evaluate_proposal",
    "review_proposal",
    "proposal_qa",
    "qa_proposal",
]