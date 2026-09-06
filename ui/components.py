import json
from typing import Any, Iterable, Optional

import streamlit as st


STEPS = [
    ("input", "01", "Client Input"),
    ("requirements", "02", "Requirements"),
    ("risks", "03", "Risk Analysis"),
    ("discovery", "04", "Discovery"),
    ("scope", "05", "Validated Scope"),
    ("pitch", "06", "AI Pitch"),
    ("proposal", "07", "Proposal"),
    ("qa", "08", "QA Review"),
    ("final", "09", "Final Gate"),
]


def _to_dict(value: Any):
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    if isinstance(value, dict):
        return value

    if hasattr(value, "__dict__"):
        return vars(value)

    return value


def _get(value: Any, key: str, default=None):
    if value is None:
        return default

    if isinstance(value, dict):
        return value.get(key, default)

    return getattr(value, key, default)


def _safe_text(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback

    if isinstance(value, bool):
        return "Yes" if value else "No"

    text = str(value).strip()

    return text if text else fallback


def _severity_icon(severity: Any) -> str:
    value = str(severity or "").lower()

    if "critical" in value:
        return "🔴"

    if "high" in value:
        return "🟠"

    if "medium" in value:
        return "🟡"

    if "low" in value:
        return "🔵"

    return "⚪"


def _status_icon(status: Any) -> str:
    value = str(status or "").lower()

    if value in {"confirmed", "pass", "passed", "ready_for_proposal"}:
        return "✓"

    if value in {"modified", "warning", "partially_validated"}:
        return "↻"

    if value in {"rejected", "fail", "failed"}:
        return "×"

    if value in {"unresolved", "needs_more_discovery"}:
        return "⚠"

    return "•"


def page_header(
    eyebrow: str,
    title: str,
    description: str,
):
    st.caption(eyebrow.upper())

    st.title(title)

    if description:
        st.write(description)

    st.divider()


def section_title(
    title: str,
    description: Optional[str] = None,
):
    st.subheader(title)

    if description:
        st.caption(description)


def metric_row(metrics):
    columns = st.columns(len(metrics))

    for column, metric in zip(columns, metrics):
        label = metric.get("label", "")
        value = metric.get("value", "—")
        delta = metric.get("delta")

        with column:
            st.metric(
                label=label,
                value=value,
                delta=delta,
            )


def render_sidebar(st, ui):
    st.sidebar.markdown("## ScopeOS")
    st.sidebar.caption("Discovery → Scope → Proposal")

    st.sidebar.divider()

    st.sidebar.markdown("**WORKFLOW**")

    for step_key, number, label in STEPS:
        active = ui.step == step_key

        if active:
            prefix = "●"
        elif _step_completed(ui, step_key):
            prefix = "✓"
        else:
            prefix = "○"

        button_label = f"{prefix}  {number}  {label}"

        if st.sidebar.button(
            button_label,
            key=f"nav_{step_key}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            if _can_enter(ui, step_key):
                ui.step = step_key
                st.rerun()

    st.sidebar.divider()

    if ui.client_name:
        st.sidebar.markdown("**CURRENT PROJECT**")
        st.sidebar.write(ui.client_name)

    if ui.source_type:
        st.sidebar.caption(
            f"Source: {ui.source_type.replace('_', ' ').title()}"
        )

    st.sidebar.divider()

    if st.sidebar.button(
        "↻ Start new project",
        use_container_width=True,
    ):
        from .workflow import reset_state

        reset_state(st)
        st.rerun()


def _step_completed(ui, step_key: str) -> bool:
    if step_key == "input":
        return bool(ui.client_request.strip())

    if step_key in {
        "requirements",
        "risks",
        "discovery",
    }:
        return ui.preparation is not None

    if step_key in {
        "scope",
        "pitch",
        "proposal",
        "qa",
        "final",
    }:
        return ui.result is not None

    return False


def _can_enter(ui, step_key: str) -> bool:
    if step_key == "input":
        return True

    if step_key in {
        "requirements",
        "risks",
        "discovery",
    }:
        return ui.preparation is not None

    if step_key in {
        "scope",
        "pitch",
        "proposal",
        "qa",
        "final",
    }:
        return ui.result is not None

    return False


def status_badge(status: str):
    status = str(status or "").replace("_", " ").title()

    if status.lower() in {
        "pass",
        "passed",
        "ready for proposal",
        "ready for client",
    }:
        st.success(status)

    elif status.lower() in {
        "fail",
        "failed",
        "rejected",
    }:
        st.error(status)

    elif status.lower() in {
        "needs revision",
        "needs more discovery",
        "partially validated",
        "warning",
    }:
        st.warning(status)

    else:
        st.info(status)


def render_requirements(preparation):
    requirement_map = _get(preparation, "requirement_map")

    if requirement_map is None:
        st.info("No requirement map is available yet.")
        return

    business_goal = _get(
        requirement_map,
        "business_goal",
    )

    target_users = _get(
        requirement_map,
        "target_users",
        [],
    )

    requirements = _get(
        requirement_map,
        "requirements",
        [],
    )

    metric_row(
        [
            {
                "label": "Requirements",
                "value": len(requirements),
            },
            {
                "label": "Target users",
                "value": len(target_users),
            },
            {
                "label": "Business goal",
                "value": _safe_text(
                    business_goal,
                    "Not specified",
                ),
            },
        ]
    )

    st.write("")

    section_title("Business goal")

    if business_goal:
        with st.container(border=True):
            st.write(business_goal)
    else:
        st.info("No business goal was explicitly identified.")

    section_title("Target users")

    if target_users:
        columns = st.columns(
            min(len(target_users), 4)
        )

        for index, user in enumerate(target_users):
            with columns[index % len(columns)]:
                with st.container(border=True):
                    st.write(f"**{user}**")
    else:
        st.info("No target users were identified.")

    section_title(
        "Requirements",
        f"{len(requirements)} requirements extracted from the client request.",
    )

    for index, requirement in enumerate(requirements, start=1):
        text = _get(requirement, "requirement")
        category = _get(requirement, "category")
        source = _get(requirement, "source")
        confidence = _get(requirement, "confidence")
        risk_level = _get(requirement, "risk_level")

        with st.container(border=True):
            st.markdown(
                f"### {index:02d}  {_safe_text(text)}"
            )

            cols = st.columns(4)

            with cols[0]:
                st.caption("CATEGORY")
                st.write(_safe_text(category))

            with cols[1]:
                st.caption("SOURCE")
                st.write(
                    _safe_text(source)
                    .replace("_", " ")
                    .title()
                )

            with cols[2]:
                st.caption("CONFIDENCE")
                if isinstance(confidence, (int, float)):
                    st.write(f"{confidence * 100:.0f}%")
                else:
                    st.write(_safe_text(confidence))

            with cols[3]:
                st.caption("RISK")
                st.write(
                    f"{_severity_icon(risk_level)} "
                    f"{_safe_text(risk_level).title()}"
                )


def render_risks(preparation):
    risks = _get(
        preparation,
        "risks",
        [],
    )

    metric_row(
        [
            {
                "label": "Total risks",
                "value": len(risks),
            },
            {
                "label": "High / Critical",
                "value": sum(
                    1
                    for risk in risks
                    if str(
                        _get(risk, "severity", "")
                    ).lower()
                    in {"high", "critical"}
                ),
            },
            {
                "label": "Needs confirmation",
                "value": sum(
                    1
                    for risk in risks
                    if _get(
                        risk,
                        "needs_confirmation",
                        True,
                    )
                ),
            },
        ]
    )

    st.write("")

    if not risks:
        st.success("No risks were identified.")
        return

    for index, risk in enumerate(risks, start=1):
        issue = _get(risk, "issue")
        risk_type = _get(risk, "type")
        severity = _get(risk, "severity")
        evidence = _get(risk, "evidence")
        impact = _get(risk, "impact")
        needs_confirmation = _get(
            risk,
            "needs_confirmation",
            True,
        )

        with st.container(border=True):
            st.markdown(
                f"### {_severity_icon(severity)} "
                f"{_safe_text(issue)}"
            )

            cols = st.columns(2)

            with cols[0]:
                st.caption("TYPE")
                st.write(
                    _safe_text(risk_type)
                    .replace("_", " ")
                    .title()
                )

            with cols[1]:
                st.caption("SEVERITY")
                st.write(
                    _safe_text(severity).title()
                )

            st.caption("EVIDENCE")
            st.write(_safe_text(evidence))

            st.caption("POTENTIAL IMPACT")
            st.write(_safe_text(impact))

            if needs_confirmation:
                st.warning(
                    "Client confirmation required."
                )


def render_discovery_questions(preparation):
    questions = _get(
        preparation,
        "discovery_questions",
        [],
    )

    metric_row(
        [
            {
                "label": "Questions",
                "value": len(questions),
            },
            {
                "label": "High priority",
                "value": sum(
                    1
                    for q in questions
                    if str(
                        _get(q, "priority", "")
                    ).lower()
                    == "high"
                ),
            },
            {
                "label": "Categories",
                "value": len(
                    {
                        str(
                            _get(q, "category", "")
                        )
                        for q in questions
                    }
                ),
            },
        ]
    )

    st.write("")

    for index, question in enumerate(
        questions,
        start=1,
    ):
        qid = _get(question, "id")
        text = _get(question, "question")
        priority = _get(question, "priority")
        category = _get(question, "category")
        reason = _get(question, "reason")
        related = _get(
            question,
            "related_requirements",
            [],
        )

        st.markdown(
            f"### Question {index:02d}"
        )

        with st.container(border=True):
            top = st.columns([3, 1])

            with top[0]:
                st.markdown(
                    f"**{_safe_text(text)}**"
                )

            with top[1]:
                st.write(
                    f"{_severity_icon(priority)} "
                    f"{_safe_text(priority).title()}"
                )

            st.caption("WHY WE'RE ASKING")

            st.write(
                _safe_text(reason)
            )

            if related:
                st.caption("RELATED REQUIREMENTS")

                for item in related:
                    st.write(f"• {item}")

            st.text_area(
                "Client answer",
                key=f"discovery_answer_{qid}",
                placeholder=(
                    "Enter the client's answer..."
                ),
                label_visibility="visible",
            )

            st.checkbox(
                "Mark as unresolved",
                key=f"discovery_unresolved_{qid}",
            )


def render_scope(result):
    scope = _get(
        result,
        "validated_scope",
    )

    if scope is None:
        st.info("Validated scope is not available.")
        return

    status = _get(
        scope,
        "overall_scope_status",
        "unknown",
    )

    st.markdown("### Scope status")

    status_badge(status)

    st.write("")

    confirmed = _get(
        scope,
        "confirmed_requirements",
        [],
    )

    unresolved = _get(
        scope,
        "unresolved_items",
        [],
    )

    boundaries = _get(
        scope,
        "scope_boundaries",
        [],
    )

    assumptions = _get(
        scope,
        "assumptions",
        [],
    )

    metric_row(
        [
            {
                "label": "Confirmed",
                "value": sum(
                    1
                    for item in confirmed
                    if str(
                        _get(item, "status", "")
                    ).lower()
                    == "confirmed"
                ),
            },
            {
                "label": "Modified",
                "value": sum(
                    1
                    for item in confirmed
                    if str(
                        _get(item, "status", "")
                    ).lower()
                    == "modified"
                ),
            },
            {
                "label": "Unresolved",
                "value": len(unresolved),
            },
        ]
    )

    st.write("")

    section_title("Requirement decisions")

    if confirmed:
        for item in confirmed:
            status_value = _get(
                item,
                "status",
            )

            requirement = _get(
                item,
                "requirement",
            )

            original = _get(
                item,
                "original_requirement",
            )

            final_scope = _get(
                item,
                "final_scope",
            )

            evidence = _get(
                item,
                "client_evidence",
            )

            notes = _get(
                item,
                "notes",
            )

            with st.container(border=True):
                st.markdown(
                    f"### {_status_icon(status_value)} "
                    f"{_safe_text(requirement)}"
                )

                st.caption("STATUS")
                st.write(
                    _safe_text(status_value)
                    .replace("_", " ")
                    .title()
                )

                if original:
                    st.caption("ORIGINAL REQUIREMENT")
                    st.write(original)

                st.caption("FINAL SCOPE")
                st.write(
                    _safe_text(final_scope)
                )

                if evidence:
                    st.caption("CLIENT EVIDENCE")
                    st.write(evidence)

                if notes:
                    st.caption("NOTES")
                    st.write(notes)
    else:
        st.info("No requirement decisions available.")

    section_title("Scope boundaries")

    if boundaries:
        with st.container(border=True):
            for item in boundaries:
                st.write(f"• {item}")
    else:
        st.info("No scope boundaries were identified.")

    section_title("Assumptions")

    if assumptions:
        with st.container(border=True):
            for item in assumptions:
                st.write(f"• {item}")
    else:
        st.info("No assumptions were identified.")

    section_title("Unresolved items")

    if unresolved:
        for item in unresolved:
            issue = _get(item, "issue")
            reason = _get(item, "reason")
            required_for = _get(
                item,
                "required_for",
            )
            priority = _get(
                item,
                "priority",
            )

            with st.container(border=True):
                st.markdown(
                    f"### {_severity_icon(priority)} "
                    f"{_safe_text(issue)}"
                )

                st.caption("REASON")
                st.write(_safe_text(reason))

                st.caption("REQUIRED FOR")
                st.write(
                    _safe_text(required_for)
                )

                st.caption("PRIORITY")
                st.write(
                    _safe_text(priority).title()
                )
    else:
        st.success(
            "No unresolved scope items remain."
        )


def render_pitch(result):
    pitch = _get(
        result,
        "pitch",
    )

    if pitch is None:
        st.info("Pitch is not available.")
        return

    headline = _get(
        pitch,
        "headline",
    )

    pitch_text = _get(
        pitch,
        "pitch",
    )

    benefits = _get(
        pitch,
        "key_benefits",
        [],
    )

    safety_note = _get(
        pitch,
        "safety_note",
    )

    cta = _get(
        pitch,
        "call_to_action",
    )

    with st.container(border=True):
        st.caption("HEADLINE")

        st.markdown(
            f"## {_safe_text(headline)}"
        )

    section_title("Tailored pitch")

    with st.container(border=True):
        st.write(
            _safe_text(pitch_text)
        )

    section_title("Key benefits")

    if benefits:
        columns = st.columns(
            min(len(benefits), 3)
        )

        for index, benefit in enumerate(
            benefits
        ):
            with columns[index % len(columns)]:
                with st.container(border=True):
                    st.write(
                        f"✓ {benefit}"
                    )
    else:
        st.info("No benefits were generated.")

    if safety_note:
        section_title("Safety / positioning note")

        st.warning(safety_note)

    if cta:
        section_title("Call to action")

        with st.container(border=True):
            st.write(cta)


def render_proposal(result):
    proposal = _get(
        result,
        "proposal",
    )

    if proposal is None:
        st.info("Proposal is not available.")
        return

    title = _get(
        proposal,
        "proposal_title",
    )

    executive_summary = _get(
        proposal,
        "executive_summary",
    )

    challenge = _get(
        proposal,
        "client_challenge",
    )

    solution = _get(
        proposal,
        "proposed_solution",
    )

    scope_of_work = _get(
        proposal,
        "scope_of_work",
        [],
    )

    benefits = _get(
        proposal,
        "key_benefits",
        [],
    )

    boundaries = _get(
        proposal,
        "scope_boundaries",
        [],
    )

    assumptions = _get(
        proposal,
        "assumptions",
        [],
    )

    implementation = _get(
        proposal,
        "implementation_approach",
        [],
    )

    next_steps = _get(
        proposal,
        "next_steps",
        [],
    )

    proposal_status = _get(
        proposal,
        "proposal_status",
        "draft",
    )

    st.caption("PROPOSAL STATUS")
    status_badge(proposal_status)

    with st.container(border=True):
        st.markdown(
            f"# {_safe_text(title)}"
        )

    section_title("Executive summary")

    with st.container(border=True):
        st.write(
            _safe_text(executive_summary)
        )

    section_title("Client challenge")

    with st.container(border=True):
        st.write(
            _safe_text(challenge)
        )

    section_title("Proposed solution")

    with st.container(border=True):
        st.write(
            _safe_text(solution)
        )

    section_title("Scope of work")

    if scope_of_work:
        for index, item in enumerate(
            scope_of_work,
            start=1,
        ):
            with st.container(border=True):
                st.write(
                    f"**{index:02d}**  {item}"
                )
    else:
        st.info("No scope of work items.")

    section_title("Key benefits")

    if benefits:
        for benefit in benefits:
            st.write(f"✓ {benefit}")
    else:
        st.info("No benefits listed.")

    section_title("Implementation approach")

    if implementation:
        for index, item in enumerate(
            implementation,
            start=1,
        ):
            st.write(
                f"**{index}.** {item}"
            )
    else:
        st.info(
            "No implementation approach listed."
        )

    section_title("Scope boundaries")

    if boundaries:
        for item in boundaries:
            st.write(f"• {item}")
    else:
        st.info("No scope boundaries listed.")

    section_title("Assumptions")

    if assumptions:
        for item in assumptions:
            st.write(f"• {item}")
    else:
        st.info("No assumptions listed.")

    section_title("Next steps")

    if next_steps:
        for index, item in enumerate(
            next_steps,
            start=1,
        ):
            st.write(
                f"**{index}.** {item}"
            )
    else:
        st.info("No next steps listed.")


def render_qa(result):
    final_qa = _get(
        result,
        "final_qa",
    )

    if final_qa is None:
        st.info("QA result is not available.")
        return

    deterministic_passed = _get(
        final_qa,
        "deterministic_passed",
        False,
    )

    ai_passed = _get(
        final_qa,
        "ai_passed",
        False,
    )

    ai_score = _get(
        final_qa,
        "ai_score",
    )

    blocking_issues = _get(
        final_qa,
        "blocking_issues",
        [],
    )

    issues = _get(
        final_qa,
        "issues",
        [],
    )

    revision_items = _get(
        final_qa,
        "revision_items",
        [],
    )

    metric_row(
        [
            {
                "label": "Deterministic QA",
                "value": (
                    "PASSED"
                    if deterministic_passed
                    else "FAILED"
                ),
            },
            {
                "label": "AI QA",
                "value": (
                    "PASSED"
                    if ai_passed
                    else "FAILED"
                ),
            },
            {
                "label": "AI score",
                "value": (
                    f"{ai_score:.1f}/10"
                    if isinstance(
                        ai_score,
                        (int, float),
                    )
                    else "—"
                ),
            },
            {
                "label": "Blocking issues",
                "value": len(
                    blocking_issues
                ),
            },
        ]
    )

    st.write("")

    section_title("Deterministic QA")

    if deterministic_passed:
        st.success(
            "Deterministic QA passed."
        )
    else:
        st.error(
            "Deterministic QA failed."
        )

    section_title("AI proposal review")

    if ai_passed:
        st.success(
            f"AI QA passed with a score of "
            f"{ai_score}/10."
        )
    else:
        st.warning(
            f"AI QA requires revision. "
            f"Score: {ai_score}/10."
        )

    section_title("Issues")

    if issues:
        for issue in issues:
            source = _get(
                issue,
                "source",
            )

            severity = _get(
                issue,
                "severity",
            )

            category = _get(
                issue,
                "category",
            )

            section = _get(
                issue,
                "section",
            )

            issue_text = _get(
                issue,
                "issue",
            )

            recommendation = _get(
                issue,
                "recommendation",
            )

            with st.container(border=True):
                st.markdown(
                    f"### {_severity_icon(severity)} "
                    f"{_safe_text(issue_text)}"
                )

                cols = st.columns(3)

                with cols[0]:
                    st.caption("SOURCE")
                    st.write(
                        _safe_text(source).title()
                    )

                with cols[1]:
                    st.caption("SEVERITY")
                    st.write(
                        _safe_text(severity).title()
                    )

                with cols[2]:
                    st.caption("CATEGORY")
                    st.write(
                        _safe_text(category).title()
                    )

                if section:
                    st.caption("SECTION")
                    st.write(section)

                if recommendation:
                    st.caption("RECOMMENDATION")
                    st.write(recommendation)
    else:
        st.success(
            "No QA issues were reported."
        )

    section_title("Blocking issues")

    if blocking_issues:
        for item in blocking_issues:
            st.error(str(item))
    else:
        st.success(
            "No blocking issues."
        )

    section_title("Revision items")

    if revision_items:
        for item in revision_items:
            st.warning(str(item))
    else:
        st.info(
            "No revision items."
        )


def render_final_gate(result):
    final_qa = _get(
        result,
        "final_qa",
    )

    if final_qa is None:
        st.info(
            "Final gate result is not available."
        )
        return

    decision = _get(
        final_qa,
        "decision",
        "UNKNOWN",
    )

    passed = _get(
        final_qa,
        "passed",
        False,
    )

    deterministic_passed = _get(
        final_qa,
        "deterministic_passed",
        False,
    )

    ai_passed = _get(
        final_qa,
        "ai_passed",
        False,
    )

    ai_score = _get(
        final_qa,
        "ai_score",
    )

    blocking = _get(
        final_qa,
        "blocking_issues",
        [],
    )

    summary = _get(
        final_qa,
        "summary",
    )

    warnings = _get(
        result,
        "warnings",
        [],
    )

    if decision == "PASS" and passed:
        st.success(
            "## ✓ PASS\n\n"
            "Proposal approved for delivery."
        )

    elif decision == "NEEDS_REVISION":
        st.warning(
            "## ⚠ NEEDS REVISION\n\n"
            "The proposal requires changes before "
            "it can be delivered."
        )

    else:
        st.error(
            "## × FAIL\n\n"
            "The proposal cannot be delivered."
        )

    st.write("")

    metric_row(
        [
            {
                "label": "Deterministic QA",
                "value": (
                    "PASSED"
                    if deterministic_passed
                    else "FAILED"
                ),
            },
            {
                "label": "AI QA",
                "value": (
                    "PASSED"
                    if ai_passed
                    else "FAILED"
                ),
            },
            {
                "label": "AI score",
                "value": (
                    f"{ai_score:.1f}/10"
                    if isinstance(
                        ai_score,
                        (int, float),
                    )
                    else "—"
                ),
            },
            {
                "label": "Blocking issues",
                "value": len(blocking),
            },
        ]
    )

    if summary:
        st.write("")
        with st.container(border=True):
            st.caption("FINAL ASSESSMENT")
            st.write(summary)

    if blocking:
        section_title("Blocking issues")

        for issue in blocking:
            st.error(str(issue))

    if warnings:
        section_title("Warnings")

        for warning in warnings:
            st.warning(str(warning))


def render_technical_details(data):
    if data is None:
        return

    with st.expander(
        "Technical details",
        expanded=False,
    ):
        serializable = _to_dict(data)

        try:
            st.json(serializable)
        except Exception:
            st.write(serializable)


def render_bullets(items: Iterable[Any]):
    for item in items or []:
        st.write(f"• {item}")