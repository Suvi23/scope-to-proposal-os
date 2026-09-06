"""
pipeline.py

Scope-to-Proposal AI OS orchestration layer.

Architecture:

    Client Request
        ↓
    Requirement Extraction
        ↓
    Risk Analysis
        ↓
    ONE Discovery Call
        ↓
    Scope Validation
        ↓
    Proposal Generation
        ↓
    ONE Proposal QA
        ↓
    PASS / FAIL

Important design rules:

1. Exactly one discovery round.
2. Exactly one scope validation call.
3. No follow-up discovery generation.
4. PARTIALLY_VALIDATED scopes may generate proposals.
5. NEEDS_MORE_DISCOVERY scopes remain blocked.
6. Unresolved scope items are carried into ProposalDraft.open_items.
7. Proposal QA is the only proposal QA engine.
8. Do not import ai_proposal_qa.py.
9. Do not import final_qa_gate.py.
10. Do not invent requirements or scope.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from .schemas import (
    DiscoveryQuestion,
    DiscoveryQuestionSet,
    PitchDraft,
    PipelineResult,
    ProposalDraft,
    ProposalStatus,
    RequirementMap,
    Risk,
    ScopeStatus,
    ValidatedScope,
    ValidationStatusType,
    extract_scope_open_items,
    serialize_pipeline_result,
    validate_scope_is_ready,
)

from .extractor import extract_requirements
from .analyzer import analyze_risks

from .discovery import (
    generate_discovery_questions,
    validate_discovery_question_set,
)

from .scope_validator import validate_scope

from .pitch_generator import generate_pitch
from .proposal_generator import generate_proposal

from .proposal_qa import validate_proposal


# ============================================================================
# EXCEPTIONS
# ============================================================================


class PipelineError(Exception):
    """Base pipeline exception."""


class RiskCoverageError(PipelineError):
    """Raised when requirements are not adequately covered by risks."""


class DiscoveryContractError(PipelineError):
    """Raised when discovery questions violate the pipeline contract."""


class AnswerContractError(PipelineError):
    """Raised when client answers violate the discovery contract."""


class ScopeClosureError(PipelineError):
    """Raised when validated scope cannot safely continue."""


class ProposalBlockedError(PipelineError):
    """Raised when proposal generation is not allowed."""


class PitchGenerationError(PipelineError):
    """Raised when pitch generation fails."""


class ProposalGenerationError(PipelineError):
    """Raised when proposal generation fails."""


class ProposalQAError(PipelineError):
    """Raised when proposal QA fails to execute."""


# ============================================================================
# DISCOVERY PREPARATION RESULT
# ============================================================================


class DiscoveryPreparation(SimpleNamespace):
    """
    Output of the preparation stage.

    This contains everything needed to conduct the ONE discovery call.
    """

    requirement_map: RequirementMap
    risks: List[Risk]
    discovery_questions: DiscoveryQuestionSet
    source_type: str = "text"

    def to_dict(self) -> Dict[str, Any]:
        return serialize_pipeline_result(
            {
                "requirement_map": self.requirement_map,
                "risks": self.risks,
                "discovery_questions": self.discovery_questions,
                "source_type": self.source_type,
            }
        )


# ============================================================================
# INTERNAL HELPERS
# ============================================================================


def _status_value(value: Any) -> str:
    """
    Safely convert Enum/string status values into plain strings.
    """

    return str(
        getattr(
            value,
            "value",
            value,
        )
    )


def _normalize_requirement_map(
    value: Any,
) -> RequirementMap:
    """
    Normalize extractor output into RequirementMap.
    """

    if isinstance(value, RequirementMap):
        return value

    if hasattr(value, "model_dump"):
        try:
            return RequirementMap.model_validate(
                value.model_dump()
            )
        except Exception:
            pass

    if isinstance(value, dict):
        return RequirementMap.model_validate(value)

    raise PipelineError(
        "Requirement extraction returned an unsupported result type."
    )


def _normalize_risks(
    value: Any,
) -> List[Risk]:
    """
    Normalize risk analyzer output into List[Risk].
    """

    if value is None:
        raise RiskCoverageError(
            "Risk analyzer returned no risks."
        )

    if isinstance(value, dict):
        if "risks" in value:
            value = value["risks"]
        else:
            value = [value]

    if hasattr(value, "risks"):
        value = value.risks

    if not isinstance(value, list):
        try:
            value = list(value)
        except Exception as exc:
            raise RiskCoverageError(
                "Risk analyzer returned an unsupported result type."
            ) from exc

    normalized: List[Risk] = []

    for item in value:

        if isinstance(item, Risk):
            normalized.append(item)
            continue

        if hasattr(item, "model_dump"):
            item = item.model_dump()

        if isinstance(item, dict):
            normalized.append(
                Risk.model_validate(item)
            )
            continue

        raise RiskCoverageError(
            "Risk analyzer returned an invalid risk item."
        )

    return normalized


def _coerce_question_set(
    value: Any,
) -> DiscoveryQuestionSet:
    """
    Normalize discovery generator output into DiscoveryQuestionSet.
    """

    if isinstance(value, DiscoveryQuestionSet):
        return value

    if hasattr(value, "model_dump"):
        try:
            return DiscoveryQuestionSet.model_validate(
                value.model_dump()
            )
        except Exception:
            pass

    if isinstance(value, dict):

        if "questions" in value:
            return DiscoveryQuestionSet.model_validate(value)

        return DiscoveryQuestionSet.model_validate(
            {
                "questions": [value],
            }
        )

    if isinstance(value, list):

        normalized_questions = []

        for item in value:

            if isinstance(item, DiscoveryQuestion):
                normalized_questions.append(item)

            elif hasattr(item, "model_dump"):
                normalized_questions.append(
                    DiscoveryQuestion.model_validate(
                        item.model_dump()
                    )
                )

            elif isinstance(item, dict):
                normalized_questions.append(
                    DiscoveryQuestion.model_validate(item)
                )

            else:
                raise DiscoveryContractError(
                    "Discovery generator returned an invalid question item."
                )

        return DiscoveryQuestionSet(
            questions=normalized_questions
        )

    raise DiscoveryContractError(
        "Discovery generator returned an unsupported result type."
    )


def _normalize_answers(
    answers: Any,
) -> Dict[str, str]:
    """
    Normalize client answers into:

        {
            question_id: answer
        }
    """

    if answers is None:
        return {}

    if isinstance(answers, dict):

        normalized: Dict[str, str] = {}

        for key, value in answers.items():

            normalized[str(key)] = str(
                value
            ).strip()

        return normalized

    if isinstance(answers, list):

        normalized = {}

        for item in answers:

            if hasattr(item, "model_dump"):
                item = item.model_dump()

            if not isinstance(item, dict):
                raise AnswerContractError(
                    "Answer list contains an invalid item."
                )

            question_id = (
                item.get("question_id")
                or item.get("id")
            )

            answer = item.get(
                "answer",
                item.get("response", ""),
            )

            if not question_id:
                raise AnswerContractError(
                    "Answer is missing question_id."
                )

            normalized[str(question_id)] = str(
                answer
            ).strip()

        return normalized

    raise AnswerContractError(
        "Client answers must be a dictionary or list."
    )


# ============================================================================
# REQUIREMENT → RISK COVERAGE
# ============================================================================


def _run_risk_coverage_gate(
    requirement_map: RequirementMap,
    risks: List[Risk],
) -> None:
    """
    Ensure every authoritative requirement has risk coverage.

    Contract:

        Every requirement
            ↓
        At least one risk
    """

    if not requirement_map.requirements:
        raise RiskCoverageError(
            "No requirements were extracted."
        )

    if not risks:
        raise RiskCoverageError(
            "No risks were generated."
        )

    requirement_ids = {
        requirement.requirement_id
        for requirement in requirement_map.requirements
    }

    seen_risk_ids = set()
    covered_requirement_ids = set()

    for risk in risks:

        risk_id = risk.risk_id.strip()

        if not risk_id:
            raise RiskCoverageError(
                "A risk is missing risk_id."
            )

        if risk_id in seen_risk_ids:
            raise RiskCoverageError(
                f"Duplicate risk_id detected: {risk_id}"
            )

        seen_risk_ids.add(risk_id)

        if risk.requirement_id not in requirement_ids:
            raise RiskCoverageError(
                f"Risk '{risk_id}' references unknown requirement "
                f"'{risk.requirement_id}'."
            )

        if not risk.issue.strip():
            raise RiskCoverageError(
                f"Risk '{risk_id}' has empty issue."
            )

        if not risk.evidence.strip():
            raise RiskCoverageError(
                f"Risk '{risk_id}' has empty evidence."
            )

        covered_requirement_ids.add(
            risk.requirement_id
        )

    missing_requirements = (
        requirement_ids - covered_requirement_ids
    )

    if missing_requirements:

        raise RiskCoverageError(
            "Every requirement must have risk coverage. "
            f"Missing requirement IDs: "
            f"{sorted(missing_requirements)}"
        )


# ============================================================================
# DISCOVERY CONTRACT
# ============================================================================


def _run_discovery_gate(
    requirement_map: RequirementMap,
    risks: List[Risk],
    question_set: Any,
) -> DiscoveryQuestionSet:
    """
    Enforce the ONE discovery-round contract.

    Contract:

        Every risk
            ↓
        Exactly one discovery question
            ↓
        Same requirement_id
    """

    question_set = _coerce_question_set(
        question_set
    )

    # Let schema validation run first.
    try:
        validate_discovery_question_set(
            question_set
        )
    except Exception as exc:
        raise DiscoveryContractError(
            f"Discovery question-set validation failed: {exc}"
        ) from exc

    if len(question_set.questions) != len(risks):
        raise DiscoveryContractError(
            "Discovery contract failed: expected exactly one "
            "question per risk. "
            f"Risks={len(risks)}, "
            f"Questions={len(question_set.questions)}"
        )

    risk_by_id = {
        risk.risk_id: risk
        for risk in risks
    }

    seen_risk_ids = set()

    for question in question_set.questions:

        if question.risk_id not in risk_by_id:
            raise DiscoveryContractError(
                f"Question '{question.question_id}' references "
                f"unknown risk '{question.risk_id}'."
            )

        if question.risk_id in seen_risk_ids:
            raise DiscoveryContractError(
                "Discovery contract failed: "
                f"risk '{question.risk_id}' has more than one question."
            )

        seen_risk_ids.add(
            question.risk_id
        )

        expected_requirement_id = (
            risk_by_id[question.risk_id].requirement_id
        )

        if question.requirement_id != expected_requirement_id:
            raise DiscoveryContractError(
                f"Question '{question.question_id}' maps to "
                f"requirement '{question.requirement_id}', "
                f"but risk '{question.risk_id}' belongs to "
                f"requirement '{expected_requirement_id}'."
            )

        if not question.question.strip():
            raise DiscoveryContractError(
                f"Question '{question.question_id}' is empty."
            )

    expected_risk_ids = set(
        risk_by_id.keys()
    )

    if seen_risk_ids != expected_risk_ids:

        missing = expected_risk_ids - seen_risk_ids

        raise DiscoveryContractError(
            "Discovery contract failed: some risks have no question. "
            f"Missing risk IDs: {sorted(missing)}"
        )

    return question_set


# ============================================================================
# REQUIREMENT → RISK → QUESTION AUDIT
# ============================================================================


def _audit_requirement_risk_question_chain(
    requirement_map: RequirementMap,
    risks: List[Risk],
    question_set: DiscoveryQuestionSet,
) -> None:
    """
    Audit complete traceability:

        requirement
            ↓
        risk
            ↓
        question
    """

    requirement_ids = {
        requirement.requirement_id
        for requirement in requirement_map.requirements
    }

    risk_by_id = {
        risk.risk_id: risk
        for risk in risks
    }

    question_by_risk = {
        question.risk_id: question
        for question in question_set.questions
    }

    for risk in risks:

        if risk.requirement_id not in requirement_ids:
            raise DiscoveryContractError(
                f"Risk '{risk.risk_id}' points to an unknown requirement."
            )

        question = question_by_risk.get(
            risk.risk_id
        )

        if question is None:
            raise DiscoveryContractError(
                f"Risk '{risk.risk_id}' has no discovery question."
            )

        if question.requirement_id != risk.requirement_id:
            raise DiscoveryContractError(
                f"Risk '{risk.risk_id}' and question "
                f"'{question.question_id}' have mismatched requirements."
            )

        if question.risk_id not in risk_by_id:
            raise DiscoveryContractError(
                f"Question '{question.question_id}' points to unknown risk."
            )


# ============================================================================
# ANSWER CONTRACT
# ============================================================================


def _validate_client_answers(
    question_set: DiscoveryQuestionSet,
    answers: Dict[str, str],
) -> Dict[str, str]:
    """
    Validate exactly one answer for every discovery question.

    No follow-up discovery is created here.

    Missing or unresolved information is expected to be represented
    by the scope validator as unresolved scope.
    """

    expected_ids = {
        question.question_id
        for question in question_set.questions
    }

    actual_ids = set(
        answers.keys()
    )

    missing_ids = expected_ids - actual_ids

    if missing_ids:
        raise AnswerContractError(
            "Missing answers for discovery questions: "
            f"{sorted(missing_ids)}"
        )

    unexpected_ids = actual_ids - expected_ids

    if unexpected_ids:
        raise AnswerContractError(
            "Answers contain unexpected question IDs: "
            f"{sorted(unexpected_ids)}"
        )

    for question_id, answer in answers.items():

        if not str(answer).strip():

            raise AnswerContractError(
                f"Question '{question_id}' has an empty answer. "
                "Use an explicit unresolved response if the client "
                "cannot provide the information."
            )

    return answers


def _audit_requirement_risk_question_answer_chain(
    requirement_map: RequirementMap,
    risks: List[Risk],
    question_set: DiscoveryQuestionSet,
    answers: Dict[str, str],
) -> None:
    """
    Final pre-scope traceability audit:

        Requirement
            ↓
        Risk
            ↓
        Question
            ↓
        Answer
    """

    _audit_requirement_risk_question_chain(
        requirement_map=requirement_map,
        risks=risks,
        question_set=question_set,
    )

    question_ids = {
        question.question_id
        for question in question_set.questions
    }

    answer_ids = set(
        answers.keys()
    )

    if question_ids != answer_ids:
        raise AnswerContractError(
            "Requirement/risk/question/answer chain is incomplete."
        )


# ============================================================================
# DISCOVERY PREPARATION
# ============================================================================


def prepare_discovery(
    client_request: str,
    source_type: str = "text",
) -> DiscoveryPreparation:
    """
    Run the preparation stages required before the ONE discovery call.

    This function does NOT validate client answers and does NOT generate
    a second round of questions.
    """

    if not str(client_request).strip():
        raise PipelineError(
            "Client request cannot be empty."
        )

    try:

        # ------------------------------------------------------------------
        # STEP 1 — REQUIREMENT EXTRACTION
        # ------------------------------------------------------------------

        raw_requirement_map = extract_requirements(
            client_request
        )

        requirement_map = _normalize_requirement_map(
            raw_requirement_map
        )

        # ------------------------------------------------------------------
        # STEP 2 — RISK ANALYSIS
        # ------------------------------------------------------------------

        raw_risks = analyze_risks(
            requirement_map
        )

        risks = _normalize_risks(
            raw_risks
        )

        # ------------------------------------------------------------------
        # STEP 3 — RISK COVERAGE
        # ------------------------------------------------------------------

        _run_risk_coverage_gate(
            requirement_map=requirement_map,
            risks=risks,
        )

        # ------------------------------------------------------------------
        # STEP 4 — ONE DISCOVERY QUESTION GENERATION
        # ------------------------------------------------------------------

        raw_questions = generate_discovery_questions(
            requirement_map=requirement_map,
            risks=risks,
        )

        discovery_questions = _run_discovery_gate(
            requirement_map=requirement_map,
            risks=risks,
            question_set=raw_questions,
        )

        # ------------------------------------------------------------------
        # STEP 5 — TRACEABILITY AUDIT
        # ------------------------------------------------------------------

        _audit_requirement_risk_question_chain(
            requirement_map=requirement_map,
            risks=risks,
            question_set=discovery_questions,
        )

        return DiscoveryPreparation(
            requirement_map=requirement_map,
            risks=risks,
            discovery_questions=discovery_questions,
            source_type=source_type,
        )

    except PipelineError:
        raise

    except Exception as exc:

        raise PipelineError(
            f"Discovery preparation failed: {exc}"
        ) from exc


# ============================================================================
# SCOPE VALIDATION
# ============================================================================


def validate_discovery_scope(
    requirement_map: RequirementMap,
    risks: List[Risk],
    question_set: Any,
    answers: Any,
) -> ValidatedScope:
    """
    Validate the discovery answers and produce authoritative scope.

    IMPORTANT:

    This function calls validate_scope() exactly ONE time.

    It does NOT:
        - generate follow-up questions
        - run another discovery round
        - call another scope validator
        - retry discovery automatically

    PARTIALLY_VALIDATED is accepted.

    NEEDS_MORE_DISCOVERY remains blocked.

    Unresolved items are intentionally preserved so that proposal
    generation can expose them through ProposalDraft.open_items.
    """

    # ------------------------------------------------------------------------
    # Normalize discovery question set
    # ------------------------------------------------------------------------

    normalized_question_set = _run_discovery_gate(
        requirement_map=requirement_map,
        risks=risks,
        question_set=question_set,
    )

    # ------------------------------------------------------------------------
    # Normalize + validate answers
    # ------------------------------------------------------------------------

    normalized_answers = _normalize_answers(
        answers
    )

    normalized_answers = _validate_client_answers(
        question_set=normalized_question_set,
        answers=normalized_answers,
    )

    # ------------------------------------------------------------------------
    # Complete traceability audit
    # ------------------------------------------------------------------------

    _audit_requirement_risk_question_answer_chain(
        requirement_map=requirement_map,
        risks=risks,
        question_set=normalized_question_set,
        answers=normalized_answers,
    )

    # ------------------------------------------------------------------------
    # EXACTLY ONE SCOPE VALIDATION CALL
    # ------------------------------------------------------------------------

    try:

        raw_scope = validate_scope(
            requirement_map=requirement_map,
            risks=risks,
            discovery_questions=normalized_question_set.questions,
            client_answers=normalized_answers,
        )

    except Exception as exc:

        raise ScopeClosureError(
            f"Scope validation failed: {exc}"
        ) from exc

    # ------------------------------------------------------------------------
    # Normalize ValidatedScope
    # ------------------------------------------------------------------------

    try:

        if isinstance(raw_scope, ValidatedScope):

            scope = raw_scope

        elif hasattr(raw_scope, "model_dump"):

            scope = ValidatedScope.model_validate(
                raw_scope.model_dump()
            )

        elif isinstance(raw_scope, dict):

            scope = ValidatedScope.model_validate(
                raw_scope
            )

        else:

            raise ScopeClosureError(
                "Scope validator returned an unsupported result type."
            )

    except ScopeClosureError:
        raise

    except Exception as exc:

        raise ScopeClosureError(
            f"Invalid scope returned by scope validator: {exc}"
        ) from exc

    # ------------------------------------------------------------------------
    # AUTHORITATIVE REQUIREMENT CHECK
    # ------------------------------------------------------------------------

    authoritative_requirements = {
        requirement.requirement.strip().lower()
        for requirement in requirement_map.requirements
    }

    for item in scope.confirmed_requirements:

        original_requirement = (
            item.original_requirement.strip().lower()
        )

        requirement = (
            item.requirement.strip().lower()
        )

        if original_requirement not in authoritative_requirements:

            raise ScopeClosureError(
                "SCOPE_BLOCKED: scope validator introduced an "
                "unknown original requirement: "
                f"'{item.original_requirement}'"
            )

        if requirement not in authoritative_requirements:

            # A modified requirement may differ in wording, but its
            # original requirement must still map to the authoritative
            # client requirement.
            if item.status != ValidationStatusType.MODIFIED:

                raise ScopeClosureError(
                    "SCOPE_BLOCKED: scope validator introduced an "
                    "unsupported requirement: "
                    f"'{item.requirement}'"
                )

    # ------------------------------------------------------------------------
    # CONFIRMED / MODIFIED REQUIREMENT SAFETY CHECK
    # ------------------------------------------------------------------------

    for item in scope.confirmed_requirements:

        status = _status_value(
            item.status
        )

        if status in {
            ValidationStatusType.CONFIRMED.value,
            ValidationStatusType.MODIFIED.value,
        }:

            if not str(item.final_scope).strip():

                raise ScopeClosureError(
                    "SCOPE_BLOCKED: requirement "
                    f"'{item.original_requirement}' has status "
                    f"'{status}' but no final_scope."
                )

    # ------------------------------------------------------------------------
    # SCOPE STATUS GATE
    # ------------------------------------------------------------------------
    #
    # READY_FOR_PROPOSAL:
    #     Fully resolved.
    #
    # PARTIALLY_VALIDATED:
    #     Proposal allowed; unresolved items flow into open_items.
    #
    # NEEDS_MORE_DISCOVERY:
    #     Blocked.
    #
    # ------------------------------------------------------------------------

    scope_status = _status_value(
        scope.overall_scope_status
    )

    if scope_status not in {
        ScopeStatus.READY_FOR_PROPOSAL.value,
        ScopeStatus.PARTIALLY_VALIDATED.value,
    }:

        raise ScopeClosureError(
            "SCOPE_BLOCKED: "
            f"scope status is '{scope_status}'. "
            "The scope must be ready_for_proposal or "
            "partially_validated."
        )

    # ------------------------------------------------------------------------
    # Schema-level readiness validation.
    #
    # IMPORTANT:
    # validate_scope_is_ready() has been updated in schemas.py to allow
    # PARTIALLY_VALIDATED while still blocking NEEDS_MORE_DISCOVERY.
    # ------------------------------------------------------------------------

    try:

        validate_scope_is_ready(
            scope
        )

    except Exception as exc:

        raise ScopeClosureError(
            f"SCOPE_BLOCKED: {exc}"
        ) from exc

    return scope


# ============================================================================
# PROPOSAL SCOPE GUARD
# ============================================================================


def _assert_proposal_scope_ready(
    scope: ValidatedScope,
) -> None:
    """
    Final proposal-generation guard.

    Fully resolved scopes:
        READY_FOR_PROPOSAL

    Partially resolved scopes:
        PARTIALLY_VALIDATED

    Unresolved information is allowed only when it is explicitly
    represented in the validated scope.

    NEEDS_MORE_DISCOVERY remains blocked.

    IMPORTANT:
    We intentionally do NOT call scope_validator.assert_scope_ready_for_proposal()
    here because that helper may represent the older strict
    ready-only contract. The authoritative proposal guard is now
    validate_scope_is_ready() from schemas.py.
    """

    if not isinstance(scope, ValidatedScope):

        raise ProposalBlockedError(
            "PROPOSAL_BLOCKED: invalid ValidatedScope."
        )

    try:

        validate_scope_is_ready(
            scope
        )

    except Exception as exc:

        raise ProposalBlockedError(
            f"PROPOSAL_BLOCKED: {exc}"
        ) from exc

    scope_status = _status_value(
        scope.overall_scope_status
    )

    if scope_status not in {
        ScopeStatus.READY_FOR_PROPOSAL.value,
        ScopeStatus.PARTIALLY_VALIDATED.value,
    }:

        raise ProposalBlockedError(
            "PROPOSAL_BLOCKED: "
            f"scope status is '{scope_status}'."
        )

    for item in scope.confirmed_requirements:

        status = _status_value(
            item.status
        )

        if status in {
            ValidationStatusType.CONFIRMED.value,
            ValidationStatusType.MODIFIED.value,
        }:

            if not str(item.final_scope).strip():

                raise ProposalBlockedError(
                    "PROPOSAL_BLOCKED: "
                    f"'{item.original_requirement}' "
                    f"has status '{status}' "
                    "but no final_scope."
                )


# ============================================================================
# OPEN ITEMS
# ============================================================================


def _build_open_items(
    scope: ValidatedScope,
) -> List[str]:
    """
    Deterministically extract unresolved scope information.

    This prevents the proposal LLM from accidentally forgetting
    unresolved items.

    No new information is invented.
    """

    try:

        return extract_scope_open_items(
            scope
        )

    except Exception as exc:

        raise ProposalGenerationError(
            f"Could not build proposal open_items: {exc}"
        ) from exc


# ============================================================================
# SAFE PITCH GENERATION
# ============================================================================


def _generate_pitch_safely(
    scope: ValidatedScope,
) -> PitchDraft:
    """
    Generate pitch safely from validated scope.
    """

    try:

        raw_pitch = generate_pitch(
            scope
        )

        if isinstance(raw_pitch, PitchDraft):
            return raw_pitch

        if hasattr(raw_pitch, "model_dump"):

            return PitchDraft.model_validate(
                raw_pitch.model_dump()
            )

        if isinstance(raw_pitch, dict):

            return PitchDraft.model_validate(
                raw_pitch
            )

        raise PitchGenerationError(
            "Pitch generator returned an unsupported result type."
        )

    except PitchGenerationError:
        raise

    except Exception as exc:

        raise PitchGenerationError(
            f"Pitch generation failed: {exc}"
        ) from exc


# ============================================================================
# SAFE PROPOSAL GENERATION
# ============================================================================


def _generate_proposal_safely(
    scope: ValidatedScope,
) -> ProposalDraft:
    """
    Generate proposal safely from validated scope.

    After AI generation, unresolved scope items are deterministically
    merged into ProposalDraft.open_items.
    """

    open_items = _build_open_items(
        scope
    )

    try:

        raw_proposal = generate_proposal(
            scope
        )

        # --------------------------------------------------------------
        # Normalize proposal output
        # --------------------------------------------------------------

        if isinstance(raw_proposal, ProposalDraft):

            proposal = raw_proposal

        elif hasattr(raw_proposal, "model_dump"):

            proposal = ProposalDraft.model_validate(
                raw_proposal.model_dump()
            )

        elif isinstance(raw_proposal, dict):

            proposal = ProposalDraft.model_validate(
                raw_proposal
            )

        else:

            raise ProposalGenerationError(
                "Proposal generator returned an unsupported result type."
            )

        # --------------------------------------------------------------
        # Deterministically carry unresolved items into proposal
        # --------------------------------------------------------------

        existing_open_items = [
            str(item).strip()
            for item in proposal.open_items
            if str(item).strip()
        ]

        combined_open_items: List[str] = []

        seen = set()

        for item in (
            existing_open_items
            + open_items
        ):

            normalized = " ".join(
                item.lower().split()
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)

            combined_open_items.append(
                item
            )

        proposal.open_items = combined_open_items

        # --------------------------------------------------------------
        # Make unresolved items visible in next steps as well.
        #
        # We only add a generic next-step statement when there are
        # actual unresolved items.
        # --------------------------------------------------------------

        if combined_open_items:

            next_steps = [
                str(step).strip()
                for step in proposal.next_steps
                if str(step).strip()
            ]

            unresolved_next_step = (
                "Confirm the open scope items before final implementation "
                "commitment."
            )

            if unresolved_next_step not in next_steps:

                next_steps.append(
                    unresolved_next_step
                )

            proposal.next_steps = next_steps

        return proposal

    except ProposalGenerationError:
        raise

    except Exception as exc:

        raise ProposalGenerationError(
            f"Proposal generation failed: {exc}"
        ) from exc


# ============================================================================
# PROPOSAL + QA
# ============================================================================


def generate_proposal_from_scope(
    requirement_map: RequirementMap,
    scope: ValidatedScope,
) -> PipelineResult:
    """
    Generate pitch + proposal and run exactly ONE proposal QA.

    No second QA engine is called.
    """

    result = PipelineResult()

    result.requirement_map = requirement_map
    result.scope = scope

    # ------------------------------------------------------------------------
    # Proposal readiness
    # ------------------------------------------------------------------------

    _assert_proposal_scope_ready(
        scope
    )

    # ------------------------------------------------------------------------
    # Pitch
    # ------------------------------------------------------------------------

    pitch = _generate_pitch_safely(
        scope
    )

    result.pitch = pitch

    # ------------------------------------------------------------------------
    # Proposal
    # ------------------------------------------------------------------------

    proposal = _generate_proposal_safely(
        scope
    )

    result.proposal = proposal
    result.proposal_generated = True

    # ------------------------------------------------------------------------
    # EXACTLY ONE PROPOSAL QA
    # ------------------------------------------------------------------------

    try:

        proposal_qa = validate_proposal(
            scope=scope,
            proposal=proposal,
            pitch=pitch,
        )

    except Exception as exc:

        result.final_status = "NEEDS_REVISION"
        result.approved = False

        raise ProposalQAError(
            f"Proposal QA failed to execute: {exc}"
        ) from exc

    # ------------------------------------------------------------------------
    # Normalize QA result where possible
    # ------------------------------------------------------------------------

    result.proposal_qa = proposal_qa

    # ------------------------------------------------------------------------
    # FINAL QA DECISION
    # ------------------------------------------------------------------------

    passed = bool(
        getattr(
            proposal_qa,
            "passed",
            False,
        )
    )

    decision = _status_value(
        getattr(
            proposal_qa,
            "decision",
            "",
        )
    )

    if passed or decision.upper() == "PASS":

        result.final_status = "PASS"
        result.approved = True

        proposal.status = ProposalStatus.READY_FOR_CLIENT
        return result

    # ------------------------------------------------------------------------
    # QA FAIL
    # ------------------------------------------------------------------------

    result.final_status = "NEEDS_REVISION"
    result.approved = False

    return result


# ============================================================================
# FINAL PIPELINE EXECUTION
# ============================================================================


def generate_final_proposal(
    preparation: DiscoveryPreparation,
    answers: Optional[Dict[str, str]] = None,
    client_answers: Optional[Dict[str, str]] = None,
) -> PipelineResult:
    """
    Complete second half of the pipeline.

    Flow:

        Prepared discovery
            ↓
        ONE scope validation
            ↓
        Pitch
            ↓
        Proposal
            ↓
        ONE Proposal QA
            ↓
        PASS / NEEDS_REVISION

    There is intentionally NO follow-up discovery stage.
    """

    if not isinstance(
        preparation,
        DiscoveryPreparation,
    ):

        raise PipelineError(
            "generate_final_proposal() requires DiscoveryPreparation."
        )

    # ------------------------------------------------------------------------
    # Resolve answer parameter
    # ------------------------------------------------------------------------

    if answers is not None and client_answers is not None:

        if answers != client_answers:

            raise AnswerContractError(
                "Both answers and client_answers were supplied "
                "with different values."
            )

    resolved_answers = (
        client_answers
        if client_answers is not None
        else answers
    )

    if resolved_answers is None:

        raise AnswerContractError(
            "Client answers are required."
        )

    # ------------------------------------------------------------------------
    # Initialize result early.
    #
    # This prevents UnboundLocalError during exception handling.
    # ------------------------------------------------------------------------

    result = PipelineResult(
        requirement_map=preparation.requirement_map,
        risks=list(preparation.risks),
        discovery_questions=preparation.discovery_questions,
        client_answers=_normalize_answers(
            resolved_answers
        ),
    )

    # ------------------------------------------------------------------------
    # ONE SCOPE VALIDATION
    # ------------------------------------------------------------------------

    try:

        validated_scope = validate_discovery_scope(
            requirement_map=preparation.requirement_map,
            risks=preparation.risks,
            question_set=preparation.discovery_questions,
            answers=resolved_answers,
        )

        result.scope = validated_scope

    except (
        AnswerContractError,
        DiscoveryContractError,
        ScopeClosureError,
    ) as exc:

        result.final_status = "BLOCKED"
        result.approved = False
        result.error = str(exc)

        return result

    except Exception as exc:

        result.final_status = "BLOCKED"
        result.approved = False
        result.error = (
            f"Unexpected scope validation error: {exc}"
        )

        return result

    # ------------------------------------------------------------------------
    # Proposal readiness
    # ------------------------------------------------------------------------

    try:

        _assert_proposal_scope_ready(
            validated_scope
        )

    except ProposalBlockedError as exc:

        result.final_status = "BLOCKED"
        result.approved = False
        result.error = str(exc)

        return result

    # ------------------------------------------------------------------------
    # Proposal generation + one QA
    # ------------------------------------------------------------------------

    try:

        proposal_result = generate_proposal_from_scope(
            requirement_map=preparation.requirement_map,
            scope=validated_scope,
        )

        # Preserve discovery context.
        proposal_result.requirement_map = (
            preparation.requirement_map
        )

        proposal_result.risks = list(
            preparation.risks
        )

        proposal_result.discovery_questions = (
            preparation.discovery_questions
        )

        proposal_result.client_answers = (
            _normalize_answers(
                resolved_answers
            )
        )

        proposal_result.scope = validated_scope

        return proposal_result

    except (
        ProposalBlockedError,
        PitchGenerationError,
        ProposalGenerationError,
        ProposalQAError,
    ) as exc:

        result.final_status = (
            "BLOCKED"
            if isinstance(
                exc,
                ProposalBlockedError,
            )
            else "NEEDS_REVISION"
        )

        result.approved = False
        result.error = str(exc)

        return result

    except Exception as exc:

        result.final_status = "NEEDS_REVISION"
        result.approved = False
        result.error = (
            f"Unexpected proposal pipeline error: {exc}"
        )

        return result


# ============================================================================
# REGENERATE PROPOSAL
# ============================================================================


def regenerate_proposal(
    scope: ValidatedScope,
) -> PipelineResult:
    """
    Regenerate a proposal from an already validated scope.

    This does NOT run discovery again.

    This performs:

        existing scope
            ↓
        pitch
            ↓
        proposal
            ↓
        ONE proposal QA
    """

    result = PipelineResult(
        scope=scope
    )

    try:

        _assert_proposal_scope_ready(
            scope
        )

        pitch = _generate_pitch_safely(
            scope
        )

        proposal = _generate_proposal_safely(
            scope
        )

        result.pitch = pitch
        result.proposal = proposal
        result.proposal_generated = True

        # Exactly one QA.
        proposal_qa = validate_proposal(
            scope=scope,
            proposal=proposal,
            pitch=pitch,
        )

        result.proposal_qa = proposal_qa

        passed = bool(
            getattr(
                proposal_qa,
                "passed",
                False,
            )
        )

        decision = _status_value(
            getattr(
                proposal_qa,
                "decision",
                "",
            )
        )

        if passed or decision.upper() == "PASS":

            result.final_status = "PASS"
            result.approved = True

        else:

            result.final_status = "NEEDS_REVISION"
            result.approved = False

        return result

    except ProposalBlockedError as exc:

        result.final_status = "BLOCKED"
        result.approved = False
        result.error = str(exc)

        return result

    except Exception as exc:

        result.final_status = "NEEDS_REVISION"
        result.approved = False
        result.error = (
            f"Proposal regeneration failed: {exc}"
        )

        return result


# ============================================================================
# COMPLETE END-TO-END PIPELINE
# ============================================================================


def run_pipeline(
    client_request: str,
    client_answers: Dict[str, str],
) -> PipelineResult:
    """
    Complete end-to-end execution.

    Architecture:

        Client Request
            ↓
        Requirement Extraction
            ↓
        Risk Analysis
            ↓
        ONE Discovery Question Set
            ↓
        ONE Scope Validation
            ↓
        Pitch
            ↓
        Proposal
            ↓
        ONE Proposal QA
            ↓
        PASS / FAIL
    """

    preparation = prepare_discovery(
        client_request=client_request,
        source_type="text",
    )

    return generate_final_proposal(
        preparation=preparation,
        client_answers=client_answers,
    )


# ============================================================================
# SERIALIZATION
# ============================================================================


def serialize_discovery_preparation(
    preparation: DiscoveryPreparation,
) -> Dict[str, Any]:
    """
    Serialize DiscoveryPreparation for UI/debugging.
    """

    if not isinstance(
        preparation,
        DiscoveryPreparation,
    ):

        raise ValueError(
            "Expected DiscoveryPreparation."
        )

    return preparation.to_dict()


def serialize_result(
    result: PipelineResult,
) -> Dict[str, Any]:
    """
    Serialize final PipelineResult.
    """

    if not isinstance(
        result,
        PipelineResult,
    ):

        raise ValueError(
            "Expected PipelineResult."
        )

    return serialize_pipeline_result(
        result
    )


# ============================================================================
# FINAL DELIVERY HELPER
# ============================================================================


def can_deliver_final_proposal(
    result: PipelineResult,
) -> bool:
    """
    Single deterministic final-delivery gate.

    A proposal is downloadable only when:

        final_status == PASS
        proposal_generated == True
        approved == True
        proposal exists
        proposal QA exists
        proposal QA passed == True
    """

    if not isinstance(
        result,
        PipelineResult,
    ):
        return False

    return result.can_download()


# ============================================================================
# DEBUG / SUMMARY HELPERS
# ============================================================================


def pipeline_summary(
    result: PipelineResult,
) -> Dict[str, Any]:
    """
    Return a compact summary useful for Streamlit.
    """

    if not isinstance(
        result,
        PipelineResult,
    ):

        raise ValueError(
            "Expected PipelineResult."
        )

    scope_status = None

    if result.scope is not None:

        scope_status = _status_value(
            result.scope.overall_scope_status
        )

    unresolved_count = 0

    if result.scope is not None:

        unresolved_count = len(
            result.scope.unresolved_items
        )

        unresolved_count += sum(
            1
            for item in result.scope.confirmed_requirements
            if item.status == ValidationStatusType.UNRESOLVED
        )

    qa_passed = False

    if result.proposal_qa is not None:

        qa_passed = bool(
            getattr(
                result.proposal_qa,
                "passed",
                False,
            )
        )

    return {
        "final_status": result.final_status,
        "scope_status": scope_status,
        "requirements": (
            len(result.requirement_map.requirements)
            if result.requirement_map is not None
            else 0
        ),
        "risks": len(result.risks),
        "discovery_questions": (
            len(result.discovery_questions.questions)
            if result.discovery_questions is not None
            else 0
        ),
        "answers": len(result.client_answers),
        "unresolved_items": unresolved_count,
        "proposal_generated": result.proposal_generated,
        "proposal_qa_passed": qa_passed,
        "approved": result.approved,
        "can_download": result.can_download(),
        "error": result.error,
    }


# ============================================================================
# END OF FILE
# ============================================================================
