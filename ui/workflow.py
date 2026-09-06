from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


WORKFLOW_ORDER = [
    "input",
    "requirements",
    "risks",
    "discovery",
    "scope",
    "pitch",
    "proposal",
    "qa",
    "final",
]


STEP_LABELS = {
    "input": "Client Input",
    "requirements": "Requirements",
    "risks": "Risk Analysis",
    "discovery": "Discovery",
    "scope": "Validated Scope",
    "pitch": "AI Pitch",
    "proposal": "Proposal",
    "qa": "QA Review",
    "final": "Final Gate",
}


@dataclass
class UIState:
    step: str = "input"

    client_name: str = ""
    source_type: str = "text"
    client_request: str = ""

    preparation: Optional[Any] = None
    answers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    result: Optional[Any] = None

    preparation_cache_key: Optional[str] = None
    result_cache_key: Optional[str] = None

    error: Optional[str] = None
    processing: bool = False


def init_state(st):
    if "ui" not in st.session_state:
        st.session_state.ui = UIState()

    return st.session_state.ui


def reset_state(st):
    st.session_state.ui = UIState()


def set_step(st, step: str):
    if step not in WORKFLOW_ORDER:
        return

    st.session_state.ui.step = step
    st.session_state.ui.error = None


def current_step(st) -> str:
    return st.session_state.ui.step


def step_index(step: str) -> int:
    try:
        return WORKFLOW_ORDER.index(step)
    except ValueError:
        return 0


def can_enter(st, step: str) -> bool:
    ui = st.session_state.ui

    if step == "input":
        return True

    if step == "requirements":
        return ui.preparation is not None

    if step == "risks":
        return ui.preparation is not None

    if step == "discovery":
        return ui.preparation is not None

    if step == "scope":
        return ui.result is not None

    if step == "pitch":
        return ui.result is not None

    if step == "proposal":
        return ui.result is not None

    if step == "qa":
        return ui.result is not None

    if step == "final":
        return ui.result is not None

    return False


def discovery_complete(st) -> bool:
    ui = st.session_state.ui

    if ui.preparation is None:
        return False

    questions = getattr(
        ui.preparation,
        "discovery_questions",
        [],
    )

    if not questions:
        return True

    for question in questions:
        qid = getattr(question, "id", None)

        if not qid:
            continue

        answer = ui.answers.get(qid)

        if not answer:
            return False

        if not answer.get("answer", "").strip() and not answer.get(
            "unresolved",
            False,
        ):
            return False

    return True


def normalize_discovery_answer(answer: str, unresolved: bool) -> Dict[str, Any]:
    return {
        "answer": (answer or "").strip(),
        "unresolved": bool(unresolved),
    }


def collect_discovery_answers(st):
    ui = st.session_state.ui

    if ui.preparation is None:
        return

    questions = getattr(
        ui.preparation,
        "discovery_questions",
        [],
    )

    for question in questions:
        qid = getattr(question, "id", None)

        if not qid:
            continue

        answer_key = f"discovery_answer_{qid}"
        unresolved_key = f"discovery_unresolved_{qid}"

        answer = st.session_state.get(answer_key, "")
        unresolved = st.session_state.get(
            unresolved_key,
            False,
        )

        ui.answers[qid] = normalize_discovery_answer(
            answer,
            unresolved,
        )


def clear_downstream_state(st):
    ui = st.session_state.ui

    ui.answers = {}
    ui.result = None
    ui.result_cache_key = None


def clear_final_result(st):
    ui = st.session_state.ui

    ui.result = None
    ui.result_cache_key = None


def has_preparation_cache(st, cache_key: str) -> bool:
    ui = st.session_state.ui

    return (
        ui.preparation is not None
        and ui.preparation_cache_key == cache_key
    )


def has_result_cache(st, cache_key: str) -> bool:
    ui = st.session_state.ui

    return (
        ui.result is not None
        and ui.result_cache_key == cache_key
    )


def to_serializable(obj):
    if obj is None:
        return None

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    if hasattr(obj, "dict"):
        return obj.dict()

    if hasattr(obj, "__dict__"):
        return {
            key: to_serializable(value)
            for key, value in vars(obj).items()
        }

    if isinstance(obj, dict):
        return {
            key: to_serializable(value)
            for key, value in obj.items()
        }

    if isinstance(obj, list):
        return [to_serializable(item) for item in obj]

    return obj


def state_summary(st) -> Dict[str, Any]:
    ui = st.session_state.ui

    return {
        "step": ui.step,
        "client_name": ui.client_name,
        "source_type": ui.source_type,
        "has_preparation": ui.preparation is not None,
        "has_result": ui.result is not None,
        "discovery_answers": len(ui.answers),
        "error": ui.error,
        "processing": ui.processing,
    }