"""
src/extractor.py
Converts raw, unstructured client inquiries into a validated RequirementMap using Groq.
"""

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import BadRequestError, Groq, RateLimitError

from .schemas import RequirementMap


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found. "
        "Please check your .env file."
    )


client = Groq(api_key=API_KEY)


# ============================================================
# MODEL
# ============================================================

MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the Requirement Extraction Engine for a consultancy
Discovery-to-Proposal AI system.

Your job is to convert a messy client request into a precise,
grounded RequirementMap.

The most important principle is:

ACCURACY OVER COMPLETENESS.

Only extract information supported by the client's message.

Never invent information.

============================================================
CORE PIPELINE PRINCIPLE
============================================================

The extracted requirements will later pass through:

Requirement
    ↓
Risk Analysis
    ↓
Discovery Question
    ↓
Client Answer
    ↓
Scope Validation
    ↓
Proposal

Therefore requirements must be atomic, traceable, and faithful
to the client's actual request.

Do NOT solve the client's problem.

Do NOT design the technical architecture.

Do NOT invent APIs, databases, AI models, vendors, workflows,
budgets, timelines, metrics, or infrastructure.

============================================================
1. BUSINESS GOAL
============================================================

business_goal must contain the main business outcome explicitly
stated by the client.

Examples:

"Increase patient bookings"
"Reduce staff workload"
"Increase average order value"

Do not duplicate the business goal as a requirement.

============================================================
2. TARGET USERS
============================================================

Only include users explicitly mentioned or clearly identified
in the client's request.

Examples:

"patients"
"customers"
"staff"
"students"

Do not invent user groups.

============================================================
3. REQUIREMENTS
============================================================

A requirement describes something the requested system must do,
support, handle, integrate with, or enforce.

Keep requirements atomic.

Examples:

"Answer common patient questions."
"Qualify potential patients."
"Book appointments."
"Escalate medical questions to clinic staff."
"Integrate with Google Calendar."
"Operate 24/7."
"Support WhatsApp and website inquiries."

Do not combine unrelated requirements.

Do not turn the business goal itself into a requirement.

============================================================
4. CHANNELS AND INTEGRATIONS
============================================================

The previous version of this extractor contained separate
top-level fields for integrations and channels.

The current RequirementMap schema intentionally does not.

Therefore, when a channel or integration represents an actual
system capability explicitly requested by the client, represent
it as an atomic requirement.

Examples:

Client:
"We receive inquiries through WhatsApp and our website."

Possible requirements:

"Handle patient inquiries through WhatsApp."
"Handle patient inquiries through the website."

Client:
"We currently use Google Calendar for appointments."

Possible requirement:

"Integrate appointment scheduling with Google Calendar."

Do NOT invent an API, webhook, middleware, database, or vendor
beyond what the client explicitly stated.

============================================================
5. CONSTRAINTS
============================================================

Explicit constraints that materially affect system behavior
should become atomic requirements when appropriate.

Examples:

"The assistant should be available 24/7."
    →
"Operate 24/7."

"If a patient asks a medical question requiring professional
judgment, the conversation should be escalated to clinic staff."
    →
"Escalate medical questions requiring professional judgment
to clinic staff."

"Must support English, Hindi and Marathi."
    →
"Support English, Hindi and Marathi."

Preserve unrealistic or absolute expectations exactly.

Do NOT silently make them safer or more realistic.

The risk analyzer will evaluate them later.

============================================================
6. SOURCE
============================================================

Use only:

"client_stated"

when explicitly stated by the client.

Use:

"inferred"

only when strongly implied and necessary.

Prefer "client_stated" whenever the wording supports it.

Never invent an inferred requirement merely because it would
normally be useful.

============================================================
7. CONFIDENCE
============================================================

Use 0.0 to 1.0.

Guidance:

1.0 = explicitly stated
0.8 = strongly implied
0.6 = reasonably inferred

Do not use confidence to hide uncertainty.

============================================================
8. RISK LEVEL
============================================================

Assign an initial extraction-level risk signal.

Allowed values:

"low"
"medium"
"high"
"critical"

Guidance:

low:
straightforward functionality with little ambiguity.

medium:
requirement has meaningful implementation or scope ambiguity.

high:
requirement involves integrations, qualification rules,
important business logic, guarantees, automation with material
consequences, or significant feasibility uncertainty.

critical:
requirement involves medical diagnosis, medical treatment,
prescribing, financial/legal high-stakes decisions, unsafe
autonomy, or similarly consequential behavior.

IMPORTANT:

This is only an initial signal.

A separate Risk Analyzer will perform deep hidden-risk
analysis. Do not attempt to replace that analyzer here.

============================================================
9. NO NOTES FIELD
============================================================

The current Requirement schema does NOT contain a notes field.

Therefore:

DO NOT return:

"notes"

or any other unsupported requirement property.

============================================================
10. UNKNOWN INFORMATION
============================================================

Do not invent missing details.

For example:

Client:
"We use a CRM."

Do NOT create:
"Integrate with Salesforce."

Client:
"We use Google Calendar."

Do NOT create:
"Use Google Calendar API."

Only extract what is actually stated.

Unknown technical details will be discovered later by the
risk-analysis and discovery stages.

============================================================
11. SAFETY
============================================================

If the client explicitly requests a high-risk capability,
preserve it as a requirement.

Examples:

"Diagnose disease from symptoms."
"Recommend medicines."
"Guarantee 100% accuracy."

Do not remove the requirement.

Do not rewrite it into a safer requirement.

The analyzer and scope-validation stages handle the risk.

============================================================
12. ATOMICITY
============================================================

Each requirement should represent one meaningful capability,
constraint, integration, or behavior.

Bad:

"Answer questions, qualify patients, book appointments,
integrate Google Calendar and escalate medical issues."

Good:

"Answer common patient questions."
"Qualify potential patients."
"Book appointments."
"Integrate appointment scheduling with Google Calendar."
"Escalate medical questions requiring professional judgment
to clinic staff."

============================================================
13. AVOID DUPLICATES
============================================================

Do not create duplicate requirements with slightly different
wording.

If the same capability is stated multiple times, extract it
once.

============================================================
14. DO NOT INVENT TECHNICAL SOLUTIONS
============================================================

Never add:

- LLM
- RAG
- vector database
- embeddings
- API gateway
- webhook
- cloud provider
- database
- authentication
- monitoring
- Twilio
- HubSpot
- Salesforce
- OpenAI
- Groq

unless explicitly mentioned by the client.

============================================================
15. COMPLETE JSON
============================================================

Return exactly one JSON object.

The object MUST contain:

business_goal
target_users
requirements

The requirements array MUST contain objects with exactly:

requirement
category
source
confidence
risk_level

Do NOT return:

notes
integrations
channels
constraints
timeline
budget
assumptions
missing_information

Those fields belonged to an older schema and are no longer
accepted by the current RequirementMap model.

If information is unknown, simply do not invent it.

Return no markdown.

Return no explanations.

Return exactly one complete JSON object.
"""


# ============================================================
# STRICT GROQ JSON SCHEMA
# ============================================================

REQUIREMENT_MAP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "business_goal",
        "target_users",
        "requirements",
    ],
    "properties": {
        "business_goal": {
            "type": [
                "string",
                "null",
            ]
        },
        "target_users": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "requirement",
                    "category",
                    "source",
                    "confidence",
                    "risk_level",
                ],
                "properties": {
                    "requirement": {
                        "type": "string",
                    },
                    "category": {
                        "type": "string",
                    },
                    "source": {
                        "type": "string",
                        "enum": [
                            "client_stated",
                            "inferred",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                            "critical",
                        ],
                    },
                },
            },
        },
    },
}


# ============================================================
# HELPERS
# ============================================================

def _clean_requirement_text(value: Any) -> str:
    """
    Normalize requirement text without changing its meaning.
    """
    if not isinstance(value, str):
        return ""

    text = " ".join(value.strip().split())

    if not text:
        return ""

    return text


def _normalize_source(value: Any) -> str:
    """
    Normalize the requirement source to the current schema.
    """
    if value == "inferred":
        return "inferred"

    return "client_stated"


def _normalize_risk_level(value: Any) -> str:
    """
    Normalize initial extraction-level risk.
    """
    allowed = {
        "low",
        "medium",
        "high",
        "critical",
    }

    value = str(value).strip().lower()

    if value in allowed:
        return value

    return "medium"


def _clean_requirement(
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert one Groq requirement into the exact current
    Requirement schema (schemas.py).

    Produces keys:
        requirement       (text of the requirement)
        category          (free string, normalized by schema)
        source            ("client_stated" | "inferred")
        confidence        (0.0 - 1.0)
        risk_level        ("low" | "medium" | "high" | "critical")
    """

    return {
        "requirement": _clean_requirement_text(
            raw.get("requirement")
        ),
        "category": _clean_requirement_text(
            raw.get("category")
        ) or "Other",
        "source": _normalize_source(
            raw.get("source")
        ),
        "confidence": max(
            0.0,
            min(
                1.0,
                float(
                    raw.get(
                        "confidence",
                        0.0,
                    )
                ),
            ),
        ),
        "risk_level": _normalize_risk_level(
            raw.get("risk_level")
        ),
    }


def _is_duplicate_requirement(
    requirement: str,
    existing: List[str],
) -> bool:
    """
    Conservative deterministic duplicate check.

    Exact normalized matches are removed here.

    Semantic duplicate detection remains an AI responsibility;
    we intentionally do not use fuzzy matching that could merge
    genuinely different requirements.
    """

    normalized = " ".join(
        requirement.lower().split()
    )

    for item in existing:
        if normalized == " ".join(
            item.lower().split()
        ):
            return True

    return False


def _assign_requirement_ids(
    requirements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Assign stable deterministic requirement IDs.

    Output structure MUST exactly match the Requirement model
    in schemas.py:

        requirement_id
        requirement
        category
        source
        confidence
        risk_level
    """

    result: List[Dict[str, Any]] = []

    seen: List[str] = []

    for raw in requirements:
        cleaned = _clean_requirement(raw)

        requirement_text = cleaned["requirement"]

        if not requirement_text:
            continue

        if _is_duplicate_requirement(
            requirement_text,
            seen,
        ):
            continue

        requirement_id = (
            f"REQ-{len(result) + 1:03d}"
        )

        item = {
            "requirement_id": requirement_id,
            "requirement": requirement_text,
            "category": cleaned["category"],
            "source": cleaned["source"],
            "confidence": cleaned["confidence"],
            "risk_level": cleaned["risk_level"],
        }

        result.append(item)
        seen.append(requirement_text)

    return result


def _validate_raw_structure(
    data: Dict[str, Any],
) -> None:
    """
    Defensive validation of raw Groq output before final Pydantic.
    """

    if not isinstance(data, dict):
        raise RuntimeError(
            "Extractor returned a JSON value that is not an object."
        )

    required = {
        "business_goal",
        "target_users",
        "requirements",
    }

    missing = sorted(
        required - set(data.keys())
    )

    if missing:
        raise RuntimeError(
            "Extractor returned incomplete JSON. "
            f"Missing fields: {missing}"
        )

    if not isinstance(
        data["target_users"],
        list,
    ):
        raise RuntimeError(
            "Extractor target_users must be an array."
        )

    if not isinstance(
        data["requirements"],
        list,
    ):
        raise RuntimeError(
            "Extractor requirements must be an array."
        )


# ============================================================
# EXTRACT REQUIREMENTS
# ============================================================

def extract_requirements(
    client_request: str,
) -> RequirementMap:
    """
    Extract grounded requirements from a client request using
    real Groq AI.

    Contract:

        client_request
            ↓
        Groq extraction
            ↓
        deterministic cleanup
            ↓
        stable REQ IDs
            ↓
        Pydantic RequirementMap (schemas.py)
    """

    if not client_request or not client_request.strip():
        raise ValueError(
            "Client request cannot be empty."
        )

    user_message = (
        "Extract the requirements from this client request.\n\n"
        "CLIENT REQUEST:\n"
        f"{client_request.strip()}\n\n"
        "Remember:\n"
        "- Extract only grounded requirements.\n"
        "- Keep requirements atomic.\n"
        "- Do not invent technical solutions.\n"
        "- Explicit channels, integrations, and constraints "
        "should become requirements when they represent actual "
        "system behavior.\n"
        "- Return exactly the requested JSON structure."
    )

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "requirement_map",
            "strict": True,
            "schema": REQUIREMENT_MAP_SCHEMA,
        },
    }

    last_error = None

    # ========================================================
    # REAL GROQ CALL
    # ========================================================

    for attempt in range(2):
        try:
            system_prompt = SYSTEM_PROMPT

            if attempt == 1:
                system_prompt += """

FINAL STRICT OUTPUT CHECK:

Before returning the response, verify that every requirement
object contains exactly these fields:

requirement
category
source
confidence
risk_level

Do not include requirement_id.

Python will assign requirement_id after generation.

Do not include notes.

Do not include integrations.

Do not include channels.

Do not include constraints.

Do not include timeline.

Do not include budget.

Do not include assumptions.

Do not include missing_information.

Return exactly one JSON object.
"""

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                response_format=response_format,
                temperature=0,
                max_completion_tokens=4500,
            )

            break

        except RateLimitError as exc:
            raise RuntimeError(
                "Groq rate limit reached. "
                "Please wait for the rate-limit window to reset "
                "before running the pipeline again."
            ) from exc

        except BadRequestError as exc:
            last_error = exc
            message = str(exc)

            if attempt == 0 and (
                "json_validate_failed" in message
                or "Failed to validate JSON" in message
            ):
                print(
                    "Extractor structured output rejected by Groq; "
                    "retrying once..."
                )
                continue

            raise RuntimeError(
                "Groq rejected the extractor structured-output "
                "request. No fallback/mock data was generated."
            ) from exc

    else:
        raise RuntimeError(
            "Groq could not produce valid structured extractor "
            "output after retrying."
        ) from last_error

    # ========================================================
    # FINISH REASON
    # ========================================================

    finish_reason = (
        response.choices[0].finish_reason
    )

    print(
        "Finish reason:",
        finish_reason,
    )

    if finish_reason != "stop":
        raise RuntimeError(
            "Extractor did not finish normally. "
            f"Finish reason: {finish_reason}"
        )

    # ========================================================
    # CONTENT
    # ========================================================

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Extractor returned empty content."
        )

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:
        data: Dict[str, Any] = json.loads(
            content
        )

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Extractor returned invalid JSON."
        ) from exc

    # ========================================================
    # HANDLE null business_goal FROM GROQ
    # ========================================================
    # The Groq JSON schema explicitly allows business_goal to be null.
    # RequirementMap.business_goal requires a non-empty string.

    if data.get("business_goal") is None or (
        isinstance(data.get("business_goal"), str)
        and not data["business_goal"].strip()
    ):
        data["business_goal"] = "Not explicitly stated"

    # ========================================================
    # RAW STRUCTURE VALIDATION
    # ========================================================

    _validate_raw_structure(data)

    # ========================================================
    # NORMALIZE REQUIREMENTS
    # ========================================================

    raw_requirements = data.get(
        "requirements",
        [],
    )

    normalized_requirements = []

    for raw in raw_requirements:
        if not isinstance(raw, dict):
            raise RuntimeError(
                "Extractor returned a requirement that is not "
                "a JSON object."
            )

        normalized_requirements.append(
            _clean_requirement(raw)
        )

    # ========================================================
    # ASSIGN STABLE REQUIREMENT IDs
    # ========================================================

    requirements_with_ids = _assign_requirement_ids(
        normalized_requirements
    )

    # Fallback: if the LLM found no structured requirements (e.g., the
    # client request is purely outcome-focused with no system description),
    # create a single requirement from the raw text so the pipeline can
    # continue and downstream QA can evaluate the content.
    if not requirements_with_ids:
        raw_text = client_request.strip()
        if raw_text:
            requirements_with_ids = [
                {
                    "requirement_id": "REQ-001",
                    "requirement": raw_text[:500],
                    "category": "Other",
                    "source": "client_stated",
                    "confidence": 0.6,
                    "risk_level": "high",
                }
            ]

    if not requirements_with_ids:
        raise RuntimeError(
            "Extractor returned zero usable requirements."
        )

    # ========================================================
    # BUILD CLEAN PAYLOAD MATCHING RequirementMap EXACTLY
    # ========================================================
    # RequirementMap uses extra="forbid".
    # We must NOT include any keys other than the three defined:
    #     business_goal
    #     target_users
    #     requirements

    clean_payload: Dict[str, Any] = {
        "business_goal": str(data["business_goal"]).strip(),
        "target_users": [
            str(user).strip()
            for user in data["target_users"]
            if str(user).strip()
        ],
        "requirements": requirements_with_ids,
    }

    # ========================================================
    # FINAL PYDANTIC VALIDATION
    # ========================================================

    try:
        result = RequirementMap.model_validate(
            clean_payload
        )

    except Exception as exc:
        print("\n========== NORMALIZED EXTRACTOR OUTPUT ==========")
        print(
            json.dumps(
                clean_payload,
                indent=2,
                ensure_ascii=False,
            )
        )
        print(
            "=================================================\n"
        )

        raise RuntimeError(
            f"Extractor output failed Pydantic validation: {exc}"
        ) from exc

    # ========================================================
    # REQUIREMENT ID SAFETY CHECK
    # ========================================================

    expected_ids = [
        f"REQ-{index:03d}"
        for index in range(
            1,
            len(result.requirements) + 1,
        )
    ]

    actual_ids = [
        requirement.requirement_id
        for requirement in result.requirements
    ]

    if actual_ids != expected_ids:
        raise RuntimeError(
            "Requirement IDs are not stable/sequential. "
            f"Expected: {expected_ids}, "
            f"Actual: {actual_ids}"
        )

    return result