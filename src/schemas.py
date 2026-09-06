"""
schemas.py

Core Pydantic schemas and validation contracts for the
Scope-to-Proposal AI OS.

Architecture:

Client Request
    ↓
Requirement Extraction
    ↓
Risk Analysis
    ↓
One Discovery Call
    ↓
Scope Validation
    ↓
Proposal
    ↓
One Proposal QA
    ↓
PASS / FAIL
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, model_validator


# ============================================================================
# BASE CONFIG
# ============================================================================

class StrictBaseModel(BaseModel):
    """
    Shared strict configuration.

    - extra="forbid":
        Prevents AI from silently introducing unsupported fields.

    - validate_assignment=True:
        Keeps validation active if a field is modified after model creation.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


# ============================================================================
# ENUMS
# ============================================================================

class RequirementCategory(str, Enum):
    CHATBOT = "Chatbot"
    LEAD_QUALIFICATION = "Lead Qualification"
    APPOINTMENT_BOOKING = "Appointment Booking"
    INTEGRATION = "Integration"
    AUTOMATION = "Automation"
    KNOWLEDGE_BASE = "Knowledge Base"
    NOTIFICATION = "Notification"
    ANALYTICS = "Analytics"
    SECURITY = "Security"
    OTHER = "Other"


class RiskType(str, Enum):
    AMBIGUOUS = "ambiguous"
    MISSING_INFORMATION = "missing_information"
    TECHNICAL = "technical"
    INTEGRATION = "integration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    SCOPE = "scope"
    DEPENDENCY = "dependency"
    FEASIBILITY = "feasibility"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationStatusType(str, Enum):
    CONFIRMED = "confirmed"
    MODIFIED = "modified"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class ScopeStatus(str, Enum):
    NEEDS_MORE_DISCOVERY = "needs_more_discovery"
    PARTIALLY_VALIDATED = "partially_validated"
    READY_FOR_PROPOSAL = "ready_for_proposal"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    READY_FOR_CLIENT = "ready_for_client"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


class ProposalQADecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


# ============================================================================
# CATEGORY NORMALIZATION HELPER
# ============================================================================

_CATEGORY_ALIASES: Dict[str, RequirementCategory] = {
    "chatbot": RequirementCategory.CHATBOT,
    "chat": RequirementCategory.CHATBOT,
    "conversational": RequirementCategory.CHATBOT,
    "assistant": RequirementCategory.CHATBOT,
    "lead_qualification": RequirementCategory.LEAD_QUALIFICATION,
    "lead qualification": RequirementCategory.LEAD_QUALIFICATION,
    "lead": RequirementCategory.LEAD_QUALIFICATION,
    "qualification": RequirementCategory.LEAD_QUALIFICATION,
    "appointment_booking": RequirementCategory.APPOINTMENT_BOOKING,
    "appointment booking": RequirementCategory.APPOINTMENT_BOOKING,
    "appointment": RequirementCategory.APPOINTMENT_BOOKING,
    "booking": RequirementCategory.APPOINTMENT_BOOKING,
    "integration": RequirementCategory.INTEGRATION,
    "integrations": RequirementCategory.INTEGRATION,
    "automation": RequirementCategory.AUTOMATION,
    "knowledge_base": RequirementCategory.KNOWLEDGE_BASE,
    "knowledge base": RequirementCategory.KNOWLEDGE_BASE,
    "notification": RequirementCategory.NOTIFICATION,
    "analytics": RequirementCategory.ANALYTICS,
    "security": RequirementCategory.SECURITY,
    "compliance": RequirementCategory.SECURITY,
    "other": RequirementCategory.OTHER,
    "functional": RequirementCategory.OTHER,
    "technical": RequirementCategory.OTHER,
}


def _normalize_category(value: Any) -> str:
    if isinstance(value, RequirementCategory):
        return value.value
    if not isinstance(value, str) or not value.strip():
        return RequirementCategory.OTHER.value
    normalized = value.strip().lower()
    if normalized in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[normalized].value
    for member in RequirementCategory:
        if member.value.lower() == normalized:
            return member.value
    return RequirementCategory.OTHER.value


# ============================================================================
# REQUIREMENT EXTRACTION
# ============================================================================

class Requirement(StrictBaseModel):
    requirement_id: str = Field(..., min_length=1)
    requirement: str = Field(..., min_length=1)
    category: RequirementCategory = Field(default=RequirementCategory.OTHER)
    source: str = Field(default="client_stated", min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_level: RiskSeverity = Field(default=RiskSeverity.LOW)

    @model_validator(mode="before")
    @classmethod
    def normalize_requirement_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "category" in data:
            data["category"] = _normalize_category(data["category"])
        if "risk_level" in data:
            raw_risk = str(data["risk_level"]).strip().lower()
            if raw_risk not in {"low", "medium", "high", "critical"}:
                data["risk_level"] = "medium"
        if "source" in data:
            raw_source = str(data["source"]).strip().lower()
            if raw_source not in {"client_stated", "inferred"}:
                data["source"] = "client_stated"
        if "confidence" in data:
            try:
                data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
            except (TypeError, ValueError):
                data["confidence"] = 0.5
        return data


class RequirementMap(StrictBaseModel):
    business_goal: str = Field(..., min_length=1)
    target_users: List[str] = Field(default_factory=list)
    requirements: List[Requirement] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_map_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for wrapper_key in ("requirement_map", "data", "result", "output"):
            if wrapper_key in data and isinstance(data[wrapper_key], dict):
                data = data[wrapper_key]
                break
        goal = data.get("business_goal")
        if goal is None or (isinstance(goal, str) and not goal.strip()):
            data["business_goal"] = "Not explicitly stated"
        users = data.get("target_users")
        if users is None:
            data["target_users"] = []
        elif isinstance(users, str):
            data["target_users"] = [u.strip() for u in users.split(",") if u.strip()] if users.strip() else []
        elif not isinstance(users, list):
            data["target_users"] = [str(users)]
        return data

    @model_validator(mode="after")
    def validate_requirements(self) -> "RequirementMap":
        if not self.requirements:
            raise ValueError("RequirementMap must contain at least one requirement.")
        requirement_ids = [item.requirement_id.strip() for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("Requirement IDs must be unique.")
        return self


# ============================================================================
# RISK ANALYSIS
# ============================================================================

class Risk(StrictBaseModel):
    risk_id: str = Field(..., min_length=1)
    requirement_id: str = Field(..., min_length=1)
    issue: str = Field(..., min_length=1)
    type: RiskType = Field(default=RiskType.AMBIGUOUS)
    severity: RiskSeverity = Field(default=RiskSeverity.MEDIUM)
    evidence: str = Field(default="")
    impact: str = Field(default="")
    needs_confirmation: bool = Field(default=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_risk_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "type" in data:
            raw_type = str(data["type"]).strip().lower()
            valid_types = {member.value for member in RiskType}
            if raw_type not in valid_types:
                data["type"] = RiskType.AMBIGUOUS.value
        if "severity" in data:
            raw_sev = str(data["severity"]).strip().lower()
            valid_sevs = {"low", "medium", "high", "critical"}
            if raw_sev not in valid_sevs:
                data["severity"] = "medium"
        return data


# ============================================================================
# DISCOVERY
# ============================================================================

class DiscoveryQuestion(StrictBaseModel):
    question_id: str = Field(..., min_length=1)
    risk_id: str = Field(..., min_length=1)
    requirement_id: str = Field(..., min_length=1)
    requirement: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    why_asking: str = Field(..., min_length=1)


class DiscoveryQuestionSet(StrictBaseModel):
    questions: List[DiscoveryQuestion] = Field(default_factory=list)


# ============================================================================
# SCOPE VALIDATION
# ============================================================================

class ValidationStatus(StrictBaseModel):
    requirement: str = Field(..., min_length=1)
    original_requirement: str = Field(..., min_length=1)
    status: ValidationStatusType
    final_scope: str = Field(default="")
    client_evidence: str = Field(default="")
    notes: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def normalize_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "status" in data:
            raw = str(data["status"]).strip().lower()
            valid = {member.value for member in ValidationStatusType}
            if raw not in valid:
                data["status"] = ValidationStatusType.UNRESOLVED.value
        return data

    @model_validator(mode="after")
    def validate_status_consistency(self) -> "ValidationStatus":
        if self.status in {ValidationStatusType.CONFIRMED, ValidationStatusType.MODIFIED}:
            if not self.final_scope.strip():
                # Provide safe fallback rather than hard crashing
                self.final_scope = self.requirement or self.original_requirement
        return self


class UnresolvedItem(StrictBaseModel):
    issue: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    required_for: str = Field(..., min_length=1)
    priority: RiskSeverity = Field(default=RiskSeverity.MEDIUM)


class ValidatedScope(StrictBaseModel):
    business_goal: str = Field(..., min_length=1)
    target_users: List[str] = Field(default_factory=list)
    confirmed_requirements: List[ValidationStatus] = Field(default_factory=list)
    scope_boundaries: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unresolved_items: List[UnresolvedItem] = Field(default_factory=list)
    overall_scope_status: ScopeStatus

    @property
    def is_ready_for_proposal(self) -> bool:
        return self.overall_scope_status in {
            ScopeStatus.READY_FOR_PROPOSAL,
            ScopeStatus.PARTIALLY_VALIDATED,
        }


# # ============================================================================
# PITCH (WITH AUTO-NORMALIZING & BACKWARD COMPATIBILITY PROPERTIES)
# ============================================================================

class PitchDraft(StrictBaseModel):
    headline: str = Field(..., min_length=1)
    pitch: str = Field(..., min_length=1)
    value_points: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

    # --- Backward-Compatibility Properties ---
    @property
    def title(self) -> str:
        return self.headline

    @title.setter
    def title(self, value: str) -> None:
        self.headline = value

    @property
    def opening(self) -> str:
        return self.pitch

    @property
    def value_proposition(self) -> str:
        return self.pitch

    @property
    def tailored_pitch(self) -> str:
        return self.pitch

    @property
    def key_benefits(self) -> List[str]:
        return self.value_points

    @property
    def benefits(self) -> List[str]:
        return self.value_points

    @property
    def call_to_action(self) -> str:
        return ""

    @model_validator(mode="before")
    @classmethod
    def normalize_pitch(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        for key in ("pitch_draft", "pitch", "data", "result", "output"):
            if key in data and isinstance(data[key], dict):
                data = data[key]
                break

        headline = (
            data.get("headline")
            or data.get("title")
            or "Tailored Solution Pitch"
        )

        pitch_body = data.get("pitch")
        if not pitch_body or not str(pitch_body).strip():
            parts = []
            for k in ("opening", "tailored_pitch", "value_proposition", "pitch_text", "summary", "call_to_action"):
                val = data.get(k)
                if val and isinstance(val, str) and val.strip():
                    parts.append(val.strip())
            
            pitch_body = "\n\n".join(parts) if parts else (data.get("description") or "Tailored AI solution for your clinic.")

        value_points = data.get("value_points") or data.get("key_benefits") or data.get("benefits") or []
        if isinstance(value_points, str):
            value_points = [value_points]
        elif not isinstance(value_points, list):
            value_points = [str(value_points)]

        assumptions = data.get("assumptions") or []
        if isinstance(assumptions, str):
            assumptions = [assumptions]
        elif not isinstance(assumptions, list):
            assumptions = [str(assumptions)]

        return {
            "headline": str(headline).strip(),
            "pitch": str(pitch_body).strip(),
            "value_points": [str(p).strip() for p in value_points if str(p).strip()],
            "assumptions": [str(a).strip() for a in assumptions if str(a).strip()],
        }


# ============================================================================
# PROPOSAL (WITH AUTO-NORMALIZING & BACKWARD COMPATIBILITY PROPERTIES)
# ============================================================================

class ProposalDraft(StrictBaseModel):
    title: str = Field(..., min_length=1)
    executive_summary: str = Field(..., min_length=1)
    business_goal: str = Field(..., min_length=1)
    target_users: List[str] = Field(default_factory=list)
    proposed_solution: str = Field(..., min_length=1)
    requirements: List[str] = Field(default_factory=list)
    scope_inclusions: List[str] = Field(default_factory=list)
    scope_exclusions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_items: List[str] = Field(default_factory=list)
    implementation_approach: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    security_and_safety: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    timeline: str = Field(default="To be finalized during implementation planning.")
    next_steps: List[str] = Field(default_factory=list)
    status: ProposalStatus = Field(default=ProposalStatus.DRAFT)

    # --- Backward-Compatibility Properties ---
    @property
    def solution_overview(self) -> str:
        return self.proposed_solution

    @property
    def features_and_deliverables(self) -> List[str]:
        return self.deliverables

    @model_validator(mode="before")
    @classmethod
    def normalize_proposal(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        def _to_list(val: Any) -> List[str]:
            if val is None:
                return []
            if isinstance(val, list):
                return [str(x).strip() for x in val if str(x).strip()]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
            return []

        title = data.get("title") or "AI Solution Proposal"
        executive_summary = data.get("executive_summary") or data.get("summary") or "Executive Summary"
        business_goal = data.get("business_goal") or data.get("goal") or "Increase patient inquiries and bookings"
        proposed_solution = data.get("proposed_solution") or data.get("solution_overview") or data.get("solution") or "AI Assistant"

        inclusions = _to_list(data.get("scope_inclusions") or data.get("inclusions") or data.get("features_and_deliverables"))
        exclusions = _to_list(data.get("scope_exclusions") or data.get("exclusions"))
        deliverables = _to_list(data.get("deliverables") or data.get("features_and_deliverables"))
        implementation = _to_list(data.get("implementation_approach") or data.get("approach"))
        security = _to_list(data.get("security_and_safety") or data.get("security") or data.get("compliance"))

        raw_status = str(data.get("status", "draft")).strip().lower()
        status_val = ProposalStatus.DRAFT.value
        for member in ProposalStatus:
            if member.value.lower() == raw_status:
                status_val = member.value
                break

        return {
            "title": str(title).strip(),
            "executive_summary": str(executive_summary).strip(),
            "business_goal": str(business_goal).strip(),
            "target_users": _to_list(data.get("target_users")),
            "proposed_solution": str(proposed_solution).strip(),
            "requirements": _to_list(data.get("requirements")),
            "scope_inclusions": inclusions,
            "scope_exclusions": exclusions,
            "assumptions": _to_list(data.get("assumptions")),
            "open_items": _to_list(data.get("open_items")),
            "implementation_approach": implementation,
            "integrations": _to_list(data.get("integrations")),
            "security_and_safety": security,
            "deliverables": deliverables,
            "success_metrics": _to_list(data.get("success_metrics") or data.get("metrics")),
            "timeline": str(data.get("timeline") or "To be finalized during implementation planning.").strip(),
            "next_steps": _to_list(data.get("next_steps")),
            "status": status_val,
        }
# ============================================================================
# PROPOSAL QA
# ============================================================================

class ProposalQAIssue(StrictBaseModel):
    issue: str = Field(..., min_length=1)
    severity: RiskSeverity = Field(default=RiskSeverity.MEDIUM)
    evidence: str = Field(default="")
    recommendation: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def normalize_issue(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "issue" not in data:
            data["issue"] = data.get("description") or data.get("details") or "Identified QA Issue"

        # Safely extract string enum value without class name prefix
        raw_sev = data.get("severity", "medium")
        if hasattr(raw_sev, "value"):
            s = str(raw_sev.value).strip().lower()
        else:
            s = str(raw_sev).strip().lower()
            if "." in s:
                s = s.split(".")[-1]

        if s not in {"low", "medium", "high", "critical"}:
            s = "medium"

        return {
            "issue": str(data.get("issue", "QA Issue")).strip(),
            "severity": s,
            "evidence": str(data.get("evidence", "")).strip(),
            "recommendation": str(data.get("recommendation", "")).strip(),
        }

class ProposalQAResult(StrictBaseModel):
    decision: ProposalQADecision
    score: float = Field(ge=0.0, le=10.0)
    passed: bool
    issues: List[ProposalQAIssue] = Field(default_factory=list)
    summary: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def normalize_qa_result(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        passed = bool(data.get("passed", True))
        decision_raw = str(data.get("decision", "PASS" if passed else "FAIL")).strip().upper()
        decision = ProposalQADecision.PASS if (passed or decision_raw == "PASS") else ProposalQADecision.FAIL
        passed = (decision == ProposalQADecision.PASS)

        score = data.get("score")
        try:
            score = float(score)
            score = max(0.0, min(10.0, score))
        except (TypeError, ValueError):
            score = 10.0 if passed else 5.0

        return {
            "decision": decision,
            "score": score,
            "passed": passed,
            "issues": data.get("issues", []),
            "summary": str(data.get("summary", "")).strip(),
        }


# ============================================================================
# PIPELINE RESULT
# ============================================================================

class PipelineResult(BaseModel):
    requirement_map: Optional[RequirementMap] = None
    risks: List[Risk] = Field(default_factory=list)
    discovery_questions: Optional[DiscoveryQuestionSet] = None
    client_answers: Dict[str, str] = Field(default_factory=dict)
    scope: Optional[ValidatedScope] = None
    pitch: Optional[PitchDraft] = None
    proposal: Optional[ProposalDraft] = None
    proposal_qa: Optional[ProposalQAResult] = None
    final_status: str = Field(default="NOT_STARTED")
    error: Optional[str] = None
    proposal_generated: bool = False
    approved: bool = False

    @property
    def is_success(self) -> bool:
        if self.final_status != "PASS":
            return False
        if not self.proposal_generated:
            return False
        if self.proposal is None:
            return False
        if self.proposal_qa is None:
            return False
        return self.proposal_qa.passed

    def can_download(self) -> bool:
        return self.is_success


# ============================================================================
# VALIDATION & HELPER FUNCTIONS
# ============================================================================

def validate_requirement_map(requirement_map: RequirementMap) -> RequirementMap:
    if not isinstance(requirement_map, RequirementMap):
        raise ValueError("Expected RequirementMap.")
    if not requirement_map.requirements:
        raise ValueError("RequirementMap contains no requirements.")
    return requirement_map


def validate_scope_is_ready(scope: ValidatedScope) -> ValidatedScope:
    if not isinstance(scope, ValidatedScope):
        raise ValueError("Proposal generation blocked: invalid ValidatedScope.")
    scope_status = str(getattr(scope.overall_scope_status, "value", scope.overall_scope_status))
    if scope_status == ScopeStatus.NEEDS_MORE_DISCOVERY.value:
        raise ValueError("Proposal generation blocked: scope needs more discovery.")
    return scope


def serialize_pipeline_result(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [serialize_pipeline_result(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_pipeline_result(item) for key, item in value.items()}
    if isinstance(value, Enum):
        return value.value
    return value


def get_scope_status_value(scope: Optional[ValidatedScope]) -> Optional[str]:
    if scope is None:
        return None
    return str(getattr(scope.overall_scope_status, "value", scope.overall_scope_status))


def get_validation_status_value(validation: ValidationStatus) -> str:
    return str(getattr(validation.status, "value", validation.status))


def get_proposal_status_value(proposal: Optional[ProposalDraft]) -> Optional[str]:
    if proposal is None:
        return None
    return str(getattr(proposal.status, "value", proposal.status))


def extract_scope_open_items(scope: ValidatedScope) -> List[str]:
    if not isinstance(scope, ValidatedScope):
        raise ValueError("Expected ValidatedScope.")
    open_items: List[str] = []
    for item in scope.unresolved_items:
        text = f"{item.issue} — {item.reason}".strip()
        if text:
            open_items.append(text)
    for requirement in scope.confirmed_requirements:
        if requirement.status == ValidationStatusType.UNRESOLVED:
            req_name = requirement.original_requirement.strip() or requirement.requirement.strip()
            open_items.append(f"{req_name} — Final scope remains unresolved.")
    return list(dict.fromkeys(open_items))