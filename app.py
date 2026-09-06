"""
app.py

Scope-to-Proposal AI OS — Streamlit UI

Pipeline:

    Client Request
        ↓
    Requirement Extraction
        ↓
    Risk Analysis
        ↓
    ONE Discovery Round
        ↓
    ONE Scope Validation
        ↓
    AI Pitch
        ↓
    Proposal
        ↓
    ONE Proposal QA
        ↓
    Final Delivery
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

import streamlit as st

from src.pipeline import (
    prepare_discovery,
    validate_discovery_scope,
    generate_proposal_from_scope,
    regenerate_proposal,
)

from src.schemas import (
    ScopeStatus,
)

from ui.styles import inject_css


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Scope-to-Proposal AI OS",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()


# =============================================================================
# WORKFLOW
# =============================================================================

STEPS = [
    ("input", "01", "Client Request"),
    ("extract", "02", "Requirements"),
    ("risks", "03", "Risk Analysis"),
    ("discovery", "04", "Discovery"),
    ("scope", "05", "Validated Scope"),
    ("pitch", "06", "AI Pitch"),
    ("proposal", "07", "Proposal"),
    ("qa", "08", "Proposal QA"),
    ("final", "09", "Final Delivery"),
]

STEP_INDEX = {
    step_key: index
    for index, (step_key, _, _) in enumerate(STEPS)
}

STEP_LABEL = {
    step_key: f"{number} — {label}"
    for step_key, number, label in STEPS
}

LOCKED_UNTIL_SCOPE_VALIDATED = {
    "pitch",
    "proposal",
    "qa",
    "final",
}


# =============================================================================
# SESSION STATE
# =============================================================================

def init_state() -> None:
    defaults = {
        "step": "input",
        "client_name": "",
        "source_type": "Client Request",
        "client_request": "",
        "preparation": None,
        "validated_scope": None,
        "result": None,
        "answers": {},
        "processing": False,
        "error": None,
        "preparation_cache_key": None,
        "scope_cache_key": None,
        "proposal_cache_key": None,
        # Appearance-only state
        "completed_steps": set(),
        "_pending_success": None,
        "_pending_action": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# =============================================================================
# MODALS  (appearance only)
# =============================================================================

def show_processing_modal(
    title: str = "Processing",
    subtitle: str = "Please wait while the system completes this step.",
    stage: str = "",
) -> None:
    """Centered blocking overlay shown while an AI call runs."""
    tag = f'<div class="m-tag">{stage}</div>' if stage else ""

    st.markdown(
        '<div class="ov">'
        '<div class="mdl">'
        '<div class="m-spin"></div>'
        f'<div class="m-title">{title}</div>'
        f'<div class="m-sub">{subtitle}</div>'
        '<div class="m-bar"><i></i></div>'
        f'{tag}'
        '</div></div>',
        unsafe_allow_html=True,
    )


def show_success_modal(
    title: str = "Step complete",
    subtitle: str = "You can review the results below.",
    stage: str = "",
) -> None:
    """Non-blocking, auto-dismissing confirmation overlay."""
    tag = f'<div class="m-tag">{stage}</div>' if stage else ""

    st.markdown(
        '<div class="ov soft">'
        '<div class="mdl">'
        '<div class="m-check"></div>'
        f'<div class="m-title">{title}</div>'
        f'<div class="m-sub">{subtitle}</div>'
        f'{tag}'
        '</div></div>',
        unsafe_allow_html=True,
    )


def queue_success(title: str, subtitle: str, stage: str = "") -> None:
    st.session_state["_pending_success"] = {
        "title": title,
        "subtitle": subtitle,
        "stage": stage,
    }


def render_pending_success() -> None:
    payload = st.session_state.get("_pending_success")
    if payload:
        st.session_state["_pending_success"] = None
        show_success_modal(
            title=payload.get("title", "Step complete"),
            subtitle=payload.get("subtitle", ""),
            stage=payload.get("stage", ""),
        )


def mark_step_complete(step_key: str) -> None:
    completed = st.session_state.get("completed_steps")
    if not isinstance(completed, set):
        completed = set()
    completed.add(step_key)
    st.session_state["completed_steps"] = completed


def is_step_complete(step_key: str) -> bool:
    completed = st.session_state.get("completed_steps")
    if not isinstance(completed, set):
        return False
    return step_key in completed


def trigger_action(action: str) -> None:
    """Queue a blocking AI action so the processing modal renders first."""
    st.session_state["_pending_action"] = action
    st.session_state["processing"] = True


# =============================================================================
# BASIC HELPERS
# =============================================================================

def enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return ""
    return str(raw).strip()


def current_step() -> str:
    step = st.session_state.get("step", "input")
    if step not in STEP_INDEX:
        return "input"
    return step


def scope_status(scope: Any) -> str:
    if scope is None:
        return ""
    return enum_value(getattr(scope, "overall_scope_status", "")).lower()


def scope_is_validated() -> bool:
    scope = st.session_state.get("validated_scope")
    if scope is None:
        return False
    status = scope_status(scope)
    return status in {
        ScopeStatus.READY_FOR_PROPOSAL.value,
        ScopeStatus.PARTIALLY_VALIDATED.value,
    }


def scope_needs_attention() -> bool:
    scope = st.session_state.get("validated_scope")
    if scope is None:
        return False
    return scope_status(scope) == ScopeStatus.PARTIALLY_VALIDATED.value


def stable_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    except Exception:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return f"{type(exc).__name__} occurred while running the pipeline."


# =============================================================================
# NAVIGATION
# =============================================================================

def set_step(step: str) -> None:
    if step not in STEP_INDEX:
        return
    if step in LOCKED_UNTIL_SCOPE_VALIDATED and not scope_is_validated():
        st.session_state.step = (
            "discovery"
            if st.session_state.get("preparation") is not None
            else "input"
        )
        return
    st.session_state.step = step


def advance_to(
    step: str,
    from_step: str,
    success_title: str,
    success_subtitle: str,
) -> None:
    mark_step_complete(from_step)
    queue_success(
        title=success_title,
        subtitle=success_subtitle,
        stage=STEP_LABEL.get(from_step, ""),
    )
    set_step(step)


# =============================================================================
# CACHE KEYS
# =============================================================================

def preparation_cache_key() -> str:
    return stable_hash({
        "client_name": st.session_state.get("client_name", ""),
        "source_type": st.session_state.get("source_type", ""),
        "client_request": st.session_state.get("client_request", ""),
    })


def scope_cache_key(preparation: Any, answers: Dict[str, Any]) -> str:
    return stable_hash({"preparation": preparation, "answers": answers})


def proposal_cache_key(validated_scope: Any) -> str:
    return stable_hash(validated_scope)


# =============================================================================
# STATE RESET
# =============================================================================

def clear_discovery_widgets() -> None:
    keys_to_remove = [
        key for key in list(st.session_state.keys())
        if key.startswith("discovery_answer_") or key.startswith("discovery_unresolved_")
    ]
    for key in keys_to_remove:
        del st.session_state[key]


def clear_downstream() -> None:
    st.session_state.validated_scope = None
    st.session_state.result = None
    st.session_state.answers = {}
    st.session_state.processing = False
    st.session_state.error = None
    st.session_state.scope_cache_key = None
    st.session_state.proposal_cache_key = None
    clear_discovery_widgets()

    completed = st.session_state.get("completed_steps")
    if isinstance(completed, set):
        for k in ["discovery", "scope", "pitch", "proposal", "qa", "final"]:
            completed.discard(k)
        st.session_state["completed_steps"] = completed


def clear_all_pipeline_state() -> None:
    st.session_state.preparation = None
    st.session_state.preparation_cache_key = None
    clear_downstream()
    st.session_state["completed_steps"] = set()


def reset_project() -> None:
    st.session_state.step = "input"
    st.session_state.client_name = ""
    st.session_state.source_type = "Client Request"
    st.session_state.client_request = ""
    st.session_state.preparation = None
    st.session_state.validated_scope = None
    st.session_state.result = None
    st.session_state.answers = {}
    st.session_state.processing = False
    st.session_state.error = None
    st.session_state.preparation_cache_key = None
    st.session_state.scope_cache_key = None
    st.session_state.proposal_cache_key = None
    st.session_state["completed_steps"] = set()
    st.session_state["_pending_success"] = None
    st.session_state["_pending_action"] = None
    clear_discovery_widgets()


def invalidate_if_client_input_changed() -> None:
    existing_key = st.session_state.get("preparation_cache_key")
    if not existing_key:
        return
    current_key = preparation_cache_key()
    if current_key != existing_key:
        clear_all_pipeline_state()


# =============================================================================
# DATA ACCESS HELPERS
# =============================================================================

def get_preparation_requirements() -> List[Any]:
    preparation = st.session_state.get("preparation")
    if preparation is None:
        return []
    requirement_map = getattr(preparation, "requirement_map", None)
    if requirement_map is None:
        return []
    requirements = getattr(requirement_map, "requirements", None)
    if requirements is None:
        return []
    return list(requirements)


def get_preparation_risks() -> List[Any]:
    preparation = st.session_state.get("preparation")
    if preparation is None:
        return []
    risks = getattr(preparation, "risks", None)
    return list(risks or [])


def get_discovery_questions() -> List[Any]:
    preparation = st.session_state.get("preparation")
    if preparation is None:
        return []
    question_set = getattr(preparation, "discovery_questions", None)
    if question_set is None:
        return []
    questions = getattr(question_set, "questions", None)
    if questions is None:
        return []
    return list(questions)


def get_proposal(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "proposal", None)


def get_qa(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "proposal_qa", None)


def get_pitch(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "pitch", None)


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def field_value(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value is not None:
            return value
    return default


def display_list(items: Any, empty_message: str = "") -> None:
    items = items or []
    if not items:
        if empty_message:
            st.caption(empty_message)
        return
    for item in items:
        if isinstance(item, dict):
            text = (
                item.get("item")
                or item.get("description")
                or item.get("text")
                or item.get("name")
                or item.get("feature")
                or item.get("next_step")
                or str(item)
            )
        else:
            text = str(item)
        st.markdown(f"- {text}")


def pill(text: str) -> None:
    st.markdown(f'<div class="pill">{text}</div>', unsafe_allow_html=True)


def chip(text: str) -> None:
    st.markdown(f'<div class="chip">✓ {text}</div>', unsafe_allow_html=True)


def note(kind: str, html: str) -> None:
    st.markdown(f'<div class="note {kind}">{html}</div>', unsafe_allow_html=True)


# =============================================================================
# DISCOVERY ANSWERS
# =============================================================================

def question_id(question: Any, index: int) -> str:
    value = field_value(question, "question_id", "id")
    if value is not None:
        return str(value)
    return f"question_{index + 1}"


def question_text(question: Any) -> str:
    return str(field_value(question, "question", "text", "question_text", default=""))


def question_requirement(question: Any) -> str:
    return str(field_value(question, "requirement_id", "requirement", default=""))


def normalize_answer(answer: str, unresolved: bool) -> str:
    answer = str(answer or "").strip()
    if unresolved:
        return (
            "UNRESOLVED — Client could not confirm this information during "
            "the discovery round. Carry this item into the proposal as an open item."
        )
    return answer


def collect_discovery_answers() -> Dict[str, str]:
    questions = get_discovery_questions()
    answers: Dict[str, str] = {}
    for index, question in enumerate(questions):
        qid = question_id(question, index)
        answer_key = f"discovery_answer_{qid}"
        unresolved_key = f"discovery_unresolved_{qid}"
        answer = st.session_state.get(answer_key, "")
        unresolved = bool(st.session_state.get(unresolved_key, False))
        answers[qid] = normalize_answer(answer=answer, unresolved=unresolved)
    return answers


def discovery_is_complete() -> bool:
    questions = get_discovery_questions()
    if not questions:
        return True
    for index, question in enumerate(questions):
        qid = question_id(question, index)
        answer_key = f"discovery_answer_{qid}"
        unresolved_key = f"discovery_unresolved_{qid}"
        answer = str(st.session_state.get(answer_key, "")).strip()
        unresolved = bool(st.session_state.get(unresolved_key, False))
        if not answer and not unresolved:
            return False
    return True


# =============================================================================
# AI ACTIONS  (pipeline logic unchanged)
# =============================================================================

def run_discovery() -> None:
    client_request = str(st.session_state.get("client_request", "")).strip()
    if not client_request:
        st.session_state.error = "Please enter the client request before running AI discovery."
        st.session_state.step = "input"
        return

    cache_key = preparation_cache_key()

    if (
        st.session_state.get("preparation") is not None
        and st.session_state.get("preparation_cache_key") == cache_key
    ):
        st.session_state.error = None
        st.session_state.step = "extract"
        return

    st.session_state.error = None

    try:
        preparation = prepare_discovery(
            client_request=client_request,
            source_type=st.session_state.get("source_type", "Client Request"),
        )
        clear_downstream()
        st.session_state.preparation = preparation
        st.session_state.preparation_cache_key = cache_key
        st.session_state.step = "extract"

        mark_step_complete("input")
        queue_success(
            title="Analysis complete",
            subtitle="Requirements extracted, risks analysed, and discovery questions prepared.",
            stage="01 — Client Request",
        )

    except Exception as exc:
        st.session_state.error = friendly_error(exc)
        st.session_state.step = "input"


def run_scope_validation() -> None:
    preparation = st.session_state.get("preparation")
    if preparation is None:
        st.session_state.error = "Please analyze the client request first."
        st.session_state.step = "input"
        return

    if not discovery_is_complete():
        st.session_state.error = (
            "Please answer every discovery question or mark it as unresolved "
            "before validating the scope."
        )
        st.session_state.step = "discovery"
        return

    answers = collect_discovery_answers()
    cache_key = scope_cache_key(preparation=preparation, answers=answers)

    if (
        st.session_state.get("result") is not None
        and st.session_state.get("scope_cache_key") == cache_key
        and st.session_state.get("validated_scope") is not None
    ):
        st.session_state.error = None
        st.session_state.step = "scope"
        return

    st.session_state.error = None

    try:
        validated_scope = validate_discovery_scope(
            requirement_map=preparation.requirement_map,
            risks=preparation.risks,
            question_set=preparation.discovery_questions,
            answers=answers,
        )
        st.session_state.validated_scope = validated_scope
        st.session_state.answers = answers
        st.session_state.scope_cache_key = cache_key

        result = generate_proposal_from_scope(
            requirement_map=preparation.requirement_map,
            scope=validated_scope,
        )
        st.session_state.result = result
        st.session_state.proposal_cache_key = proposal_cache_key(validated_scope)
        st.session_state.step = "scope"

        mark_step_complete("discovery")
        queue_success(
            title="Scope validated",
            subtitle="Scope validation, pitch, proposal, and QA have all been generated.",
            stage="04 — Discovery",
        )

    except Exception as exc:
        st.session_state.error = friendly_error(exc)
        if st.session_state.get("validated_scope") is not None:
            st.session_state.step = "scope"
        else:
            st.session_state.step = "discovery"


def run_proposal_regeneration() -> None:
    validated_scope = st.session_state.get("validated_scope")
    if validated_scope is None:
        st.session_state.error = "There is no validated scope available for regeneration."
        st.session_state.step = "scope"
        return

    if not scope_is_validated():
        st.session_state.error = (
            "Proposal regeneration is blocked because the scope is not in an allowed proposal state."
        )
        st.session_state.step = "scope"
        return

    st.session_state.error = None

    try:
        regenerated = regenerate_proposal(validated_scope)
        st.session_state.validated_scope = validated_scope
        st.session_state.result = regenerated
        st.session_state.proposal_cache_key = proposal_cache_key(validated_scope)
        st.session_state.step = "proposal"

        queue_success(
            title="Proposal regenerated",
            subtitle="A fresh pitch, proposal, and QA pass have been produced.",
            stage="07 — Proposal",
        )

    except Exception as exc:
        st.session_state.error = friendly_error(exc)
        st.session_state.step = "proposal"


# =============================================================================
# HEADER + STEPPER
# =============================================================================

def render_appbar() -> None:
    step = current_step()
    label = STEP_LABEL.get(step, "")

    st.markdown(
        '<div class="appbar">'
        '<div class="ab-mark">S</div>'
        '<div>'
        '<div class="ab-name">Scope&nbsp;to&nbsp;Proposal</div>'
        '<div class="ab-tag">AI Operating System</div>'
        '</div>'
        '<div class="ab-gap"></div>'
        f'<div class="ab-stage">{label}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_stepper() -> None:
    active_step = current_step()
    active_index = STEP_INDEX[active_step]

    parts = ['<div class="stepper-wrap"><div class="stepper">']

    for key, number, label in STEPS:
        index = STEP_INDEX[key]
        locked = key in LOCKED_UNTIL_SCOPE_VALIDATED and not scope_is_validated()

        if key == active_step:
            cls, icon = "now", str(index + 1)
        elif is_step_complete(key) or index < active_index:
            cls, icon = "done", "✓"
        elif locked:
            cls, icon = "lock", "·"
        else:
            cls, icon = "", str(index + 1)

        parts.append(
            f'<div class="stp {cls}">'
            f'<div class="dot">{icon}</div>'
            f'<div class="lbl"><span class="num">{number}</span>{label}</div>'
            f'</div>'
        )

    parts.append('</div></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_jump_nav() -> None:
    with st.expander("Navigate to a stage  ·  Reset project"):
        available = [
            (k, n, l) for k, n, l in STEPS
            if not (k in LOCKED_UNTIL_SCOPE_VALIDATED and not scope_is_validated())
        ]

        rows = [available[i:i + 5] for i in range(0, len(available), 5)]
        for row in rows:
            cols = st.columns(5)
            for col, (key, number, label) in zip(cols, row):
                with col:
                    if st.button(f"{number} · {label}", key=f"nav_{key}", use_container_width=True):
                        set_step(key)
                        st.rerun()

        st.markdown("")
        if st.button("Reset and start a new project", key="nav_reset", use_container_width=True):
            reset_project()
            st.rerun()


# =============================================================================
# PAGE 01 — INPUT
# =============================================================================

def render_input_page() -> None:
    pill("Stage 01")
    st.title("Client Request")
    st.markdown(
        "Paste the client's raw request below. The pipeline will structure it into "
        "requirements, identify risks, prepare one discovery round, validate scope, "
        "and produce a client-ready proposal."
    )

    st.divider()

    col_a, col_b = st.columns([2, 1])

    with col_a:
        client_name = st.text_input(
            "Client / Company name",
            value=st.session_state.client_name,
            placeholder="e.g. Bright Dental Clinic",
        )

    with col_b:
        source_options = ["Client Request", "Discovery Call", "Email", "WhatsApp", "Other"]
        current_source = st.session_state.source_type
        source_index = (
            source_options.index(current_source)
            if current_source in source_options
            else 0
        )
        source_type = st.selectbox("Request source", source_options, index=source_index)

    client_request = st.text_area(
        "Client request",
        value=st.session_state.client_request,
        height=300,
        placeholder="Paste the complete client requirement here...",
    )

    st.session_state.client_name = client_name
    st.session_state.source_type = source_type
    st.session_state.client_request = client_request

    st.divider()

    if st.button(
        "Analyze client request",
        type="primary",
        use_container_width=True,
        disabled=(not client_request.strip()),
    ):
        trigger_action("discovery")
        st.rerun()


# =============================================================================
# PAGE 02 — REQUIREMENTS
# =============================================================================

def render_requirements_page() -> None:
    pill("Stage 02")
    st.title("Requirement Extraction")

    preparation = st.session_state.get("preparation")
    if preparation is None:
        st.info("Run the client analysis first.")
        return

    requirements = get_preparation_requirements()

    col1, col2 = st.columns([4, 1])
    with col1:
        note("ok", f"<strong>{len(requirements)}</strong> requirement(s) extracted from the client request.")
    with col2:
        if is_step_complete("extract"):
            chip("Reviewed")

    if not requirements:
        st.warning("No requirements were returned by the pipeline.")
    else:
        left, right = st.columns(2)
        for index, requirement in enumerate(requirements, start=1):
            text = field_value(requirement, "requirement", "description", "text", default=str(requirement))
            category = field_value(requirement, "category", default="")
            source = field_value(requirement, "source", default="")
            confidence = field_value(requirement, "confidence", default=None)

            target = left if index % 2 == 1 else right
            with target:
                with st.container(border=True):
                    st.markdown(f"**{index}. {text}**")
                    meta = []
                    if category:
                        meta.append(f"Category `{category}`")
                    if source:
                        meta.append(f"Source `{source}`")
                    if confidence is not None:
                        try:
                            conf_text = f"{float(confidence):.0%}"
                        except Exception:
                            conf_text = str(confidence)
                        meta.append(f"Confidence `{conf_text}`")
                    if meta:
                        st.caption("  ·  ".join(meta))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to request", use_container_width=True):
            set_step("input")
            st.rerun()
    with col2:
        if st.button("View risk analysis", type="primary", use_container_width=True):
            advance_to(
                step="risks",
                from_step="extract",
                success_title="Requirements reviewed",
                success_subtitle="Moving on to the risk analysis stage.",
            )
            st.rerun()


# =============================================================================
# PAGE 03 — RISKS
# =============================================================================

def render_risks_page() -> None:
    pill("Stage 03")
    st.title("Risk Analysis")

    preparation = st.session_state.get("preparation")
    if preparation is None:
        st.info("Run the client analysis first.")
        return

    risks = get_preparation_risks()

    col1, col2 = st.columns([4, 1])
    with col1:
        note("warn", f"<strong>{len(risks)}</strong> risk(s) identified requiring clarification.")
    with col2:
        if is_step_complete("risks"):
            chip("Reviewed")

    if not risks:
        st.info("No explicit risks were returned by the analyzer.")
    else:
        left, right = st.columns(2)
        for index, risk in enumerate(risks, start=1):
            title = field_value(risk, "issue", "risk", "description", "title", default=str(risk))
            level = enum_value(field_value(risk, "risk_level", "severity", default="")).lower()
            requirement = field_value(risk, "requirement_id", "requirement", default="")
            evidence = field_value(risk, "evidence", default="")

            target = left if index % 2 == 1 else right
            with target:
                with st.container(border=True):
                    st.markdown(f"**{index}. {title}**")
                    meta = []
                    if level:
                        meta.append(f"Severity `{level}`")
                    if requirement:
                        meta.append(f"Requirement `{requirement}`")
                    if meta:
                        st.caption("  ·  ".join(meta))
                    if evidence:
                        st.caption(f"Evidence: {evidence}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to requirements", use_container_width=True):
            set_step("extract")
            st.rerun()
    with col2:
        if st.button("Start discovery", type="primary", use_container_width=True):
            advance_to(
                step="discovery",
                from_step="risks",
                success_title="Risks reviewed",
                success_subtitle="Discovery questions are ready for the client call.",
            )
            st.rerun()


# =============================================================================
# PAGE 04 — DISCOVERY
# =============================================================================

def render_discovery_page() -> None:
    pill("Stage 04")
    st.title("Discovery Call")

    note(
        "info",
        "<strong>This is the only discovery round.</strong> Every question is tied to "
        "an identified requirement and risk. If the client cannot confirm something, "
        "mark it unresolved — it will be carried into the proposal as an open item.",
    )

    preparation = st.session_state.get("preparation")
    if preparation is None:
        st.warning("Please analyze the client request first.")
        return

    questions = get_discovery_questions()

    if not questions:
        st.success("No discovery questions were required.")
    else:
        st.markdown(f"### {len(questions)} discovery question(s)")

        left, right = st.columns(2)

        for index, question in enumerate(questions, start=1):
            qid = question_id(question, index - 1)
            text = question_text(question)
            requirement = question_requirement(question)
            answer_key = f"discovery_answer_{qid}"
            unresolved_key = f"discovery_unresolved_{qid}"

            if answer_key not in st.session_state:
                st.session_state[answer_key] = ""
            if unresolved_key not in st.session_state:
                st.session_state[unresolved_key] = False

            target = left if index % 2 == 1 else right
            with target:
                with st.container(border=True):
                    st.markdown(f"**Q{index}. {text}**")
                    if requirement:
                        st.caption(f"Related requirement `{requirement}`")
                    st.text_area(
                        "Client answer",
                        key=answer_key,
                        height=100,
                        placeholder="Enter the client's answer...",
                    )
                    st.checkbox("Mark as unresolved", key=unresolved_key)
                    if st.session_state.get(unresolved_key, False):
                        st.caption(
                            "Sent to scope validation as an explicit unresolved answer. "
                            "This will not trigger another discovery round."
                        )

    st.divider()

    complete = discovery_is_complete()

    if not complete:
        note("warn", "Complete every question or explicitly mark it as unresolved.")
    else:
        note("ok", "Discovery response set is complete and ready for validation.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to risk analysis", use_container_width=True):
            set_step("risks")
            st.rerun()
    with col2:
        if st.button(
            "Validate scope and generate proposal",
            type="primary",
            use_container_width=True,
            disabled=not complete,
        ):
            trigger_action("scope")
            st.rerun()


# =============================================================================
# PAGE 05 — VALIDATED SCOPE
# =============================================================================

def render_scope_page() -> None:
    pill("Stage 05")
    st.title("Validated Scope")

    scope = st.session_state.get("validated_scope")

    if scope is None:
        st.info("Complete the discovery round and validate scope.")
        return

    status = scope_status(scope)

    if status == ScopeStatus.READY_FOR_PROPOSAL.value:
        note("ok", "<strong>Scope fully validated.</strong> Ready for proposal.")
    elif status == ScopeStatus.PARTIALLY_VALIDATED.value:
        note(
            "warn",
            "<strong>Scope partially validated.</strong> The proposal can proceed, and "
            "unresolved items will appear as open items and next steps.",
        )
    elif status == ScopeStatus.NEEDS_MORE_DISCOVERY.value:
        note("err", "<strong>Scope requires more discovery.</strong> Proposal generation is blocked.")
    else:
        note("info", f"Scope status: <code>{status or 'unknown'}</code>")

    confirmed_requirements = getattr(scope, "confirmed_requirements", None) or []
    if confirmed_requirements:
        st.markdown("### Validated requirements")
        left, right = st.columns(2)
        for index, item in enumerate(confirmed_requirements, start=1):
            original = field_value(item, "original_requirement", default="")
            final_scope = field_value(item, "final_scope", default="")
            item_status = enum_value(field_value(item, "status", default="")).lower()

            target = left if index % 2 == 1 else right
            with target:
                with st.container(border=True):
                    st.markdown(f"**{index}. {original or 'Requirement'}**")
                    if item_status:
                        st.caption(f"Status `{item_status}`")
                    if final_scope:
                        st.write(final_scope)

    boundaries = getattr(scope, "scope_boundaries", None) or []
    if boundaries:
        st.markdown("### Scope boundaries")
        display_list(boundaries)

    unresolved = getattr(scope, "unresolved_items", None) or []
    if unresolved:
        st.markdown("### Open items")
        note("warn", "These items were not fully resolved and will be carried into the proposal.")
        for item in unresolved:
            text = field_value(item, "issue", "item", "description", "question", "text", default=str(item))
            st.markdown(f"- {text}")

    assumptions = getattr(scope, "assumptions", None) or []
    if assumptions:
        st.markdown("### Assumptions")
        display_list(assumptions)

    exclusions = getattr(scope, "exclusions", None) or []
    if exclusions:
        st.markdown("### Exclusions")
        display_list(exclusions)

    st.divider()

    result = st.session_state.get("result")
    if result is not None:
        note("ok", "Pitch, proposal, and QA have already been generated from this scope.")

    if status in {ScopeStatus.READY_FOR_PROPOSAL.value, ScopeStatus.PARTIALLY_VALIDATED.value}:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to discovery", use_container_width=True):
                set_step("discovery")
                st.rerun()
        with col2:
            if st.button(
                "View AI pitch",
                type="primary",
                use_container_width=True,
                disabled=result is None,
            ):
                advance_to(
                    step="pitch",
                    from_step="scope",
                    success_title="Scope confirmed",
                    success_subtitle="Reviewing the generated client pitch next.",
                )
                st.rerun()
    else:
        st.error("Proposal generation is not available for this scope status.")


# =============================================================================
# PAGE 06 — AI PITCH
# =============================================================================

def render_pitch_page() -> None:
    pill("Stage 06")
    st.title("AI Pitch")

    result = st.session_state.get("result")
    if result is None:
        st.info("Generate the proposal from validated scope first.")
        return

    pitch = get_pitch(result)

    if pitch is None:
        st.info("No separate pitch object was returned. Continue to the proposal.")
    elif isinstance(pitch, str):
        st.markdown(pitch)
    else:
        headline = field_value(pitch, "headline", "title", default=None)
        pitch_text = field_value(pitch, "pitch", "message", "body", "content", default=None)

        if headline:
            with st.container(border=True):
                st.markdown(f"## {headline}")

        if pitch_text:
            st.markdown("### The pitch")
            st.write(str(pitch_text))
        elif not headline:
            st.json(pitch.model_dump() if hasattr(pitch, "model_dump") else pitch)

        value_points = field_value(pitch, "value_points", "key_benefits", default=None)
        if value_points:
            st.markdown("### Key benefits")
            cols = st.columns(min(3, max(1, len(value_points))))
            for i, vp in enumerate(value_points):
                with cols[i % len(cols)]:
                    with st.container(border=True):
                        st.markdown(f"{vp}")

        pitch_assumptions = field_value(pitch, "assumptions", default=None)
        if pitch_assumptions:
            st.markdown("### Assumptions")
            display_list(pitch_assumptions)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to validated scope", use_container_width=True):
            set_step("scope")
            st.rerun()
    with col2:
        if st.button("View proposal", type="primary", use_container_width=True):
            advance_to(
                step="proposal",
                from_step="pitch",
                success_title="Pitch reviewed",
                success_subtitle="Opening the full client-facing proposal.",
            )
            st.rerun()


# =============================================================================
# PAGE 07 — PROPOSAL
# =============================================================================

def render_proposal_page() -> None:
    pill("Stage 07")
    st.title("Proposal")

    result = st.session_state.get("result")
    if result is None:
        st.info("No proposal has been generated yet.")
        return

    proposal = get_proposal(result)
    if proposal is None:
        st.error("The pipeline result does not contain a proposal.")
        return

    proposal_status = enum_value(getattr(proposal, "status", ""))
    if proposal_status:
        st.caption(f"Proposal status `{proposal_status}`")

    title = field_value(proposal, "title", default=None)
    if title:
        with st.container(border=True):
            st.markdown(f"## {title}")

    summary = field_value(proposal, "executive_summary", "summary", default=None)
    if summary:
        st.markdown("### Executive summary")
        st.write(summary)

    goals = field_value(proposal, "business_goals", "goals", "business_goal", default=None)
    if goals:
        st.markdown("### Business goal")
        if isinstance(goals, str):
            st.write(goals)
        else:
            display_list(goals)

    target_users = field_value(proposal, "target_users", default=None)
    if target_users:
        st.markdown("### Target users")
        display_list(target_users)

    solution = field_value(proposal, "proposed_solution", "solution", default=None)
    if solution:
        st.markdown("### Proposed solution")
        if isinstance(solution, str):
            st.write(solution)
        else:
            st.json(solution)

    c1, c2 = st.columns(2)

    with c1:
        scope_inclusions = field_value(proposal, "scope_inclusions", default=None)
        if scope_inclusions:
            st.markdown("### Scope inclusions")
            display_list(scope_inclusions)

        deliverables = field_value(proposal, "deliverables", default=None)
        if deliverables:
            st.markdown("### Deliverables")
            display_list(deliverables)

        implementation = field_value(proposal, "implementation_approach", default=None)
        if implementation:
            st.markdown("### Implementation approach")
            display_list(implementation)

    with c2:
        exclusions = field_value(proposal, "scope_exclusions", "exclusions", default=None)
        if exclusions:
            st.markdown("### Exclusions")
            display_list(exclusions)

        integrations = field_value(proposal, "integrations", default=None)
        if integrations:
            st.markdown("### Integrations")
            display_list(integrations)

        security = field_value(proposal, "security_and_safety", default=None)
        if security:
            st.markdown("### Security and safety")
            display_list(security)

    assumptions = field_value(proposal, "assumptions", default=None)
    if assumptions:
        st.markdown("### Assumptions")
        display_list(assumptions)

    open_items = field_value(proposal, "open_items", default=None) or []
    st.markdown("### Open items and next steps")

    if open_items:
        note("warn", "These items should be confirmed before final implementation commitment.")
        display_list(open_items)
    else:
        note("ok", "No open items. The scope is fully confirmed.")

    timeline = field_value(proposal, "timeline", default=None)
    if timeline:
        st.markdown("### Timeline")
        st.write(timeline)

    next_steps = field_value(proposal, "next_steps", default=None) or []
    if next_steps:
        st.markdown("### Next steps")
        display_list(next_steps)

    success_metrics = field_value(proposal, "success_metrics", default=None)
    if success_metrics:
        st.markdown("### Success metrics")
        display_list(success_metrics)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Regenerate proposal",
            use_container_width=True,
            disabled=not scope_is_validated(),
        ):
            trigger_action("regenerate")
            st.rerun()
    with col2:
        if st.button("Continue to proposal QA", type="primary", use_container_width=True):
            advance_to(
                step="qa",
                from_step="proposal",
                success_title="Proposal reviewed",
                success_subtitle="Running the final quality assurance review.",
            )
            st.rerun()


# =============================================================================
# PAGE 08 — PROPOSAL QA
# =============================================================================

def render_qa_page() -> None:
    pill("Stage 08")
    st.title("Proposal QA")

    result = st.session_state.get("result")
    if result is None:
        st.info("Generate the proposal first.")
        return

    qa = get_qa(result)
    if qa is None:
        st.error("No proposal QA result is available.")
        return

    decision = enum_value(getattr(qa, "decision", "")).upper()
    passed = bool(getattr(qa, "passed", False))
    score = getattr(qa, "score", None)

    col1, col2 = st.columns([3, 1])

    with col1:
        if passed or decision == "PASS":
            note("ok", "<strong>Proposal QA: Pass</strong><br>The proposal is safe, grounded, and client-ready.")
        else:
            note("err", f"<strong>Proposal QA: {decision or 'Needs review'}</strong><br>Blocking issues were found.")

    with col2:
        if score is not None:
            st.metric("QA score", f"{score} / 10")

    issues = getattr(qa, "issues", None) or []
    if issues:
        st.markdown("### QA findings")
        left, right = st.columns(2)
        for i, issue in enumerate(issues, start=1):
            text = field_value(issue, "issue", "description", "message", default=str(issue))
            severity = enum_value(field_value(issue, "severity", default="")).lower()
            recommendation = field_value(issue, "recommendation", default="")

            target = left if i % 2 == 1 else right
            with target:
                with st.container(border=True):
                    st.markdown(f"**{text}**")
                    if severity:
                        st.caption(f"Severity `{severity}`")
                    if recommendation:
                        st.caption(f"Recommendation: {recommendation}")
    else:
        note("ok", "No QA issues reported.")

    summary = getattr(qa, "summary", "")
    if summary:
        st.markdown("### QA summary")
        st.info(summary)

    st.divider()

    try:
        can_download = bool(result.can_download())
    except Exception:
        can_download = False

    final_gate_passed = can_download and (passed or decision == "PASS")

    if final_gate_passed:
        note("ok", "The proposal has passed QA and is eligible for final delivery.")
    else:
        note("warn", "Final delivery remains locked until proposal QA passes and the download gate is satisfied.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to proposal", use_container_width=True):
            set_step("proposal")
            st.rerun()
    with col2:
        if st.button(
            "Continue to final delivery",
            type="primary",
            use_container_width=True,
            disabled=not final_gate_passed,
        ):
            advance_to(
                step="final",
                from_step="qa",
                success_title="QA passed",
                success_subtitle="The proposal is approved and ready to download.",
            )
            st.rerun()


# =============================================================================
# PDF PROPOSAL GENERATOR
# =============================================================================

def _sanitize_pdf_text(text: Any) -> str:
    if text is None:
        return ""
    result = str(text)

    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u201c": '"', "\u201d": '"',
        "\u2018": "'", "\u2019": "'",
        "\u2022": "*", "\u2026": "...",
        "\u2265": ">=", "\u2264": "<=",
        "\u2192": "->", "\u2190": "<-",
        "\u00d7": "x", "\u00a9": "(c)",
        "\u00ae": "(R)", "\u2122": "(TM)",
    }
    for old, new in replacements.items():
        result = result.replace(old, new)

    return result.encode("latin-1", "replace").decode("latin-1")


def generate_proposal_pdf(proposal: Any, client_name: str = "") -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    width = pdf.epw

    def heading(text: str, size: int = 13) -> None:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_text_color(45, 65, 130)
        pdf.multi_cell(width, 8, _sanitize_pdf_text(text))
        pdf.ln(1.5)

    def body(text: str, size: int = 10) -> None:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "", size)
        pdf.set_text_color(55, 60, 70)
        pdf.multi_cell(width, 5.8, _sanitize_pdf_text(text))
        pdf.ln(2.5)

    def bullet_list(items: List[Any], size: int = 10) -> None:
        pdf.set_font("Helvetica", "", size)
        pdf.set_text_color(55, 60, 70)
        for item in items:
            if isinstance(item, dict):
                item_text = (
                    item.get("item") or item.get("description")
                    or item.get("text") or item.get("name") or str(item)
                )
            else:
                item_text = str(item)
            pdf.set_x(15)
            pdf.multi_cell(width - 5, 5.8, f"-  {_sanitize_pdf_text(item_text)}")
        pdf.ln(2.5)

    def section(title: str, content: Any) -> None:
        if content is None or content == "" or content == []:
            return
        heading(title, 12)
        if isinstance(content, list):
            bullet_list(content)
        else:
            body(str(content))

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 45, 77)
    title_text = _sanitize_pdf_text(
        field_value(proposal, "title", default="AI Solution Proposal") or "AI Solution Proposal"
    )
    pdf.multi_cell(width, 11, title_text, align="C")
    pdf.ln(2)

    if client_name:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(120, 128, 145)
        pdf.multi_cell(width, 6, _sanitize_pdf_text(f"Prepared for: {client_name}"), align="C")
        pdf.ln(2)

    pdf.set_draw_color(107, 125, 179)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.set_line_width(0.2)
    pdf.ln(8)

    section("Executive Summary", field_value(proposal, "executive_summary", default=""))
    section("Business Goal", field_value(proposal, "business_goal", default=""))

    target_users = field_value(proposal, "target_users", default=None)
    if target_users:
        section("Target Users", target_users)

    section("Proposed Solution", field_value(proposal, "proposed_solution", default=""))
    section("Scope Inclusions", field_value(proposal, "scope_inclusions", default=[]))
    section("Deliverables", field_value(proposal, "deliverables", default=[]))
    section("Implementation Approach", field_value(proposal, "implementation_approach", default=[]))
    section("Integrations", field_value(proposal, "integrations", default=[]))
    section("Security and Safety", field_value(proposal, "security_and_safety", default=[]))
    section("Assumptions", field_value(proposal, "assumptions", default=[]))
    section("Scope Exclusions", field_value(proposal, "scope_exclusions", default=[]))
    section("Open Items / Pending Confirmations", field_value(proposal, "open_items", default=[]))

    timeline = field_value(proposal, "timeline", default="")
    if timeline:
        section("Timeline", timeline)

    section("Next Steps", field_value(proposal, "next_steps", default=[]))
    section("Success Metrics", field_value(proposal, "success_metrics", default=[]))

    pdf.ln(6)
    pdf.set_draw_color(215, 220, 235)
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.ln(3)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 158, 172)
    pdf.multi_cell(width, 5, "Generated by Scope-to-Proposal AI OS", align="C")

    output = pdf.output()
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    return bytes(output, encoding="latin-1")


# =============================================================================
# PAGE 09 — FINAL DELIVERY
# =============================================================================

def render_final_page() -> None:
    pill("Stage 09")
    st.title("Final Delivery")

    result = st.session_state.get("result")
    if result is None:
        st.info("No pipeline result is available.")
        return

    qa = get_qa(result)
    if qa is None:
        st.error("Final delivery is blocked because proposal QA is missing.")
        return

    decision = enum_value(getattr(qa, "decision", "")).upper()
    passed = bool(getattr(qa, "passed", False))

    try:
        can_download = bool(result.can_download())
    except Exception:
        can_download = False

    final_gate_passed = can_download and (passed or decision == "PASS")

    if final_gate_passed:
        mark_step_complete("final")

        st.markdown(
            '<div class="hero">'
            '<div class="h-ic">✓</div>'
            '<div class="h-tt">Proposal approved for delivery</div>'
            '<div class="h-sb">All QA gates passed. Your client-ready proposal is available below.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        try:
            proposal = get_proposal(result)
            client_name_raw = st.session_state.get("client_name", "").strip() or "Client"

            pdf_bytes = generate_proposal_pdf(proposal, client_name=client_name_raw)

            safe_name = "".join(
                c if c.isalnum() else "_" for c in client_name_raw
            ).strip("_") or "client"

            st.download_button(
                "Download approved proposal (PDF)",
                data=pdf_bytes,
                file_name=f"{safe_name}_proposal.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        except ImportError:
            st.error(
                "PDF generation requires fpdf2. Run `pip install fpdf2` in your "
                "terminal, then restart Streamlit."
            )
        except Exception as exc:
            st.error(f"Could not prepare the proposal PDF: {friendly_error(exc)}")

    else:
        note("err", "<strong>Final delivery is locked.</strong>")
        note(
            "warn",
            "Download is available only when proposal QA returns Pass and the "
            "pipeline download gate is satisfied.",
        )

    st.markdown("### Delivery summary")

    scope = st.session_state.get("validated_scope")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        with st.container(border=True):
            st.caption("SCOPE STATUS")
            st.markdown(f"**{(scope_status(scope) or 'unknown').replace('_', ' ').title()}**")

    with c2:
        with st.container(border=True):
            st.caption("PROPOSAL QA")
            st.markdown(f"**{decision.title() or 'Unknown'}**")

    with c3:
        with st.container(border=True):
            st.caption("DELIVERY GATE")
            st.markdown(f"**{'Approved' if final_gate_passed else 'Locked'}**")

    with c4:
        with st.container(border=True):
            st.caption("DOWNLOAD")
            st.markdown(f"**{'Available' if can_download else 'Locked'}**")

    proposal = get_proposal(result)
    if proposal is not None:
        open_items = field_value(proposal, "open_items", default=None) or []
        if open_items:
            st.markdown("### Open items carried into the proposal")
            note("warn", "These were intentionally not resolved through another discovery round.")
            display_list(open_items)

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Back to proposal QA", use_container_width=True):
            set_step("qa")
            st.rerun()
    with c2:
        if st.button("Start a new project", type="primary", use_container_width=True):
            reset_project()
            st.rerun()


# =============================================================================
# GLOBAL ERROR
# =============================================================================

def render_global_error() -> None:
    error = st.session_state.get("error")
    if error:
        st.error(error)


# =============================================================================
# ROUTER
# =============================================================================

def render_current_page() -> None:
    step = current_step()

    if step in LOCKED_UNTIL_SCOPE_VALIDATED and not scope_is_validated():
        st.session_state.step = (
            "discovery"
            if st.session_state.get("preparation") is not None
            else "input"
        )
        step = st.session_state.step

    pages = {
        "input": render_input_page,
        "extract": render_requirements_page,
        "risks": render_risks_page,
        "discovery": render_discovery_page,
        "scope": render_scope_page,
        "pitch": render_pitch_page,
        "proposal": render_proposal_page,
        "qa": render_qa_page,
        "final": render_final_page,
    }

    pages.get(step, render_input_page)()


# =============================================================================
# PENDING ACTION EXECUTOR
# =============================================================================

PROCESSING_COPY = {
    "discovery": (
        "Extracting requirements",
        "Analysing the client request, identifying risks, and preparing the discovery questions.",
    ),
    "scope": (
        "Validating scope",
        "Processing discovery answers, validating scope, generating the pitch, proposal, and QA.",
    ),
    "regenerate": (
        "Regenerating proposal",
        "Rebuilding the pitch, proposal, and quality assurance review.",
    ),
}


def run_pending_action() -> bool:
    """
    Renders the processing modal first so it streams to the browser,
    then executes the queued blocking AI action.
    """
    action = st.session_state.get("_pending_action")
    if not action:
        return False

    title, subtitle = PROCESSING_COPY.get(
        action,
        ("Processing", "Please wait while the system completes this step."),
    )

    render_appbar()
    render_stepper()

    show_processing_modal(
        title=title,
        subtitle=subtitle,
        stage=STEP_LABEL.get(current_step(), ""),
    )

    st.session_state["_pending_action"] = None

    if action == "discovery":
        run_discovery()
    elif action == "scope":
        run_scope_validation()
    elif action == "regenerate":
        run_proposal_regeneration()

    st.session_state["processing"] = False
    st.rerun()
    return True


# =============================================================================
# MAIN APP
# =============================================================================

invalidate_if_client_input_changed()

if not run_pending_action():
    render_appbar()
    render_stepper()
    render_jump_nav()

    render_pending_success()
    render_global_error()
    render_current_page()